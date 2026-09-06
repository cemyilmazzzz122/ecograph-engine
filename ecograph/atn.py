"""
Allometric Trophic Network (ATN) Continuous Dynamical Engine.
Solves coupled ODEs with Kleiber mass scaling, generalized Holling functional response,
and adaptive 4th-order Runge-Kutta (RK4) integration with Richardson extrapolation.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Optional, Tuple

from ecograph.models import (
    AtnParameters,
    AtnResult,
    AtnSeries,
    EcosystemGraph,
    Perturbation,
    Species,
)

CLASS_BASE_MASS_KG: Dict[str, float] = {
    "Mammalia": 10.0,
    "Aves": 0.5,
    "Reptilia": 1.0,
    "Amphibia": 0.05,
    "Actinopterygii": 0.5,
    "Chondrichthyes": 25.0,
    "Insecta": 0.0005,
    "Arachnida": 0.0001,
    "Malacostraca": 0.02,
    "Gastropoda": 0.01,
    "Magnoliopsida": 2.0,
    "Liliopsida": 0.5,
    "Pinopsida": 100.0,
    "Florideophyceae": 0.01,
    "Phaeophyceae": 0.5,
    "Agaricomycetes": 0.02,
}


def _estimate_body_mass(species: Species) -> float:
    """Estimates body mass in kg from explicit traits or allometric trophic scaling."""
    if species.body_mass_kg is not None and species.body_mass_kg > 0:
        return species.body_mass_kg

    # Base estimate from taxonomy or default
    base = 1.0
    if species.trophic_level == "PRODUCER":
        base = 1.0
    elif species.trophic_level == "APEX_PREDATOR":
        base = 50.0
    elif "CONSUMER" in species.trophic_level:
        base = 5.0
    elif species.trophic_level == "DECOMPOSER":
        base = 0.01

    # In food webs, predator-prey mass ratios scale ~10-100x per trophic step
    rank_multiplier = 20.0 ** max(0.0, species.trophic_rank - 2.0)
    return max(base * rank_multiplier, 1e-6)


class AtnModel:
    """Compiled internal structure of arrays (SoA) for efficient vectorized ODE evaluation."""

    def __init__(self, graph: EcosystemGraph, params: AtnParameters):
        self.graph = graph
        self.params = params
        self.n = len(graph.species)
        self.ids = [s.id for s in graph.species]
        self.id_to_idx = {s.id: i for i, s in enumerate(graph.species)}

        masses = [_estimate_body_mass(s) for s in graph.species]
        producer_masses = [
            masses[i] for i, s in enumerate(graph.species) if s.trophic_level == "PRODUCER"
        ]
        producer_masses.sort()

        if producer_masses:
            ref_mass = producer_masses[len(producer_masses) // 2]
        else:
            ref_mass = min(masses) if masses else 1.0

        self.producer = [1 if s.trophic_level == "PRODUCER" else 0 for s in graph.species]
        self.initial = [1.0 if self.producer[i] else 0.5 for i in range(self.n)]

        # Kleiber mass-specific metabolic scaling: x_i = a * (M_i / M_ref)^(-0.25)
        self.metabolic: List[float] = [0.0] * self.n
        for i in range(self.n):
            if not self.producer[i]:
                raw = params.metabolic_scale * math.pow(masses[i] / ref_mass, -0.25)
                self.metabolic[i] = max(params.metabolic_floor, min(params.metabolic_ceiling, raw))

        # Build predation links
        prey_of: List[List[int]] = [[] for _ in range(self.n)]
        weight_of: List[List[float]] = [[] for _ in range(self.n)]

        for edge in graph.interactions:
            if edge.type != "PREYS_ON":
                continue
            pred = self.id_to_idx.get(edge.source)
            prey = self.id_to_idx.get(edge.target)
            if pred is not None and prey is not None and pred != prey:
                prey_of[pred].append(prey)
                weight_of[pred].append(max(edge.strength, 0.01))

        self.prey_indices: List[List[int]] = prey_of
        self.prey_weights: List[List[float]] = []
        self.prey_efficiencies: List[List[float]] = []

        for i in range(self.n):
            total_w = sum(weight_of[i]) or 1.0
            self.prey_weights.append([w / total_w for w in weight_of[i]])
            self.prey_efficiencies.append(
                [
                    params.herbivore_efficiency if self.producer[p] else params.carnivore_efficiency
                    for p in prey_of[i]
                ]
            )

        # Build non-trophic / symbiotic links
        # Stores (target_idx, strength, kind) where kind: +1 (mutualism), -1 (host), +2 (parasite)
        self.partners: List[List[Tuple[int, float, int]]] = [[] for _ in range(self.n)]
        self.mutualist_dependent = [0] * self.n

        for edge in graph.interactions:
            u = self.id_to_idx.get(edge.source)
            v = self.id_to_idx.get(edge.target)
            if u is None or v is None or u == v:
                continue

            strength = max(0.0, min(1.0, edge.strength))
            if edge.type == "MUTUALISM":
                self.partners[u].append((v, strength, 1))
                self.partners[v].append((u, strength, 1))
            elif edge.type == "PARASITISM":
                self.partners[v].append((u, strength, -1))  # v is host
                self.partners[u].append((v, strength, 2))   # u is parasite

        for i in range(self.n):
            if (
                not self.producer[i]
                and len(self.prey_indices[i]) == 0
                and any(p[2] == 1 for p in self.partners[i])
            ):
                self.mutualist_dependent[i] = 1


def _derivative(model: AtnModel, biomass: List[float], out: List[float]) -> None:
    """Computes dB_i/dt for all species."""
    n = model.n
    p = model.params
    q = p.holling_exponent
    b0q = math.pow(p.half_saturation, q)

    for i in range(n):
        out[i] = 0.0

    # 1. Primary producer growth and consumer basal maintenance
    for i in range(n):
        bi = biomass[i]
        if model.producer[i]:
            out[i] += p.growth_rate * bi * (1.0 - bi / p.carrying_capacity)
        else:
            out[i] -= model.metabolic[i] * bi

    # 2. Non-trophic / symbiotic interactions
    for i in range(n):
        bi = biomass[i]
        if bi <= 0.0:
            continue
        for j, strength, kind in model.partners[i]:
            bj = biomass[j]
            avail = bj / (bj + p.partner_half_saturation) if (bj + p.partner_half_saturation) > 0 else 0.0
            shortfall = 1.0 - avail

            if kind == 1:
                # Mutualism
                out[i] -= p.mutualism_weight * strength * shortfall * bi
                if model.mutualist_dependent[i]:
                    out[i] += model.metabolic[i] * p.mutualist_subsidy * avail * bi
            elif kind == -1:
                # Host burden
                out[i] -= p.parasite_burden * strength * avail * bi
            elif kind == 2:
                # Parasite shortfall
                out[i] -= strength * shortfall * bi

    # 3. Predation / Functional Response
    for i in range(n):
        bi = biomass[i]
        prey_list = model.prey_indices[i]
        if bi <= 0.0 or not prey_list:
            continue

        weights = model.prey_weights[i]
        denom = b0q
        contributions: List[float] = []

        for k, prey_idx in enumerate(prey_list):
            bj = biomass[prey_idx]
            val = weights[k] * math.pow(bj, q) if bj > 0.0 else 0.0
            contributions.append(val)
            denom += val

        if denom <= 0.0:
            continue

        intake = model.metabolic[i] * p.max_consumption * bi
        efficiencies = model.prey_efficiencies[i]

        for k, prey_idx in enumerate(prey_list):
            share = contributions[k] / denom
            if share <= 0.0:
                continue
            flow = intake * share
            out[i] += flow
            out[prey_idx] -= flow / efficiencies[k]


def _rk4_step(
    model: AtnModel,
    state: List[float],
    h: number,
    out: List[float],
    k1: List[float],
    k2: List[float],
    k3: List[float],
    k4: List[float],
    temp: List[float],
) -> None:
    """Executes a single classical 4th-order Runge-Kutta step."""
    n = model.n

    # k1 = f(state)
    _derivative(model, state, k1)

    # k2 = f(state + h/2 * k1)
    for i in range(n):
        temp[i] = max(state[i] + 0.5 * h * k1[i], 0.0)
    _derivative(model, temp, k2)

    # k3 = f(state + h/2 * k2)
    for i in range(n):
        temp[i] = max(state[i] + 0.5 * h * k2[i], 0.0)
    _derivative(model, temp, k3)

    # k4 = f(state + h * k3)
    for i in range(n):
        temp[i] = max(state[i] + h * k3[i], 0.0)
    _derivative(model, temp, k4)

    # out = state + h/6 * (k1 + 2*k2 + 2*k3 + k4)
    h6 = h / 6.0
    for i in range(n):
        out[i] = max(state[i] + h6 * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i]), 0.0)


def _integrate(
    model: AtnModel,
    state: List[float],
    span: float,
    sample_count: int = 1,
    on_sample: Optional[Callable[[float], None]] = None,
    on_extinct: Optional[Callable[[int, float], None]] = None,
) -> Tuple[int, int, float, float]:
    """Integrates the ATN ODE system with adaptive step-doubling (Richardson extrapolation)."""
    if span <= 0:
        return 0, 0, 0.0, 0.0

    n = model.n
    k1 = [0.0] * n
    k2 = [0.0] * n
    k3 = [0.0] * n
    k4 = [0.0] * n
    temp = [0.0] * n
    full = [0.0] * n
    half = [0.0] * n

    interval = span / sample_count
    time = 0.0
    h = interval / 8.0
    tolerance = 1e-4

    steps = 0
    rejected = 0
    min_step = float("inf")
    max_step = 0.0

    for sample in range(1, sample_count + 1):
        target = sample * interval

        while time < target - 1e-12:
            h = min(h, target - time)

            # Full step of size h
            _rk4_step(model, state, h, full, k1, k2, k3, k4, temp)

            # Two half steps of size h/2
            _rk4_step(model, state, 0.5 * h, half, k1, k2, k3, k4, temp)
            _rk4_step(model, half, 0.5 * h, half, k1, k2, k3, k4, temp)

            # Local truncation error estimate
            error = max(abs(full[i] - half[i]) for i in range(n))

            if error > tolerance and h > interval / 4096.0:
                h *= 0.5
                rejected += 1
                continue

            # Accept step; Richardson extrapolation adopts the more accurate half-step solution
            for i in range(n):
                state[i] = half[i]

            time += h
            steps += 1
            min_step = min(min_step, h)
            max_step = max(max_step, h)

            # Extinction thresholding
            for i in range(n):
                if 0.0 < state[i] < model.params.extinction_threshold:
                    state[i] = 0.0
                    if on_extinct:
                        on_extinct(i, time)

            if error < tolerance / 10.0:
                h *= 1.6  # smooth region, expand step size

        if on_sample:
            on_sample(time)

    return steps, rejected, min_step if min_step != float("inf") else 0.0, max_step


def simulate_atn(
    graph: EcosystemGraph,
    perturbations: Optional[List[Perturbation]] = None,
    duration: float = 200.0,
    burn_in: float = 1500.0,
    samples: int = 120,
    parameters: Optional[AtnParameters] = None,
) -> AtnResult:
    """
    Simulates the Allometric Trophic Network (ATN) ODE system.

    Protocol:
    1. System is stabilized through an unperturbed burn-in phase to find the dynamic baseline.
    2. Runs dual trajectories (perturbed run vs. control run).
    3. Calculates percentage change over time relative to the unperturbed baseline.

    Args:
        graph: Ecosystem network.
        perturbations: List of initial shocks applied to species.
        duration: Total simulation time units (default: 200).
        burn_in: Transient stabilization duration (default: 1500, cap: 8000).
        samples: Number of equidistant time points to capture (default: 120).
        parameters: Biophysical ATN model parameters.

    Returns:
        AtnResult with trajectory time series, extinctions, and numerical diagnostics.
    """
    params = parameters or AtnParameters()
    model = AtnModel(graph, params)
    n = model.n

    duration = max(1.0, min(2000.0, duration))
    samples = max(10, min(400, samples))
    burn_in_cap = max(0.0, min(8000.0, burn_in))

    # 1. Attractor stabilization (Burn-in)
    state = list(model.initial)
    burn_in_done = 0.0
    chunk = 100.0
    scratch_deriv = [0.0] * n

    while burn_in_done < burn_in_cap:
        _integrate(model, state, chunk, sample_count=4)
        burn_in_done += chunk

        # Evaluate maximum relative drift
        _derivative(model, state, scratch_deriv)
        worst_drift = 0.0
        for i in range(n):
            if state[i] > params.extinction_threshold:
                drift = abs(scratch_deriv[i]) / state[i]
                if drift > worst_drift:
                    worst_drift = drift
        if worst_drift < 1e-4:
            break

    baseline = list(state)
    persisted = sum(1 for v in baseline if v > params.extinction_threshold)

    # 2. Setup dual runs: Control vs. Perturbed
    control = list(baseline)
    perturbed = list(baseline)

    shocks: Dict[str, float] = {
        p.species_id: p.change_percent for p in (perturbations or [])
    }
    for i, s_id in enumerate(model.ids):
        if s_id in shocks:
            perturbed[i] = max(perturbed[i] * (1.0 + shocks[s_id] / 100.0), 0.0)

    times: List[float] = [0.0]
    interval = duration / samples
    for s_idx in range(1, samples + 1):
        times.append(round(s_idx * interval, 2))

    control_history: List[List[float]] = [list(control)]
    _integrate(
        model,
        control,
        duration,
        sample_count=samples,
        on_sample=lambda t: control_history.append(list(control)),
    )

    extinctions: List[Dict[str, Any]] = []
    perturbed_history: List[List[float]] = [list(perturbed)]

    def handle_extinct(idx: int, t: float):
        extinctions.append(
            {
                "species_id": model.ids[idx],
                "common_name": graph.species[idx].common_name,
                "time": round(t, 2),
            }
        )

    steps, rejected, min_s, max_s = _integrate(
        model,
        perturbed,
        duration,
        sample_count=samples,
        on_sample=lambda t: perturbed_history.append(list(perturbed)),
        on_extinct=handle_extinct,
    )

    # Compute percentage changes relative to control
    series_list: List[AtnSeries] = []
    for i, sp in enumerate(graph.species):
        values: List[float] = []
        for step_idx in range(len(times)):
            ctrl_val = control_history[step_idx][i]
            pert_val = perturbed_history[step_idx][i]

            if ctrl_val > params.extinction_threshold:
                pct = ((pert_val - ctrl_val) / ctrl_val) * 100.0
            else:
                pct = 0.0 if pert_val <= params.extinction_threshold else 100.0
            values.append(round(pct, 2))

        final_pct = values[-1] if values else 0.0
        is_extinct = perturbed_history[-1][i] <= params.extinction_threshold

        series_list.append(
            AtnSeries(
                species_id=sp.id,
                common_name=sp.common_name,
                trophic_level=sp.trophic_level,
                values=values,
                final_change_percent=final_pct,
                extinct=is_extinct,
            )
        )

    diagnostics = {
        "burn_in_duration": round(burn_in_done, 1),
        "persisted_species": persisted,
        "persistence_ratio": round(persisted / max(n, 1), 3),
        "total_steps": steps,
        "rejected_steps": rejected,
        "min_step_size": round(min_s, 6),
        "max_step_size": round(max_s, 6),
    }

    return AtnResult(
        times=times,
        series=series_list,
        extinctions=extinctions,
        diagnostics=diagnostics,
    )

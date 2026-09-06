"""
Discrete Linear Wave & Relaxation Propagation Engine.
Simulates trophic cascades as discrete waves of directional ecological impacts.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ecograph.models import (
    EcosystemGraph,
    Interaction,
    LinearImpact,
    LinearResult,
    Perturbation,
    Species,
)

# Canonical ecological impact coefficients
COEFF = {
    "bottom_up_loss": 1.00,
    "bottom_up_gain": 0.45,
    "top_down_release": 0.40,
    "mutualism": 0.60,
    "parasite_on_host_loss": 0.85,
    "host_relief_from_parasite": 0.15,
    "competition": 0.30,
    "decomposer_substrate": 0.35,
    "nutrient_recycling": 0.10,
}

MIN_CHANGE = -100.0
MAX_CHANGE = 300.0


def _clamp(val: float, low: float, high: float) -> float:
    return max(low, min(high, val))


def simulate_linear(
    graph: EcosystemGraph,
    perturbations: List[Perturbation],
    steps: int = 6,
) -> LinearResult:
    """
    Runs discrete wave propagation on an ecosystem network.

    Args:
        graph: The ecosystem network.
        perturbations: Initial population shocks applied to species.
        steps: Number of discrete propagation waves (default: 6, range: [1, 12]).

    Returns:
        LinearResult containing per-species percentage impacts and cascade summary.
    """
    if not perturbations:
        raise ValueError("At least one perturbation is required.")

    species_by_id: Dict[str, Species] = {s.id: s for s in graph.species}
    for p in perturbations:
        if p.species_id not in species_by_id:
            raise ValueError(f"Unknown species ID in perturbation: '{p.species_id}'")

    steps = int(_clamp(steps, 1, 12))

    # Pinned species (scenario inputs held constant each wave)
    pinned: Dict[str, float] = {
        p.species_id: _clamp(p.change_percent, MIN_CHANGE, MAX_CHANGE)
        for p in perturbations
    }

    # Index incoming interactions for each species
    incoming_edges: Dict[str, List[Interaction]] = {s.id: [] for s in graph.species}
    for edge in graph.interactions:
        if edge.source in incoming_edges:
            incoming_edges[edge.source].append(edge)
        if edge.target in incoming_edges and edge.source != edge.target:
            incoming_edges[edge.target].append(edge)

    state: Dict[str, float] = {s.id: pinned.get(s.id, 0.0) for s in graph.species}
    first_wave: Dict[str, int] = {s_id: 0 for s_id in pinned}
    last_contributions: Dict[str, List[Tuple[str, float, str]]] = {s.id: [] for s in graph.species}

    for round_num in range(1, steps + 1):
        next_state: Dict[str, float] = {}
        round_contributions: Dict[str, List[Tuple[str, float, str]]] = {}

        for s in graph.species:
            if s.id in pinned:
                next_state[s.id] = pinned[s.id]
                continue

            val, parts = _influence_on(s, incoming_edges.get(s.id, []), state)
            next_state[s.id] = val
            round_contributions[s.id] = parts

            if s.id not in first_wave and abs(val) >= 1.0:
                first_wave[s.id] = round_num

        state = next_state
        last_contributions = round_contributions

    impacts: List[LinearImpact] = []
    for s in graph.species:
        change = round(state.get(s.id, 0.0), 1)
        reasons_raw = last_contributions.get(s.id, [])
        reasons_formatted = [
            f"{species_by_id.get(p[0], s).common_name} ({p[2]}: {p[1]:+.1f}%)"
            for p in sorted(reasons_raw, key=lambda x: abs(x[1]), reverse=True)[:3]
        ]
        impacts.append(
            LinearImpact(
                species_id=s.id,
                common_name=s.common_name,
                change_percent=change,
                wave=first_wave.get(s.id, -1),
                reasons=reasons_formatted,
            )
        )

    # Filter to affected species or pinned inputs, sorted by magnitude
    filtered_impacts = [
        im for im in impacts if im.species_id in pinned or abs(im.change_percent) >= 1.0
    ]
    filtered_impacts.sort(key=lambda im: abs(im.change_percent), reverse=True)

    collapsed = [
        im for im in filtered_impacts
        if im.species_id not in pinned and im.change_percent <= -70.0
    ]

    summary = _build_summary(perturbations, species_by_id, filtered_impacts, len(collapsed))

    return LinearResult(
        impacts=filtered_impacts,
        collapsed_count=len(collapsed),
        summary=summary,
    )


def _influence_on(
    species: Species,
    edges: List[Interaction],
    state: Dict[str, float],
) -> Tuple[float, List[Tuple[str, float, str]]]:
    """Computes total incoming perturbation influence on a species."""
    parts: List[Tuple[str, float, str]] = []

    for edge in edges:
        is_source = edge.source == species.id
        other_id = edge.target if is_source else edge.source
        delta = state.get(other_id, 0.0)
        if abs(delta) < 0.01:
            continue

        amount = 0.0
        reason = ""

        if edge.type == "PREYS_ON":
            if is_source:
                # species is predator, other is prey -> bottom-up
                coeff = COEFF["bottom_up_loss"] if delta < 0 else COEFF["bottom_up_gain"]
                amount = delta * edge.strength * coeff
                reason = "prey loss" if delta < 0 else "prey abundance"
            else:
                # species is prey, other is predator -> top-down
                amount = -delta * edge.strength * COEFF["top_down_release"]
                reason = "reduced predator pressure" if delta < 0 else "increased predation"

        elif edge.type == "MUTUALISM":
            amount = delta * edge.strength * COEFF["mutualism"]
            reason = "mutualist partner"

        elif edge.type == "PARASITISM":
            if is_source:
                # species is parasite, other is host
                amount = delta * edge.strength * COEFF["parasite_on_host_loss"]
                reason = "host density"
            else:
                # species is host, other is parasite
                amount = -delta * edge.strength * COEFF["host_relief_from_parasite"]
                reason = "parasite burden"

        elif edge.type == "COMPETITION":
            amount = -delta * edge.strength * COEFF["competition"]
            reason = "competition pressure"

        elif edge.type == "DECOMPOSES":
            if is_source:
                amount = delta * edge.strength * COEFF["decomposer_substrate"]
                reason = "decomposing biomass"
            else:
                amount = delta * edge.strength * COEFF["nutrient_recycling"]
                reason = "nutrient recycling"

        if abs(amount) >= 0.01:
            parts.append((other_id, amount, reason))

    # Resilience dampens incoming total shock
    damping = 1.0 - (species.resilience * 0.5)
    raw_sum = sum(p[1] for p in parts) * damping
    clamped_val = _clamp(raw_sum, MIN_CHANGE, MAX_CHANGE)
    return clamped_val, parts


def _build_summary(
    perturbations: List[Perturbation],
    species_by_id: Dict[str, Species],
    impacts: List[LinearImpact],
    collapsed_count: int,
) -> str:
    """Generates an ecological natural language synthesis of the cascade."""
    shock_desc = ", ".join(
        f"{species_by_id[p.species_id].common_name} ({p.change_percent:+.0f}%)"
        for p in perturbations
        if p.species_id in species_by_id
    )
    if collapsed_count > 0:
        conclusion = f"Severe trophic cascade: {collapsed_count} species collapsed (>= 70% decline)."
    else:
        conclusion = "Moderate cascade: community absorbed shock without catastrophic collapse."

    return (
        f"Initial shock: {shock_desc}. "
        f"{len(impacts)} species experienced detectable population shifts. "
        f"{conclusion}"
    )

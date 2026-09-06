# EcoGraph Engine

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python Version](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-12%20passed-brightgreen.svg)]()
[![Type Checked](https://img.shields.io/badge/types-pure--python--zero--dependency-success.svg)]()

**EcoGraph Engine** is a high-performance, mathematically rigorous computational framework for modeling, simulating, and analyzing complex ecological networks, food webs, trophic cascades, and keystone species dynamics.

The engine unifies **Allometric Trophic Network (ATN)** continuous non-linear differential equations with **Discrete Linear Wave Propagation** and **Network Centrality / Topological Analysis**.

For complete mathematical derivations and formal proofs, see [SPECIFICATION.md](SPECIFICATION.md) (or [MATH.md](MATH.md)).

---

## Key Capabilities

- **Allometric Trophic Network (ATN) ODE Engine:**
  - Non-linear coupled ordinary differential equations based on Yodzis & Innes (1992) and Brose et al. (2006).
  - **Kleiber's 3/4-Power Law:** Mass-specific metabolic rate scaling ($x_i \propto M_i^{-0.25}$).
  - **Generalized Holling Functional Response:** Hill exponent continuum ($q = 1.2$) bridging Holling Type II and Type III with prey-switching refuges.
  - **Non-Trophic Interactions:** Saturating Michaelis-Menten formulation for mutualism, host-parasite burdens, and metabolic subsidies.
  - **Adaptive 4th-Order Runge-Kutta (RK4):** Richardson step-doubling local error control with extinction thresholding ($10^{-6}$).
  - **Burn-In Attractor Protocol:** Dual-run differential trajectories isolating causal perturbations from intrinsic network oscillations.
- **Discrete Linear Wave Propagation:**
  - Fast turn-based relaxation modeling trophic cascade waves with asymmetric interaction coefficients and resilience damping ($1 - 0.5 \times \rho$).
- **Topological & Network Science Analysis:**
  - **Brandes Betweenness Centrality:** Exact $\mathcal{O}(V \cdot E)$ algorithm.
  - **Power-Iteration Eigenvector Centrality:** Principal eigenvector convergence.
  - **Rarity-Weighted Keystone Scoring:** Robert Paine's criterion scaling topological centrality inversely with baseline biomass abundance.
  - **Levine (1980) Weighted Trophic Positions:** Iterative relaxation accommodating omnivory and cannibalism.
  - **Lindeman Thermodynamic Energy Paths:** Depth-first search (DFS) with node budget pruning.
- **Zero Mandatory External Dependencies:**
  - Built with pure Python standard library for maximum portability and compatibility with Python 3.9 through 3.14+.

---

## Installation

### From Source
```bash
git clone https://github.com/cemyilmazzzz122/ecograph-engine.git
cd ecograph-engine
pip install .
```

### Development / Editable Mode
```bash
pip install -e .
pip install pytest
pytest
```

---

## Quickstart (Python API)

```python
from ecograph import (
    fetch_species,
    identify_keystones,
    simulate_atn,
    simulate_linear,
    yellowstone_trophic_cascade,
    Perturbation,
)

# 1. Fetch biological traits for any species via online APIs (Wikipedia, Wikidata, GBIF)
lion = fetch_species("Lion")
print(f"{lion.common_name} ({lion.scientific_name}): {lion.body_mass_kg} kg, Metabolic Rate: {lion.get_metabolic_rate()}")

# 2. Load canonical Yellowstone National Park food web
graph = yellowstone_trophic_cascade()

# 3. Evaluate Keystone Species
keystones = identify_keystones(graph, limit=5)
for k in keystones:
    print(f"{k.common_name:<25} Keystone Score: {k.score:.4f} (Betweenness: {k.betweenness:.4f})")

# 4. Simulate Trophic Cascade via Continuous ATN (90% Wolf Cull)
result = simulate_atn(
    graph=graph,
    perturbations=[Perturbation(species_id="wolf", change_percent=-90.0)],
    duration=100.0,
    samples=20,
)

for s in result.series:
    print(f"{s.common_name:<25} Dynamic Shift: {s.final_change_percent:+7.2f}% (Extinct: {s.extinct})")
```

---

## Command-Line Interface (CLI)

The package provides a command-line executable `ecograph`:

### 1. Run Ecological Simulations
```bash
# Continuous Allometric Trophic Network (ATN) simulation
ecograph simulate -i @yellowstone -e atn -s "wolf:-80" --duration 100 --samples 20

# Discrete linear wave cascade simulation
ecograph simulate -i @kelp -e linear -s "sea_otter:-100" --steps 5

# Export simulation results to JSON
ecograph simulate -i @yellowstone -e atn -s "wolf:-50" -o results.json
```

### 2. Identify Keystone Species
```bash
ecograph keystone -i @kelp --limit 5
```

### 3. Fetch Biological Traits from Scientific APIs
Automatically resolves taxonomy from GBIF, body mass & IUCN status from Wikidata, and description from Wikipedia:
```bash
# Fetch and inspect biological profile for any species (common or scientific name)
ecograph fetch "Lion"
ecograph fetch "Enhydra lutris"
ecograph fetch "Quaking Aspen" -o aspen.json
```

### 4. Enrich an Entire Food Web Graph
```bash
ecograph enrich -i raw_ecosystem.json -o enriched_ecosystem.json
```

### 5. Food Web Topology & Trophic Levels
```bash
ecograph topology -i @yellowstone
```

### 6. Export Benchmark Datasets
```bash
ecograph dataset yellowstone -o yellowstone.json
ecograph dataset kelp -o kelp.json
```

---

## Theoretical Overview & Mathematical Model

### 1. Allometric Scaling (Kleiber's Law)

The mass-specific metabolic rate $x_i$ scales inversely with body mass:

$$
x_i = a_x \left( \frac{M_i}{M_{\text{ref}}} \right)^{-0.25}
$$

### 2. Generalized Holling Functional Response

Predation intake rates follow a Hill-type functional response:

$$
F_{ij}(\mathbf{B}) = \frac{\omega_{ij} B_j^q}{B_0^q + \sum_{k \in \mathrm{Prey}(i)} \omega_{ik} B_k^q}
$$

where $q = 1.2$ provides empirical ecological persistence by preventing artificial population crashes at low densities.

### 3. Differential Equations ($dB_i/dt$)

**Basal Producers ($i \in \mathcal{P}$):**

$$
\frac{dB_i}{dt} = r_i B_i \left( 1 - \frac{B_i}{K_i} \right) - \sum_{j \in \mathrm{Pred}(i)} \frac{x_j y_j B_j F_{ji}}{e_{ji}} + \mathcal{S}_i(\mathbf{B})
$$

**Consumers ($i \in \mathcal{C}$):**

$$
\frac{dB_i}{dt} = -x_i B_i + x_i y_i B_i \sum_{j \in \mathrm{Prey}(i)} F_{ij} - \sum_{k \in \mathrm{Pred}(i)} \frac{x_k y_k B_k F_{ki}}{e_{ki}} + \mathcal{S}_i(\mathbf{B})
$$

### 4. Keystone Species Index

$$
\mathcal{R}(i) = 1 + 0.6 \log_{10}\left( \frac{100}{\max(P_0(i), 1)} \right)
$$

$$
\mathcal{K}(i) = \left( 0.5 \tilde{C}_B(i) + 0.3 \tilde{C}_E(i) + 0.2 \tilde{C}_D(i) \right) \times \mathcal{R}(i)
$$

For complete mathematical derivations and non-trophic terms, refer to [SPECIFICATION.md](SPECIFICATION.md).

---

## License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.  
See the [LICENSE](LICENSE) file for the full license text.

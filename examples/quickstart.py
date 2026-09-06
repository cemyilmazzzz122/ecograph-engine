"""
EcoGraph Quickstart Example
Demonstrates basic food web simulation and keystone analysis.
"""

from ecograph import (
    identify_keystones,
    simulate_atn,
    simulate_linear,
    yellowstone_trophic_cascade,
    Perturbation,
)

def main():
    # 1. Load canonical Yellowstone food web
    graph = yellowstone_trophic_cascade()
    print(f"Loaded ecosystem: {len(graph.species)} species, {len(graph.interactions)} interactions.")

    # 2. Evaluate Keystone Species
    print("\n--- Identifying Keystone Species ---")
    keystones = identify_keystones(graph, limit=3)
    for k in keystones:
        print(f"Species: {k.common_name:<22} Keystone Score: {k.score:.4f} (Betweenness: {k.betweenness:.4f})")

    # 3. Discrete Trophic Cascade Simulation (Remove 90% of Wolves)
    print("\n--- Discrete Wave Simulation: 90% Wolf Loss ---")
    linear_res = simulate_linear(
        graph,
        perturbations=[Perturbation("wolf", -90.0)],
        steps=5,
    )
    for im in linear_res.impacts:
        print(f"{im.common_name:<22} Shift: {im.change_percent:+6.1f}% (Wave {im.wave})")

    # 4. Continuous Allometric Trophic Network (ATN) ODE Simulation
    print("\n--- Continuous ATN ODE Simulation: 90% Wolf Loss ---")
    atn_res = simulate_atn(
        graph,
        perturbations=[Perturbation("wolf", -90.0)],
        duration=100.0,
        samples=10,
    )
    for s in atn_res.series:
        status = "EXTINCT" if s.extinct else "Surviving"
        print(f"{s.common_name:<22} Dynamic Impact: {s.final_change_percent:+7.2f}% [{status}]")

if __name__ == "__main__":
    main()

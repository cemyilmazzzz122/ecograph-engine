from ecograph.datasets import kelp_forest_marine, yellowstone_trophic_cascade
from ecograph.topology import (
    calculate_connectance,
    calculate_trophic_positions,
    ecosystem_summary,
    trace_food_chains,
)


def test_trophic_positions():
    graph = yellowstone_trophic_cascade()
    tp = calculate_trophic_positions(graph)

    # Producers must be 1.0
    assert tp["willow"] == 1.0
    assert tp["aspen"] == 1.0

    # Herbivores must be 2.0
    assert tp["elk"] == 2.0

    # Wolf must be > 2.0
    assert tp["wolf"] > 2.5


def test_connectance():
    graph = kelp_forest_marine()
    c = calculate_connectance(graph)
    # Directed connectance must be between 0 and 1
    assert 0.0 < c < 1.0


def test_trace_food_chains():
    graph = yellowstone_trophic_cascade()
    chains = trace_food_chains(graph, "wolf", limit=5)
    assert len(chains) > 0
    # Top node in chain should be wolf, basal node should be producer (willow/aspen)
    for ch in chains:
        path = ch["path"]
        assert path[0]["id"] in ["willow", "aspen"]
        assert path[-1]["id"] == "wolf"
        assert ch["energy_reaching"] > 0.0


def test_ecosystem_summary():
    graph = yellowstone_trophic_cascade()
    summary = ecosystem_summary(graph)
    assert summary["species_count"] == 6
    assert summary["interaction_count"] == 6
    assert len(summary["keystone_species"]) > 0

import pytest
from ecograph.centrality import (
    calculate_betweenness,
    calculate_degree,
    calculate_eigenvector,
    identify_keystones,
)
from ecograph.datasets import kelp_forest_marine, yellowstone_trophic_cascade
from ecograph.models import EcosystemGraph, Interaction, Species


def test_degree_centrality():
    graph = yellowstone_trophic_cascade()
    deg = calculate_degree(graph)
    # Elk is preyed upon by wolf, preys on willow and aspen -> connected to 3 species
    assert deg["elk"] >= 3
    assert deg["wolf"] >= 2


def test_betweenness_centrality():
    # Simple line graph: A <-> B <-> C
    # B must have highest betweenness
    graph = EcosystemGraph()
    graph.add_species(Species(id="A", common_name="A"))
    graph.add_species(Species(id="B", common_name="B"))
    graph.add_species(Species(id="C", common_name="C"))
    graph.add_interaction(Interaction(source="B", target="A", type="PREYS_ON"))
    graph.add_interaction(Interaction(source="C", target="B", type="PREYS_ON"))

    bw = calculate_betweenness(graph)
    assert bw["B"] > bw["A"]
    assert bw["B"] > bw["C"]


def test_eigenvector_centrality():
    graph = kelp_forest_marine()
    ev = calculate_eigenvector(graph)
    assert len(ev) == len(graph.species)
    for v in ev.values():
        assert 0.0 <= v <= 1.0


def test_keystone_scoring():
    graph = kelp_forest_marine()
    candidates = identify_keystones(graph)
    assert len(candidates) > 0

    # Sea Otter has low baseline abundance and critical trophic position,
    # so it should rank at or near the top
    top_ids = [c.id for c in candidates[:2]]
    assert "sea_otter" in top_ids

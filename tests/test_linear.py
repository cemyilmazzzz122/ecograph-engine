import pytest
from ecograph.datasets import yellowstone_trophic_cascade
from ecograph.linear import simulate_linear
from ecograph.models import Perturbation


def test_linear_simulation_predator_loss():
    graph = yellowstone_trophic_cascade()

    # Wolf complete extirpation (-100%)
    shocks = [Perturbation(species_id="wolf", change_percent=-100.0)]
    result = simulate_linear(graph, perturbations=shocks, steps=4)

    assert len(result.impacts) > 0
    impact_map = {im.species_id: im.change_percent for im in result.impacts}

    # Wolf loss releases elk from top-down predation -> elk increases
    assert impact_map["elk"] > 0.0

    # Elk increase exerts higher grazing on willow -> willow decreases
    assert impact_map["willow"] < 0.0


def test_linear_simulation_validation():
    graph = yellowstone_trophic_cascade()
    with pytest.raises(ValueError):
        simulate_linear(graph, perturbations=[])

    with pytest.raises(ValueError):
        simulate_linear(graph, perturbations=[Perturbation("non_existent", -50.0)])

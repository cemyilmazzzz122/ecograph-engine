import pytest
from ecograph.atn import simulate_atn
from ecograph.datasets import yellowstone_trophic_cascade
from ecograph.models import AtnParameters, Perturbation


def test_atn_burn_in_and_stability():
    graph = yellowstone_trophic_cascade()

    # Run ATN without external shocks
    result = simulate_atn(
        graph=graph,
        perturbations=[],
        duration=50.0,
        burn_in=200.0,
        samples=20,
    )

    assert result.diagnostics["persisted_species"] > 0
    assert len(result.series) == len(graph.species)
    for s in result.series:
        # Since perturbations was empty, control and perturbed are identical -> final change is 0.0%
        assert abs(s.final_change_percent) < 1e-4


def test_atn_trophic_cascade_perturbation():
    graph = yellowstone_trophic_cascade()

    # Wolf cull by 80%
    shocks = [Perturbation(species_id="wolf", change_percent=-80.0)]
    result = simulate_atn(
        graph=graph,
        perturbations=shocks,
        duration=60.0,
        burn_in=200.0,
        samples=30,
    )

    wolf_series = result.get_series("wolf")
    assert wolf_series is not None
    assert wolf_series.final_change_percent < 0.0

    # Elk should experience release and be positive relative to control
    elk_series = result.get_series("elk")
    assert elk_series is not None
    assert elk_series.final_change_percent > 0.0

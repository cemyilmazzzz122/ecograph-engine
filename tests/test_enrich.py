import pytest
from ecograph.enrich import (
    calculate_kleiber_metabolic_rate,
    enrich_species,
    resolve_species_traits,
)
from ecograph.models import Species


def test_kleiber_metabolic_rate_calculation():
    # Producer must have 0.0
    assert calculate_kleiber_metabolic_rate(50.0, "PRODUCER") == 0.0

    # Small animal (0.05 kg mouse) vs large animal (4000 kg whale)
    small_rate = calculate_kleiber_metabolic_rate(0.05, "PRIMARY_CONSUMER")
    large_rate = calculate_kleiber_metabolic_rate(4000.0, "APEX_PREDATOR")

    # Mass-specific metabolic rate: smaller organism burns more energy per unit mass
    assert small_rate > large_rate
    assert 0.05 <= small_rate <= 0.50
    assert 0.05 <= large_rate <= 0.50


def test_species_metabolic_rate_method():
    sp = Species(
        id="lion",
        common_name="Lion",
        trophic_level="APEX_PREDATOR",
        trophic_rank=4.0,
        body_mass_kg=126.0,
    )
    rate = sp.get_metabolic_rate()
    assert 0.05 <= rate <= 0.50

    producer = Species(
        id="oak",
        common_name="Oak",
        trophic_level="PRODUCER",
        trophic_rank=1.0,
        body_mass_kg=200.0,
    )
    assert producer.get_metabolic_rate() == 0.0


def test_online_traits_resolution():
    try:
        traits = resolve_species_traits("Panthera leo")
    except Exception as e:
        pytest.skip(f"Network unavailable for online test: {e}")

    assert traits["scientific_name"] == "Panthera leo"
    assert traits["body_mass_kg"] > 50.0  # Adult lion > 50kg
    assert traits["trophic_level"] == "APEX_PREDATOR"
    assert traits["taxonomy"]["kingdom"] == "Animalia"
    assert traits["metabolic_rate"] > 0.0


def test_enrich_existing_species():
    sp = Species(
        id="wolf",
        common_name="Gray Wolf",
        scientific_name="Canis lupus",
    )
    assert sp.body_mass_kg is None

    try:
        enrich_species(sp)
    except Exception as e:
        pytest.skip(f"Network unavailable: {e}")

    assert sp.body_mass_kg is not None
    assert sp.body_mass_kg > 0
    assert len(sp.description) > 0

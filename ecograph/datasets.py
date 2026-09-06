"""
Curated benchmark ecological food webs and datasets.
Includes Yellowstone Trophic Cascade, Serengeti Savanna, and Kelp Forest Marine Ecosystems.
"""

from ecograph.models import EcosystemGraph, Interaction, Species


def yellowstone_trophic_cascade() -> EcosystemGraph:
    """
    Constructs the canonical Yellowstone National Park trophic cascade food web.
    Demonstrates apex predator reintroduction dynamics (Gray Wolf -> Elk -> Willow/Aspen -> Beaver).
    """
    graph = EcosystemGraph()

    # Species
    graph.add_species(
        Species(
            id="wolf",
            common_name="Gray Wolf",
            scientific_name="Canis lupus",
            trophic_level="APEX_PREDATOR",
            trophic_rank=4.0,
            body_mass_kg=40.0,
            resilience=0.6,
            baseline_population_index=15.0,  # Rare apex predator
            energy_transfer_efficiency=0.10,
            is_keystone=True,
            keystone_role="Apex predator regulating herbivore density and behavior",
            biomes=["GRASSLAND", "TUNDRA"],
            description="Reintroduced apex predator in Yellowstone.",
        )
    )
    graph.add_species(
        Species(
            id="elk",
            common_name="Rocky Mountain Elk",
            scientific_name="Cervus canadensis",
            trophic_level="PRIMARY_CONSUMER",
            trophic_rank=2.0,
            body_mass_kg=300.0,
            resilience=0.5,
            baseline_population_index=100.0,
            energy_transfer_efficiency=0.10,
            biomes=["GRASSLAND"],
            description="Dominant ungulate herbivore.",
        )
    )
    graph.add_species(
        Species(
            id="willow",
            common_name="Riparian Willow",
            scientific_name="Salix spp.",
            trophic_level="PRODUCER",
            trophic_rank=1.0,
            body_mass_kg=10.0,
            resilience=0.7,
            baseline_population_index=100.0,
            energy_transfer_efficiency=0.12,
            biomes=["FRESHWATER", "GRASSLAND"],
            description="Critical riparian vegetation stabilizing stream banks.",
        )
    )
    graph.add_species(
        Species(
            id="aspen",
            common_name="Quaking Aspen",
            scientific_name="Populus tremuloides",
            trophic_level="PRODUCER",
            trophic_rank=1.0,
            body_mass_kg=150.0,
            resilience=0.6,
            baseline_population_index=100.0,
            energy_transfer_efficiency=0.10,
            biomes=["GRASSLAND"],
            description="Deciduous tree species subject to heavy ungulate browsing.",
        )
    )
    graph.add_species(
        Species(
            id="beaver",
            common_name="North American Beaver",
            scientific_name="Castor canadensis",
            trophic_level="PRIMARY_CONSUMER",
            trophic_rank=2.0,
            body_mass_kg=20.0,
            resilience=0.4,
            baseline_population_index=25.0,
            energy_transfer_efficiency=0.10,
            is_keystone=True,
            keystone_role="Ecosystem engineer creating wetland habitats",
            biomes=["FRESHWATER"],
            description="Riparian engineer relying on willow for food and dam construction.",
        )
    )
    graph.add_species(
        Species(
            id="coyote",
            common_name="Coyote",
            scientific_name="Canis latrans",
            trophic_level="SECONDARY_CONSUMER",
            trophic_rank=3.0,
            body_mass_kg=13.0,
            resilience=0.7,
            baseline_population_index=60.0,
            energy_transfer_efficiency=0.10,
            biomes=["GRASSLAND"],
            description="Mesopredator competing with wolves.",
        )
    )

    # Interactions
    graph.add_interaction(Interaction(source="wolf", target="elk", type="PREYS_ON", strength=0.85))
    graph.add_interaction(Interaction(source="wolf", target="coyote", type="COMPETITION", strength=0.60))
    graph.add_interaction(Interaction(source="elk", target="willow", type="PREYS_ON", strength=0.90))
    graph.add_interaction(Interaction(source="elk", target="aspen", type="PREYS_ON", strength=0.80))
    graph.add_interaction(Interaction(source="beaver", target="willow", type="PREYS_ON", strength=0.50))
    graph.add_interaction(Interaction(source="beaver", target="willow", type="MUTUALISM", strength=0.40, notes="Beavers foster willow seedling beds."))

    return graph


def kelp_forest_marine() -> EcosystemGraph:
    """
    Constructs the classic Pacific Kelp Forest marine food web.
    Demonstrates Robert Paine and James Estes' sea otter keystone species cascade.
    """
    graph = EcosystemGraph()

    graph.add_species(
        Species(
            id="sea_otter",
            common_name="Southern Sea Otter",
            scientific_name="Enhydra lutris",
            trophic_level="SECONDARY_CONSUMER",
            trophic_rank=3.0,
            body_mass_kg=30.0,
            resilience=0.4,
            baseline_population_index=20.0,  # Low biomass keystone
            energy_transfer_efficiency=0.10,
            is_keystone=True,
            keystone_role="Keystone predator preventing sea urchin barren formation",
            biomes=["OCEAN"],
        )
    )
    graph.add_species(
        Species(
            id="sea_urchin",
            common_name="Purple Sea Urchin",
            scientific_name="Strongylocentrotus purpuratus",
            trophic_level="PRIMARY_CONSUMER",
            trophic_rank=2.0,
            body_mass_kg=0.08,
            resilience=0.8,
            baseline_population_index=100.0,
            energy_transfer_efficiency=0.10,
            biomes=["OCEAN"],
        )
    )
    graph.add_species(
        Species(
            id="giant_kelp",
            common_name="Giant Kelp",
            scientific_name="Macrocystis pyrifera",
            trophic_level="PRODUCER",
            trophic_rank=1.0,
            body_mass_kg=5.0,
            resilience=0.6,
            baseline_population_index=100.0,
            energy_transfer_efficiency=0.15,
            biomes=["OCEAN"],
        )
    )
    graph.add_species(
        Species(
            id="orca",
            common_name="Killer Whale",
            scientific_name="Orcinus orca",
            trophic_level="APEX_PREDATOR",
            trophic_rank=4.0,
            body_mass_kg=4000.0,
            resilience=0.5,
            baseline_population_index=5.0,
            energy_transfer_efficiency=0.10,
            biomes=["OCEAN"],
        )
    )
    graph.add_species(
        Species(
            id="garibaldi",
            common_name="Garibaldi",
            scientific_name="Hypsypops rubicundus",
            trophic_level="PRIMARY_CONSUMER",
            trophic_rank=2.0,
            body_mass_kg=0.4,
            resilience=0.6,
            baseline_population_index=80.0,
            energy_transfer_efficiency=0.10,
            biomes=["OCEAN"],
        )
    )

    graph.add_interaction(Interaction(source="orca", target="sea_otter", type="PREYS_ON", strength=0.70))
    graph.add_interaction(Interaction(source="sea_otter", target="sea_urchin", type="PREYS_ON", strength=0.90))
    graph.add_interaction(Interaction(source="sea_urchin", target="giant_kelp", type="PREYS_ON", strength=0.95))
    graph.add_interaction(Interaction(source="garibaldi", target="giant_kelp", type="MUTUALISM", strength=0.30, notes="Shelter and nursery habitat"))

    return graph

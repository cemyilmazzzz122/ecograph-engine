"""
EcoGraph: Mathematical and Ecological Simulation Engine for Complex Food Webs.
"""

__version__ = "1.0.0"
__author__ = "EcoGraph Development Team"
__license__ = "GNU General Public License v3.0 (GPL-3.0)"

from ecograph.atn import AtnModel, simulate_atn
from ecograph.centrality import (
    calculate_betweenness,
    calculate_degree,
    calculate_eigenvector,
    identify_keystones,
)
from ecograph.datasets import kelp_forest_marine, yellowstone_trophic_cascade
from ecograph.enrich import (
    calculate_kleiber_metabolic_rate,
    enrich_ecosystem,
    enrich_species,
    fetch_species,
    resolve_species_traits,
)
from ecograph.linear import simulate_linear
from ecograph.models import (
    AtnParameters,
    AtnResult,
    AtnSeries,
    EcosystemGraph,
    Interaction,
    KeystoneCandidate,
    LinearImpact,
    LinearResult,
    Perturbation,
    Species,
)
from ecograph.topology import (
    calculate_connectance,
    calculate_trophic_positions,
    ecosystem_summary,
    trace_food_chains,
)

__all__ = [
    "__version__",
    "Species",
    "Interaction",
    "EcosystemGraph",
    "Perturbation",
    "AtnParameters",
    "AtnResult",
    "AtnSeries",
    "LinearImpact",
    "LinearResult",
    "KeystoneCandidate",
    "simulate_atn",
    "AtnModel",
    "simulate_linear",
    "calculate_betweenness",
    "calculate_eigenvector",
    "calculate_degree",
    "identify_keystones",
    "calculate_trophic_positions",
    "calculate_connectance",
    "trace_food_chains",
    "ecosystem_summary",
    "yellowstone_trophic_cascade",
    "kelp_forest_marine",
    "resolve_species_traits",
    "fetch_species",
    "enrich_species",
    "enrich_ecosystem",
    "calculate_kleiber_metabolic_rate",
]

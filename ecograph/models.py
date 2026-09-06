"""
Data structures and domain models for EcoGraph.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Species:
    """Represents an ecological species node in the ecosystem network."""
    id: str
    common_name: str
    scientific_name: str = ""
    trophic_level: str = "PRIMARY_CONSUMER"  # PRODUCER, PRIMARY_CONSUMER, SECONDARY_CONSUMER, TERTIARY_CONSUMER, APEX_PREDATOR, DECOMPOSER
    trophic_rank: float = 2.0
    body_mass_kg: Optional[float] = None
    resilience: float = 0.5  # Resistance to perturbation [0, 1]
    baseline_population_index: float = 100.0  # Canonical reference abundance
    energy_transfer_efficiency: float = 0.10  # Lindeman efficiency [0, 1]
    is_keystone: bool = False
    keystone_role: Optional[str] = None
    biomes: List[str] = field(default_factory=list)
    description: str = ""

    def get_metabolic_rate(self, ref_mass_kg: float = 1.0, metabolic_scale: float = 0.314) -> float:
        """Calculates mass-specific metabolic rate via Kleiber's Law."""
        if self.trophic_level == "PRODUCER":
            return 0.0
        import math
        mass = self.body_mass_kg if self.body_mass_kg is not None and self.body_mass_kg > 0 else (
            20.0 ** max(0.0, self.trophic_rank - 2.0)
        )
        raw = metabolic_scale * math.pow(max(mass, 1e-6) / max(ref_mass_kg, 1e-6), -0.25)
        return round(max(0.05, min(0.50, raw)), 4)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["metabolic_rate"] = self.get_metabolic_rate()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Species:
        return cls(
            id=data["id"],
            common_name=data.get("common_name") or data.get("commonName", data["id"]),
            scientific_name=data.get("scientific_name") or data.get("scientificName", ""),
            trophic_level=data.get("trophic_level") or data.get("trophicLevel", "PRIMARY_CONSUMER"),
            trophic_rank=float(data.get("trophic_rank") or data.get("trophicRank", 2.0)),
            body_mass_kg=float(data["body_mass_kg"]) if data.get("body_mass_kg") is not None else (
                float(data["bodyMassKg"]) if data.get("bodyMassKg") is not None else None
            ),
            resilience=float(data.get("resilience", 0.5)),
            baseline_population_index=float(
                data.get("baseline_population_index") or data.get("baselinePopulationIndex", 100.0)
            ),
            energy_transfer_efficiency=float(
                data.get("energy_transfer_efficiency") or data.get("energyTransferEfficiency", 0.10)
            ),
            is_keystone=bool(data.get("is_keystone") or data.get("isKeystone", False)),
            keystone_role=data.get("keystone_role") or data.get("keystoneRole"),
            biomes=list(data.get("biomes", [])),
            description=data.get("description", ""),
        )


@dataclass
class Interaction:
    """Represents a directed ecological interaction edge."""
    source: str  # Predator/Consumer in PREYS_ON, parasite in PARASITISM
    target: str  # Prey/Resource in PREYS_ON, host in PARASITISM
    type: str = "PREYS_ON"  # PREYS_ON, MUTUALISM, PARASITISM, COMPETITION, DECOMPOSES
    strength: float = 1.0  # Weight in (0, 1]
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Interaction:
        return cls(
            source=data["source"],
            target=data["target"],
            type=data.get("type", "PREYS_ON"),
            strength=float(data.get("strength", 1.0)),
            notes=data.get("notes"),
        )


@dataclass
class Perturbation:
    """Defines an external population shock applied to a species."""
    species_id: str
    change_percent: float  # e.g., -50.0 for a 50% decrease, +100.0 for doubling

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EcosystemGraph:
    """Ecosystem food web and interaction network."""
    species: List[Species] = field(default_factory=list)
    interactions: List[Interaction] = field(default_factory=list)

    def add_species(self, species: Species) -> None:
        if self.get_species(species.id) is not None:
            raise ValueError(f"Species with ID '{species.id}' already exists.")
        self.species.append(species)

    def add_interaction(self, interaction: Interaction) -> None:
        self.interactions.append(interaction)

    def get_species(self, species_id: str) -> Optional[Species]:
        for s in self.species:
            if s.id == species_id:
                return s
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "species": [s.to_dict() for s in self.species],
            "interactions": [i.to_dict() for i in self.interactions],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EcosystemGraph:
        species = [Species.from_dict(s) for s in data.get("species", [])]
        interactions = [Interaction.from_dict(i) for i in data.get("interactions", [])]
        return cls(species=species, interactions=interactions)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> EcosystemGraph:
        return cls.from_dict(json.loads(json_str))


@dataclass
class AtnParameters:
    """Biophysical and numerical integration parameters for the ATN model."""
    holling_exponent: float = 1.2
    half_saturation: float = 0.30
    carrying_capacity: float = 1.00
    growth_rate: float = 1.00
    max_consumption: float = 8.00
    herbivore_efficiency: float = 0.45
    carnivore_efficiency: float = 0.85
    metabolic_scale: float = 0.314
    extinction_threshold: float = 1e-6
    mutualism_weight: float = 1.00
    parasite_burden: float = 0.40
    partner_half_saturation: float = 0.05
    mutualist_subsidy: float = 1.40
    metabolic_floor: float = 0.05
    metabolic_ceiling: float = 0.50


@dataclass
class AtnSeries:
    """Time-series trajectory for an individual species."""
    species_id: str
    common_name: str
    trophic_level: str
    values: List[float]  # Percentage change relative to control baseline
    final_change_percent: float
    extinct: bool


@dataclass
class AtnResult:
    """Results produced by the Allometric Trophic Network (ATN) simulation."""
    times: List[float]
    series: List[AtnSeries]
    extinctions: List[Dict[str, Any]]
    diagnostics: Dict[str, Any]

    def get_series(self, species_id: str) -> Optional[AtnSeries]:
        for s in self.series:
            if s.species_id == species_id:
                return s
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "times": self.times,
            "series": [asdict(s) for s in self.series],
            "extinctions": self.extinctions,
            "diagnostics": self.diagnostics,
        }


@dataclass
class LinearImpact:
    """Impact assessment for a species in the discrete linear relaxation model."""
    species_id: str
    common_name: str
    change_percent: float
    wave: int
    reasons: List[str]


@dataclass
class LinearResult:
    """Results produced by the discrete linear relaxation wave simulation."""
    impacts: List[LinearImpact]
    collapsed_count: int
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "impacts": [asdict(im) for im in self.impacts],
            "collapsed_count": self.collapsed_count,
            "summary": self.summary,
        }


@dataclass
class KeystoneCandidate:
    """Keystone species candidate evaluation."""
    id: str
    common_name: str
    betweenness: float
    eigenvector: float
    degree: int
    baseline_population_index: float
    score: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

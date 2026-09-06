"""
Automated Ecological Trait Resolution and Enrichment Engine.
Fetches biological data (taxonomy, body mass, metabolic rates, trophic ranks, IUCN status)
from public scientific APIs: GBIF, Wikipedia REST, and Wikidata Entity Claims.
"""

from __future__ import annotations

import json
import math
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from ecograph.models import EcosystemGraph, Species

UA = "EcoGraph-Engine/1.0 (https://github.com/cemyilmazzzz122/ecograph-engine; mailto:cemyleo3944@gmail.com)"

# Unit conversion multipliers to Kilograms (kg)
MASS_UNIT_MULTIPLIERS: Dict[str, float] = {
    "http://www.wikidata.org/entity/Q11570": 1.0,        # kg
    "http://www.wikidata.org/entity/Q41803": 0.001,      # gram
    "http://www.wikidata.org/entity/Q11574": 1000.0,     # metric ton
    "http://www.wikidata.org/entity/Q100995": 0.453592,  # pound (lb)
    "http://www.wikidata.org/entity/Q483261": 0.0283495, # ounce (oz)
    "http://www.wikidata.org/entity/Q174728": 1e-6,      # milligram
}

# IUCN QID to code mapping
IUCN_QID_MAP: Dict[str, str] = {
    "Q211005": "LC",  # Least Concern
    "Q719675": "NT",  # Near Threatened
    "Q278113": "VU",  # Vulnerable
    "Q11394": "EN",   # Endangered
    "Q219127": "CR",  # Critically Endangered
    "Q239526": "EX",  # Extinct
    "Q237350": "EW",  # Extinct in the Wild
}

# Taxonomic baseline mass estimates (fallback when empirical records are unavailable)
TAXON_BASELINE_MASS_KG: Dict[str, float] = {
    "Mammalia": 15.0,
    "Aves": 0.6,
    "Reptilia": 1.2,
    "Amphibia": 0.05,
    "Actinopterygii": 0.8,
    "Chondrichthyes": 35.0,
    "Insecta": 0.0005,
    "Arachnida": 0.0001,
    "Malacostraca": 0.03,
    "Gastropoda": 0.01,
    "Magnoliopsida": 5.0,
    "Liliopsida": 0.8,
    "Pinopsida": 120.0,
    "Florideophyceae": 0.02,
    "Phaeophyceae": 1.0,
    "Bacillariophyceae": 1e-6,
    "Agaricomycetes": 0.03,
}

# Orders with specialized trophic roles
HERBIVORE_ORDERS = {
    "Artiodactyla", "Perissodactyla", "Rodentia", "Lagomorpha", "Proboscidea", "Sirenia"
}
CARNIVORE_ORDERS = {
    "Carnivora", "Falconiformes", "Accipitriformes", "Strigiformes", "Cetacea"
}


def _http_get_json(url: str, timeout: float = 6.0) -> Optional[Dict[str, Any]]:
    """Safe standard-library HTTP GET helper returning parsed JSON."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    return None


def calculate_kleiber_metabolic_rate(
    body_mass_kg: float,
    trophic_level: str,
    ref_mass_kg: float = 1.0,
    metabolic_scale: float = 0.314,
    floor: float = 0.05,
    ceiling: float = 0.50,
) -> float:
    """
    Computes mass-specific metabolic rate x_i via Kleiber's 3/4-power law:
        x_i = metabolic_scale * (M_i / M_ref)^(-0.25)
    For producers, metabolic loss is implicitly subsumed into net growth (returns 0.0).
    For consumers, metabolic rate is clamped within [floor, ceiling].
    """
    if trophic_level == "PRODUCER":
        return 0.0
    mass = max(body_mass_kg, 1e-6)
    raw = metabolic_scale * math.pow(mass / max(ref_mass_kg, 1e-6), -0.25)
    return round(max(floor, min(ceiling, raw)), 4)


def query_wikipedia_summary(name: str) -> Optional[Dict[str, Any]]:
    """Queries Wikipedia Summary REST API for natural descriptions, titles, and Wikidata QID."""
    clean_name = re.sub(r"\s+spp?\.?$", "", name.strip(), flags=re.IGNORECASE)
    encoded = urllib.parse.quote(clean_name.replace(" ", "_"))
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
    data = _http_get_json(url)
    if data and data.get("type") != "disambiguation" and data.get("extract"):
        return data
    return None


def query_wikidata_claims(qid: str) -> Tuple[List[float], Optional[str], Optional[str]]:
    """
    Queries Wikidata Claims API for an entity:
    Returns (masses_in_kg, iucn_status, scientific_taxon_name).
    """
    url = f"https://www.wikidata.org/w/api.php?action=wbgetclaims&entity={qid}&format=json"
    data = _http_get_json(url)
    if not data or "claims" not in data:
        return [], None, None

    claims = data["claims"]

    # 1. P2067: Mass
    masses: List[float] = []
    for c in claims.get("P2067", []):
        try:
            snak = c.get("mainsnak", {})
            val = snak.get("datavalue", {}).get("value", {})
            if isinstance(val, dict) and "amount" in val:
                amt_str = val["amount"].lstrip("+")
                amt = float(amt_str)
                unit_uri = val.get("unit", "")
                multiplier = MASS_UNIT_MULTIPLIERS.get(unit_uri, 1.0)
                if amt > 0:
                    masses.append(amt * multiplier)
        except Exception:
            continue

    # 2. P141: IUCN Status
    iucn_status: Optional[str] = None
    for c in claims.get("P141", []):
        try:
            target_qid = c.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id")
            if target_qid in IUCN_QID_MAP:
                iucn_status = IUCN_QID_MAP[target_qid]
                break
        except Exception:
            continue

    # 3. P225: Scientific Taxon Name
    scientific_name: Optional[str] = None
    for c in claims.get("P225", []):
        try:
            name_val = c.get("mainsnak", {}).get("datavalue", {}).get("value")
            if isinstance(name_val, str) and name_val.strip():
                scientific_name = name_val.strip()
                break
        except Exception:
            continue

    return masses, iucn_status, scientific_name


def query_gbif_taxonomy(name: str) -> Optional[Dict[str, Any]]:
    """Queries GBIF Backbone Taxonomy matching API."""
    encoded = urllib.parse.quote(name.strip())
    url = f"https://api.gbif.org/v1/species/match?name={encoded}"
    data = _http_get_json(url)
    if data and data.get("matchType") != "NONE" and data.get("kingdom"):
        return data
    return None


def resolve_species_traits(name: str) -> Dict[str, Any]:
    """
    Automated pipeline that fetches and synthesizes biological traits for any species name.
    Queries Wikipedia, Wikidata, and GBIF.
    """
    # 1. Wikipedia summary lookup
    wiki_data = query_wikipedia_summary(name)
    qid: Optional[str] = wiki_data.get("wikibase_item") if wiki_data else None

    # 2. Wikidata claims (mass, IUCN, scientific taxon)
    masses: List[float] = []
    iucn: Optional[str] = None
    wiki_sci_name: Optional[str] = None
    if qid:
        masses, iucn, wiki_sci_name = query_wikidata_claims(qid)

    # 3. GBIF taxonomic hierarchy
    search_taxa = wiki_sci_name or (wiki_data.get("title") if wiki_data else name)
    gbif_data = query_gbif_taxonomy(search_taxa) or query_gbif_taxonomy(name) or {}

    # Extract taxonomy
    kingdom = gbif_data.get("kingdom", "")
    phylum = gbif_data.get("phylum", "")
    cls_name = gbif_data.get("class", "")
    order = gbif_data.get("order", "")
    family = gbif_data.get("family", "")
    scientific_name = wiki_sci_name or gbif_data.get("canonicalName") or gbif_data.get("scientificName") or name

    # Common name resolution
    common_name = name
    if wiki_data and wiki_data.get("title"):
        common_name = wiki_data["title"]

    # 4. Infer body mass (empirical median or taxonomic fallback)
    body_mass_kg: float = 1.0
    if masses:
        sorted_m = sorted(masses)
        mid = len(sorted_m) // 2
        body_mass_kg = sorted_m[mid] if len(sorted_m) % 2 else (sorted_m[mid - 1] + sorted_m[mid]) / 2.0
    else:
        body_mass_kg = TAXON_BASELINE_MASS_KG.get(cls_name, 1.0)
        if kingdom == "Plantae" and cls_name in ["Pinopsida", "Magnoliopsida"]:
            body_mass_kg = 50.0

    # 5. Infer Trophic Level and Rank
    trophic_level = "PRIMARY_CONSUMER"
    trophic_rank = 2.0
    resilience = 0.5
    baseline_pop = 100.0

    if kingdom in ["Plantae", "Chromista"] or phylum in ["Chlorophyta", "Rhodophyta"] or cls_name in ["Phaeophyceae", "Bacillariophyceae"]:
        trophic_level = "PRODUCER"
        trophic_rank = 1.0
        resilience = 0.7
        baseline_pop = 100.0
    elif kingdom == "Fungi":
        trophic_level = "DECOMPOSER"
        trophic_rank = 1.5
        resilience = 0.8
        baseline_pop = 90.0
    elif kingdom == "Animalia":
        if order in CARNIVORE_ORDERS:
            if body_mass_kg >= 25.0:
                trophic_level = "APEX_PREDATOR"
                trophic_rank = 4.0
                resilience = 0.45
                baseline_pop = 15.0
            else:
                trophic_level = "SECONDARY_CONSUMER"
                trophic_rank = 3.0
                resilience = 0.55
                baseline_pop = 40.0
        elif order in HERBIVORE_ORDERS:
            trophic_level = "PRIMARY_CONSUMER"
            trophic_rank = 2.0
            resilience = 0.6
            baseline_pop = 100.0
        else:
            trophic_level = "PRIMARY_CONSUMER"
            trophic_rank = 2.0

    # Compute metabolic rate via Kleiber's Law
    metabolic_rate = calculate_kleiber_metabolic_rate(body_mass_kg, trophic_level)

    # Description
    description = ""
    if wiki_data and wiki_data.get("extract"):
        description = wiki_data["extract"]
    elif gbif_data:
        description = f"{scientific_name} is a member of {family or order or cls_name} ({kingdom})."

    # Normalize ID slug
    slug = re.sub(r"[^a-z0-9_]+", "", name.lower().replace(" ", "_"))

    return {
        "id": slug,
        "common_name": common_name,
        "scientific_name": scientific_name,
        "taxonomy": {
            "kingdom": kingdom,
            "phylum": phylum,
            "class": cls_name,
            "order": order,
            "family": family,
        },
        "trophic_level": trophic_level,
        "trophic_rank": trophic_rank,
        "body_mass_kg": round(body_mass_kg, 4),
        "metabolic_rate": metabolic_rate,
        "resilience": resilience,
        "baseline_population_index": baseline_pop,
        "conservation_status": iucn or "LC",
        "description": description,
    }


def fetch_species(name: str) -> Species:
    """
    Fetches biological traits and taxonomy for a species name via online scientific APIs,
    returning a fully initialized Species domain model.
    """
    data = resolve_species_traits(name)
    return Species(
        id=data["id"],
        common_name=data["common_name"],
        scientific_name=data["scientific_name"],
        trophic_level=data["trophic_level"],
        trophic_rank=data["trophic_rank"],
        body_mass_kg=data["body_mass_kg"],
        resilience=data["resilience"],
        baseline_population_index=data["baseline_population_index"],
        description=data["description"],
    )


def enrich_species(species: Species) -> Species:
    """Enriches an existing Species object if body mass or description is missing."""
    if species.body_mass_kg is not None and species.description:
        return species

    search_term = species.scientific_name or species.common_name
    traits = resolve_species_traits(search_term)

    if species.body_mass_kg is None:
        species.body_mass_kg = traits["body_mass_kg"]
    if not species.description:
        species.description = traits["description"]
    if not species.scientific_name and traits["scientific_name"]:
        species.scientific_name = traits["scientific_name"]

    return species


def enrich_ecosystem(graph: EcosystemGraph) -> EcosystemGraph:
    """Enriches all species in an ecosystem graph with biological traits from APIs."""
    for s in graph.species:
        enrich_species(s)
    return graph

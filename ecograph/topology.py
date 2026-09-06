"""
Topological food web analysis and thermodynamic energy transfer metrics.
Implements Levine (1980) Weighted Trophic Positions, Connectance, and Lindeman Efficiency Paths.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set

from ecograph.models import EcosystemGraph, Species


def calculate_trophic_positions(
    graph: EcosystemGraph, max_rounds: int = 30
) -> Dict[str, float]:
    """
    Computes weighted trophic positions using Levine's (1980) algorithm.
    Primary producers are fixed at level 1.0. Consumers are defined recursively as:
        TP(i) = 1 + sum_j (omega_ij * TP(j))
    Iteratively solved via relaxation with an ecological upper bound of 6.0.
    """
    diet: Dict[str, List[Dict[str, Any]]] = {s.id: [] for s in graph.species}
    for edge in graph.interactions:
        if edge.type == "PREYS_ON":
            diet[edge.source].append({"id": edge.target, "share": edge.strength})

    positions: Dict[str, float] = {s.id: 1.0 for s in graph.species}

    for _ in range(max_rounds):
        for s in graph.species:
            prey = diet.get(s.id, [])
            if not prey:
                continue
            total_share = sum(p["share"] for p in prey) or 1.0
            weighted = sum(
                (p["share"] / total_share) * positions.get(p["id"], 1.0)
                for p in prey
            )
            positions[s.id] = min(1.0 + weighted, 6.0)

    return {k: round(v, 2) for k, v in positions.items()}


def calculate_connectance(graph: EcosystemGraph) -> float:
    """
    Computes directed food web connectance C = L / S^2,
    where L is the number of trophic (PREYS_ON) links and S is total species richness.
    """
    s = len(graph.species)
    if s == 0:
        return 0.0
    trophic_edges = sum(1 for e in graph.interactions if e.type == "PREYS_ON")
    return round(trophic_edges / (s * s), 4)


def trace_food_chains(
    graph: EcosystemGraph, species_id: str, limit: int = 12
) -> List[Dict[str, Any]]:
    """
    Traces trophic energy pathways leading down from a species to primary producers via DFS.
    Calculates path diet weight and Lindeman thermodynamic energy efficiency attenuation.
    Constrained by a node-traversal exploration budget of 120,000 steps.
    """
    species_by_id: Dict[str, Species] = {s.id: s for s in graph.species}
    if species_id not in species_by_id:
        return []

    diet: Dict[str, List[Dict[str, Any]]] = {s.id: [] for s in graph.species}
    for edge in graph.interactions:
        if edge.type == "PREYS_ON":
            diet[edge.source].append({"id": edge.target, "share": edge.strength})

    chains: List[Dict[str, Any]] = []
    budget = 120_000
    explored = 0

    def walk(
        current: str,
        visited: Set[str],
        trail: List[str],
        weight: float,
        energy: float,
    ) -> None:
        nonlocal explored
        if len(chains) >= 400 or len(trail) > 8 or explored > budget:
            return
        explored += 1

        prey = diet.get(current, [])
        curr_sp = species_by_id.get(current)
        if not curr_sp:
            return

        if not prey:
            # Reached a basal node (producer or basal consumer without prey)
            path_nodes = [
                {"id": node_id, "common_name": species_by_id[node_id].common_name}
                for node_id in reversed(trail)
            ]
            chains.append(
                {
                    "path": path_nodes,
                    "weight": round(weight, 5),
                    "energy_reaching": round(energy, 6),
                }
            )
            return

        for step in prey:
            next_id = step["id"]
            if next_id in visited:
                continue
            next_sp = species_by_id.get(next_id)
            if not next_sp:
                continue

            visited.add(next_id)
            walk(
                next_id,
                visited,
                trail + [next_id],
                weight * step["share"],
                energy * next_sp.energy_transfer_efficiency,
            )
            visited.remove(next_id)

    walk(species_id, {species_id}, [species_id], 1.0, 1.0)
    chains.sort(key=lambda c: c["weight"], reverse=True)
    return chains[:limit]


def ecosystem_summary(graph: EcosystemGraph) -> Dict[str, Any]:
    """Generates structural and network statistics for the ecosystem."""
    trophic_positions = calculate_trophic_positions(graph)
    connectance = calculate_connectance(graph)

    by_trophic: Dict[str, int] = {}
    for s in graph.species:
        by_trophic[s.trophic_level] = by_trophic.get(s.trophic_level, 0) + 1

    by_type: Dict[str, int] = {}
    for e in graph.interactions:
        by_type[e.type] = by_type.get(e.type, 0) + 1

    return {
        "species_count": len(graph.species),
        "interaction_count": len(graph.interactions),
        "connectance": connectance,
        "max_trophic_position": max(trophic_positions.values(), default=1.0),
        "species_by_trophic_level": by_trophic,
        "interactions_by_type": by_type,
        "keystone_species": [
            {"id": s.id, "common_name": s.common_name, "role": s.keystone_role}
            for s in graph.species
            if s.is_keystone
        ],
    }

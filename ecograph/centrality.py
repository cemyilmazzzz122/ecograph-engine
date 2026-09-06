"""
Network centrality algorithms and Keystone Species evaluation.
Implements Brandes Betweenness, Power-Iteration Eigenvector, and Rarity-Weighted Keystone Scoring.
"""

from __future__ import annotations

import math
from collections import deque
from typing import Dict, List, Tuple

from ecograph.models import EcosystemGraph, KeystoneCandidate


def _build_undirected_trophic_adjacency(
    graph: EcosystemGraph
) -> Tuple[Dict[str, int], List[List[int]]]:
    """Constructs undirected adjacency list from trophic (PREYS_ON) links."""
    n = len(graph.species)
    id_to_idx = {s.id: i for i, s in enumerate(graph.species)}
    neighbours: List[List[int]] = [[] for _ in range(n)]

    for edge in graph.interactions:
        if edge.type != "PREYS_ON":
            continue
        u = id_to_idx.get(edge.source)
        v = id_to_idx.get(edge.target)
        if u is not None and v is not None and u != v:
            neighbours[u].append(v)
            neighbours[v].append(u)

    # Deduplicate neighbours
    neighbours = [sorted(list(set(adj))) for adj in neighbours]
    return id_to_idx, neighbours


def calculate_betweenness(graph: EcosystemGraph) -> Dict[str, float]:
    """
    Computes normalized betweenness centrality using Brandes' (2001) algorithm.
    Time complexity: O(V * E).
    """
    n = len(graph.species)
    if n == 0:
        return {}
    if n == 1:
        return {graph.species[0].id: 0.0}

    _, neighbours = _build_undirected_trophic_adjacency(graph)
    cb = [0.0] * n

    for s in range(n):
        stack: List[int] = []
        predecessors: List[List[int]] = [[] for _ in range(n)]
        sigma = [0.0] * n
        sigma[s] = 1.0
        distance = [-1] * n
        distance[s] = 0

        queue: deque[int] = deque([s])

        while queue:
            v = queue.popleft()
            stack.append(v)
            for w in neighbours[v]:
                if distance[w] < 0:
                    distance[w] = distance[v] + 1
                    queue.append(w)
                if distance[w] == distance[v] + 1:
                    sigma[w] += sigma[v]
                    predecessors[w].append(v)

        delta = [0.0] * n
        while stack:
            w = stack.pop()
            for v in predecessors[w]:
                delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
            if w != s:
                cb[w] += delta[w]

    # For undirected graphs, every path is counted twice; normalize by 2 / ((n - 1) * (n - 2))
    scale = 2.0 / ((n - 1) * (n - 2)) if n > 2 else 1.0
    return {graph.species[i].id: round(cb[i] * scale, 6) for i in range(n)}


def calculate_eigenvector(
    graph: EcosystemGraph, max_iter: int = 150, tol: float = 1e-10
) -> Dict[str, float]:
    """
    Computes eigenvector centrality via Power Iteration on the trophic adjacency matrix.
    """
    n = len(graph.species)
    if n == 0:
        return {}
    if n == 1:
        return {graph.species[0].id: 1.0}

    _, neighbours = _build_undirected_trophic_adjacency(graph)
    current = [1.0 / math.sqrt(n)] * n

    for _ in range(max_iter):
        next_vec = [0.0] * n
        for v in range(n):
            val = current[v]
            if val == 0.0:
                continue
            for w in neighbours[v]:
                next_vec[w] += val

        norm = math.sqrt(sum(x * x for x in next_vec))
        if norm == 0.0:
            break

        next_vec = [x / norm for x in next_vec]
        drift = sum(abs(next_vec[i] - current[i]) for i in range(n))
        current = next_vec
        if drift < tol:
            break

    return {graph.species[i].id: round(current[i], 6) for i in range(n)}


def calculate_degree(graph: EcosystemGraph) -> Dict[str, int]:
    """Computes total degree centrality (in-degree + out-degree) across all interactions."""
    degrees = {s.id: 0 for s in graph.species}
    for edge in graph.interactions:
        if edge.source in degrees:
            degrees[edge.source] += 1
        if edge.target in degrees:
            degrees[edge.target] += 1
    return degrees


def identify_keystones(
    graph: EcosystemGraph, limit: int = 15
) -> List[KeystoneCandidate]:
    """
    Ranks species by the composite Keystone Species Score.
    Disproportionately weights topological centrality against baseline biomass abundance.
    """
    if not graph.species:
        return []

    bw = calculate_betweenness(graph)
    ev = calculate_eigenvector(graph)
    deg = calculate_degree(graph)

    max_bw = max(max(bw.values(), default=0.0), 1e-12)
    max_ev = max(max(ev.values(), default=0.0), 1e-12)
    max_deg = max(max(deg.values(), default=0), 1)

    candidates: List[KeystoneCandidate] = []

    for s in graph.species:
        b_norm = (bw.get(s.id, 0.0)) / max_bw
        e_norm = (ev.get(s.id, 0.0)) / max_ev
        d_norm = (deg.get(s.id, 0)) / max_deg

        # Rarity multiplier: scaling down abundant dominants and elevating rare keystones
        rarity = 1.0 + math.log10(100.0 / max(s.baseline_population_index, 1.0)) * 0.6

        # Composite score
        score = (0.5 * b_norm + 0.3 * e_norm + 0.2 * d_norm) * rarity

        candidates.append(
            KeystoneCandidate(
                id=s.id,
                common_name=s.common_name,
                betweenness=round(bw.get(s.id, 0.0), 6),
                eigenvector=round(ev.get(s.id, 0.0), 6),
                degree=deg.get(s.id, 0),
                baseline_population_index=s.baseline_population_index,
                score=round(score, 4),
            )
        )

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates[:limit]

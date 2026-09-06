"""
Command-Line Interface (CLI) for EcoGraph Computational Engine.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List

from ecograph.atn import simulate_atn
from ecograph.centrality import (
    calculate_betweenness,
    calculate_degree,
    calculate_eigenvector,
    identify_keystones,
)
from ecograph.datasets import kelp_forest_marine, yellowstone_trophic_cascade
from ecograph.linear import simulate_linear
from ecograph.models import EcosystemGraph, Perturbation
from ecograph.topology import (
    calculate_connectance,
    calculate_trophic_positions,
    ecosystem_summary,
    trace_food_chains,
)


def _load_graph(file_path: str) -> EcosystemGraph:
    """Loads an ecosystem graph from a JSON file or built-in dataset keyword."""
    if file_path == "@yellowstone":
        return yellowstone_trophic_cascade()
    elif file_path == "@kelp":
        return kelp_forest_marine()

    with open(file_path, "r", encoding="utf-8") as f:
        return EcosystemGraph.from_json(f.read())


def cmd_simulate(args: argparse.Namespace) -> None:
    graph = _load_graph(args.input)

    perturbations: List[Perturbation] = []
    if args.shock:
        for item in args.shock:
            parts = item.split(":")
            if len(parts) != 2:
                print(f"Error: Invalid shock format '{item}'. Expected 'species_id:percentage'.", file=sys.stderr)
                sys.exit(1)
            perturbations.append(Perturbation(species_id=parts[0], change_percent=float(parts[1])))

    if args.engine == "atn":
        result = simulate_atn(
            graph=graph,
            perturbations=perturbations,
            duration=args.duration,
            burn_in=args.burn_in,
            samples=args.samples,
        )
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, indent=2)
            print(f"ATN simulation results written to {args.output}")
        else:
            print("\n=== ATN Simulation Results ===")
            print(f"Burn-in: {result.diagnostics['burn_in_duration']} | Persistence: {result.diagnostics['persistence_ratio'] * 100:.1f}%")
            print(f"{'Species':<25} {'Trophic Level':<20} {'Impact (%)':<12} {'Status'}")
            print("-" * 65)
            for s in sorted(result.series, key=lambda x: abs(x.final_change_percent), reverse=True):
                status = "EXTINCT" if s.extinct else "Surviving"
                print(f"{s.common_name:<25} {s.trophic_level:<20} {s.final_change_percent:+10.2f}%   {status}")

    else:
        result = simulate_linear(graph, perturbations=perturbations, steps=args.steps)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, indent=2)
            print(f"Linear simulation results written to {args.output}")
        else:
            print("\n=== Discrete Linear Wave Simulation ===")
            print(f"Summary: {result.summary}")
            print(f"\n{'Species':<25} {'Impact (%)':<12} {'Wave':<6} {'Primary Drivers'}")
            print("-" * 75)
            for im in result.impacts:
                drivers = "; ".join(im.reasons) if im.reasons else "Initial shock"
                print(f"{im.common_name:<25} {im.change_percent:+10.1f}%   {im.wave:<6} {drivers}")


def cmd_keystone(args: argparse.Namespace) -> None:
    graph = _load_graph(args.input)
    candidates = identify_keystones(graph, limit=args.limit)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump([c.to_dict() for c in candidates], f, indent=2)
        print(f"Keystone scores written to {args.output}")
    else:
        print("\n=== Keystone Species Ranking ===")
        print(f"{'Rank':<5} {'Species':<25} {'Score':<10} {'Betweenness':<13} {'Eigenvector':<13} {'Degree'}")
        print("-" * 75)
        for i, c in enumerate(candidates, 1):
            print(f"{i:<5} {c.common_name:<25} {c.score:<10.4f} {c.betweenness:<13.6f} {c.eigenvector:<13.6f} {c.degree}")


def cmd_topology(args: argparse.Namespace) -> None:
    graph = _load_graph(args.input)
    summary = ecosystem_summary(graph)
    positions = calculate_trophic_positions(graph)

    print("\n=== Ecosystem Network Topology ===")
    print(f"Species: {summary['species_count']} | Interactions: {summary['interaction_count']} | Connectance: {summary['connectance']}")
    print(f"Max Trophic Position: {summary['max_trophic_position']}")
    print("\n--- Trophic Positions (Levine 1980) ---")
    for s in sorted(graph.species, key=lambda sp: positions.get(sp.id, 1.0), reverse=True):
        print(f"{s.common_name:<25} (TP: {positions.get(s.id, 1.0):.2f}) - {s.trophic_level}")


def cmd_dataset(args: argparse.Namespace) -> None:
    if args.name == "yellowstone":
        g = yellowstone_trophic_cascade()
    elif args.name == "kelp":
        g = kelp_forest_marine()
    else:
        print(f"Unknown dataset '{args.name}'. Available: yellowstone, kelp", file=sys.stderr)
        sys.exit(1)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(g.to_json())
        print(f"Dataset '{args.name}' exported to {args.output}")
    else:
        print(g.to_json())


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ecograph",
        description="EcoGraph: Mathematical and Ecological Simulation Engine",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # simulate
    p_sim = subparsers.add_parser("simulate", help="Run ecological simulation (ATN or Linear)")
    p_sim.add_argument("-i", "--input", required=True, help="Path to graph JSON or built-in '@yellowstone', '@kelp'")
    p_sim.add_argument("-e", "--engine", choices=["atn", "linear"], default="atn", help="Simulation engine")
    p_sim.add_argument("-s", "--shock", action="append", help="Perturbation in format 'species_id:percent', e.g. -s 'wolf:-100'")
    p_sim.add_argument("-d", "--duration", type=float, default=200.0, help="ATN simulation duration (time units)")
    p_sim.add_argument("-b", "--burn-in", type=float, default=1500.0, help="ATN burn-in stabilization duration")
    p_sim.add_argument("--samples", type=int, default=120, help="ATN output sample points")
    p_sim.add_argument("--steps", type=int, default=6, help="Linear model wave steps")
    p_sim.add_argument("-o", "--output", help="Save output to JSON file")
    p_sim.set_defaults(func=cmd_simulate)

    # keystone
    p_key = subparsers.add_parser("keystone", help="Evaluate keystone species and network centralities")
    p_key.add_argument("-i", "--input", required=True, help="Path to graph JSON or built-in '@yellowstone', '@kelp'")
    p_key.add_argument("-l", "--limit", type=int, default=15, help="Number of candidates to list")
    p_key.add_argument("-o", "--output", help="Save output to JSON file")
    p_key.set_defaults(func=cmd_keystone)

    # topology
    p_top = subparsers.add_parser("topology", help="Analyze food web topology and trophic positions")
    p_top.add_argument("-i", "--input", required=True, help="Path to graph JSON or built-in '@yellowstone', '@kelp'")
    p_top.set_defaults(func=cmd_topology)

    # dataset
    p_dat = subparsers.add_parser("dataset", help="Inspect or export built-in benchmark datasets")
    p_dat.add_argument("name", choices=["yellowstone", "kelp"], help="Dataset name")
    p_dat.add_argument("-o", "--output", help="Export to JSON file")
    p_dat.set_defaults(func=cmd_dataset)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

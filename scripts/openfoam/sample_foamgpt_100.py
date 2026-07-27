#!/usr/bin/env python3
"""Stratified sample of 100 OpenFOAM cases from FoamGPT test split.

Two-level stratification:
  1. case_domain --- allocated more uniformly than population-proportional so
     small physics families still receive meaningful test coverage. Domains
     smaller than their target take all available cases; the residual budget
     is distributed across the large domains (multiphase / incompressible /
     combustion / compressible / heatTransfer) so they retain solver
     diversity rather than being collapsed to one or two solver families.
  2. case_solver within domain --- when sampling inside a domain, every
     solver family present in the test split receives at least one slot if
     the per-domain budget permits, then remaining slots are filled by
     random sample at seed=42 to preserve reproducibility.

The existing 5-task seed42 subset is force-included to preserve continuity
with prior benchmark results.

Outputs:
- configs/openfoam_benchmark/foamgpt_subset_seed42_n100.json (subset config)
- configs/openfoam_benchmark/foamgpt_subset_seed42_n100_summary.json
  (stratification breakdown and pilot 5)
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

DATASET = Path("/home/brianliu/FoamGPT/foamgpt_test.jsonl")
SEED = 42
PILOT_SIZE = 5

# From paper transfer study (Table tab:openfoam-summary); preserved for continuity.
EXISTING_5 = [
    "boundaryWallFunctionsProfile",
    "Grossetete",
    "helmholtzResonance",
    "externalCoupledCavity",
    "damBreakWithObstacle",
]

# Test-split domain sizes (for reference):
#   multiphase=48, incompressible=35, combustion=22, compressible=16,
#   heatTransfer=11, mesh=7, lagrangian=5, discreteMethods=2,
#   molecularDynamics=2, financial=1, DNS=1.
#
# Two pre-baked allocations. Both are deliberately more uniform than the
# population distribution so small physics families still receive meaningful
# coverage; in both, domains smaller than the target take all available
# cases and the residual budget is concentrated in the largest domains to
# preserve solver diversity within them.
DOMAIN_ALLOCATION_BY_SIZE: dict[int, dict[str, int]] = {
    30: {
        "multiphase":        4,
        "incompressible":    4,
        "combustion":        4,
        "compressible":      3,
        "heatTransfer":      3,
        "mesh":              3,
        "lagrangian":        3,
        "discreteMethods":   2,
        "molecularDynamics": 2,
        "financial":         1,
        "DNS":               1,
    },
    100: {
        "multiphase":        20,
        "incompressible":    19,
        "combustion":        16,
        "compressible":      16,
        "heatTransfer":      11,
        "mesh":               7,
        "lagrangian":         5,
        "discreteMethods":    2,
        "molecularDynamics":  2,
        "financial":          1,
        "DNS":                1,
    },
}

# Category-mix target for the 30-case hybrid-diversity subset. This target is
# intentionally approximate rather than mandatory: the search objective tries to
# move the subset toward this mix while preserving the fixed per-domain quotas.
#
# Rationale:
# - the full test split is heavily skewed toward `None`, with several domains
#   containing only `None` labels, so a perfectly balanced category histogram is
#   impossible without sacrificing domain coverage;
# - a realistic hybrid objective should still keep broad solver diversity.
HYBRID_CATEGORY_TARGETS_BY_SIZE: dict[int, dict[str, int]] = {
    30: {
        "None": 15,
        "RAS": 3,
        "laminar": 3,
        "LES": 2,
        "Lagrangian": 2,
        "hopper": 2,
        "cavity": 1,
        "decompressionTank": 1,
        "damBreak": 1,
    }
}

HYBRID_SEARCH_STEPS_BY_SIZE: dict[int, int] = {
    30: 80000,
}


def load_cases() -> dict[str, dict]:
    cases: dict[str, dict] = {}
    with DATASET.open() as fh:
        for line in fh:
            d = json.loads(line)
            name = d["case_name"]
            if name not in cases:
                cases[name] = {
                    "case_name": name,
                    "case_domain": d["case_domain"],
                    "case_category": d["case_category"],
                    "case_solver": d["case_solver"],
                    "required_files": [],
                }
            cases[name]["required_files"].append(f"{d['folder_name']}/{d['file_name']}")
    for info in cases.values():
        info["required_files"].sort()
        info["n_files"] = len(info["required_files"])
    return cases


def _sample_within_domain(
    *,
    pool: list[str],
    quota: int,
    forced: list[str],
    cases: dict[str, dict],
    rng: random.Random,
) -> list[str]:
    """Sample ``quota`` case names from ``pool`` while spreading across solver
    families. ``forced`` entries are always kept (and counted toward quota).
    Step 1 picks one fresh case per solver family that the forced set does
    not already cover, in random order. Step 2 fills remaining slots with a
    uniform random sample over the still-unused remainder."""
    forced_set = set(forced)
    remaining_quota = max(0, quota - len(forced_set))
    available = [name for name in pool if name not in forced_set]
    if remaining_quota >= len(available):
        return sorted(forced_set | set(available))

    by_solver: dict[str, list[str]] = defaultdict(list)
    for name in available:
        by_solver[cases[name]["case_solver"]].append(name)
    for names in by_solver.values():
        names.sort()

    covered_solvers = {cases[name]["case_solver"] for name in forced_set}
    selected: set[str] = set()
    solver_order = list(by_solver.keys())
    rng.shuffle(solver_order)
    for solver in solver_order:
        if len(selected) >= remaining_quota:
            break
        if solver in covered_solvers:
            continue
        pick = rng.choice(by_solver[solver])
        selected.add(pick)
        covered_solvers.add(solver)

    leftover = [name for name in available if name not in selected]
    rng.shuffle(leftover)
    for name in leftover:
        if len(selected) >= remaining_quota:
            break
        selected.add(name)

    return sorted(forced_set | selected)


def _hybrid_score(
    *,
    chosen: list[str],
    cases: dict[str, dict],
    category_targets: dict[str, int],
) -> int:
    """Score a subset for hybrid diversity.

    Objective:
    - preserve broad solver-family coverage;
    - increase the number of meaningful category labels represented;
    - reduce the over-representation of `None`;
    - move the category histogram toward the configured target.
    """
    category_counts = Counter(cases[name]["case_category"] for name in chosen)
    solver_count = len({cases[name]["case_solver"] for name in chosen})
    represented_target_categories = sum(
        1 for category in category_targets if category_counts[category] > 0
    )
    all_categories = {info["case_category"] for info in cases.values()}

    weights = {category: (12 if category in category_targets else 2) for category in all_categories}
    weights["None"] = 12
    weights["RAS"] = 8
    weights["laminar"] = 8
    weights["LES"] = 10
    weights["Lagrangian"] = 10
    weights["hopper"] = 10
    weights["cavity"] = 8
    weights["decompressionTank"] = 8
    weights["damBreak"] = 8

    penalty = 0
    for category in all_categories:
        penalty += weights[category] * abs(category_counts[category] - category_targets.get(category, 0))

    return (
        22 * solver_count
        + 40 * represented_target_categories
        - penalty
    )


def sample_hybrid_diversity(
    cases: dict[str, dict],
    allocation: dict[str, int],
    sample_size: int,
) -> list[str]:
    """Fixed-domain, local-search hybrid sampler.

    Start from the existing domain/solver-balanced sampler, then swap cases
    within each domain when the swap improves the hybrid diversity objective.
    Domain quotas remain unchanged throughout the search.
    """
    category_targets = HYBRID_CATEGORY_TARGETS_BY_SIZE.get(sample_size)
    search_steps = HYBRID_SEARCH_STEPS_BY_SIZE.get(sample_size)
    if not category_targets or not search_steps:
        raise RuntimeError(f"Hybrid diversity strategy is not configured for size={sample_size}")

    chosen = sample_stratified(cases, allocation, sample_size)
    chosen_set = set(chosen)

    by_domain: dict[str, list[str]] = defaultdict(list)
    for name, info in cases.items():
        by_domain[info["case_domain"]].append(name)
    for names in by_domain.values():
        names.sort()

    rng = random.Random(SEED)
    best = list(chosen)
    best_set = set(best)
    best_score = _hybrid_score(chosen=best, cases=cases, category_targets=category_targets)
    domains = list(allocation.keys())

    for _ in range(search_steps):
        domain = rng.choice(domains)
        selected_in_domain = [name for name in best if cases[name]["case_domain"] == domain]
        available_in_domain = [name for name in by_domain[domain] if name not in best_set]
        if not selected_in_domain or not available_in_domain:
            continue

        outgoing = rng.choice(selected_in_domain)
        incoming = rng.choice(available_in_domain)

        candidate = [name for name in best if name != outgoing]
        candidate.append(incoming)
        candidate_score = _hybrid_score(
            chosen=candidate,
            cases=cases,
            category_targets=category_targets,
        )
        if candidate_score > best_score:
            best = candidate
            best_set.remove(outgoing)
            best_set.add(incoming)
            best_score = candidate_score

    if len(best) != sample_size:
        raise RuntimeError(f"Expected {sample_size} cases after hybrid search, got {len(best)}")
    return sorted(best)


def sample_stratified(
    cases: dict[str, dict],
    allocation: dict[str, int],
    sample_size: int,
) -> list[str]:
    by_domain: dict[str, list[str]] = defaultdict(list)
    for name, info in cases.items():
        by_domain[info["case_domain"]].append(name)
    for names in by_domain.values():
        names.sort()

    rng = random.Random(SEED)
    chosen: list[str] = []
    for domain, quota in allocation.items():
        pool = by_domain.get(domain, [])
        forced = [name for name in EXISTING_5 if name in pool]
        domain_sample = _sample_within_domain(
            pool=pool, quota=quota, forced=forced, cases=cases, rng=rng
        )
        chosen.extend(domain_sample)

    if len(chosen) != sample_size:
        raise RuntimeError(f"Expected {sample_size} cases, got {len(chosen)}")
    return chosen


def pick_pilot(chosen: list[str]) -> list[str]:
    """Pick a pilot of fresh cases (not in EXISTING_5) for the smoke run."""
    rng = random.Random(SEED + 1)
    pool = [name for name in chosen if name not in EXISTING_5]
    return sorted(rng.sample(pool, PILOT_SIZE))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--size",
        type=int,
        default=30,
        choices=sorted(DOMAIN_ALLOCATION_BY_SIZE.keys()),
        help="Number of cases to sample (must have a pre-baked uniform allocation).",
    )
    parser.add_argument(
        "--strategy",
        choices=("domain_solver_uniform", "hybrid_diversity"),
        default="domain_solver_uniform",
        help="Sampling strategy to use.",
    )
    parser.add_argument(
        "--suffix",
        default=None,
        help="Optional subset-name suffix override, e.g. n30_hybrid.",
    )
    args = parser.parse_args()

    allocation = DOMAIN_ALLOCATION_BY_SIZE[args.size]
    sample_size = args.size
    cases = load_cases()
    if args.strategy == "hybrid_diversity":
        chosen = sample_hybrid_diversity(cases, allocation, sample_size)
    else:
        chosen = sample_stratified(cases, allocation, sample_size)
    pilot = pick_pilot(chosen)

    # Stratification summary
    domain_counts = Counter(cases[name]["case_domain"] for name in chosen)
    solver_counts = Counter(cases[name]["case_solver"] for name in chosen)
    category_counts = Counter(cases[name]["case_category"] for name in chosen)

    repo_root = Path(__file__).resolve().parents[2]
    if args.suffix:
        suffix = args.suffix
    elif args.strategy == "hybrid_diversity":
        suffix = f"n{sample_size}_hybrid"
    else:
        suffix = f"n{sample_size}"
    config_path = repo_root / "configs" / "openfoam_benchmark" / f"foamgpt_subset_seed42_{suffix}.json"
    summary_path = repo_root / "configs" / "openfoam_benchmark" / f"foamgpt_subset_seed42_{suffix}_summary.json"

    subset_name = f"foamgpt_subset_seed42_{suffix}"
    config = {
        "subset_name": subset_name,
        "dataset_path": str(DATASET),
        "selection": {
            "method": args.strategy,
            "seed": SEED,
            "sample_size": sample_size,
            "domain_allocation": allocation,
        },
        "model": {
            "provider": "openrouter",
            "model": "deepseek/deepseek-v4-flash",
            "anthropic_base_url": "https://openrouter.ai/api/anthropic",
        },
        "cases": chosen,
        "pilot_5": pilot,
    }
    if args.strategy == "domain_solver_uniform":
        config["selection"]["existing_5_forced"] = EXISTING_5
    if args.strategy == "hybrid_diversity":
        config["selection"]["hybrid_category_targets"] = HYBRID_CATEGORY_TARGETS_BY_SIZE[sample_size]
        config["selection"]["hybrid_search_steps"] = HYBRID_SEARCH_STEPS_BY_SIZE[sample_size]

    summary = {
        "subset_name": subset_name,
        "n_cases": len(chosen),
        "strategy": args.strategy,
        "pilot_5": pilot,
        "by_domain": dict(sorted(domain_counts.items(), key=lambda kv: -kv[1])),
        "by_category": dict(sorted(category_counts.items(), key=lambda kv: -kv[1])),
        "by_solver": dict(sorted(solver_counts.items(), key=lambda kv: -kv[1])),
        "cases_with_metadata": [
            {
                "case_name": name,
                "case_domain": cases[name]["case_domain"],
                "case_category": cases[name]["case_category"],
                "case_solver": cases[name]["case_solver"],
                "n_files": cases[name]["n_files"],
                "required_files": cases[name]["required_files"],
            }
            for name in chosen
        ],
    }

    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {config_path}")
    print(f"wrote {summary_path}")
    print(f"n_cases={len(chosen)}  pilot={pilot}")
    print("by_domain:", dict(domain_counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

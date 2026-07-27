# OpenFOAM `n100` Pilot-5 Results

Date: 2026-05-26 UTC

## Artifacts

- 100-task subset config: `configs/openfoam_benchmark/foamgpt_subset_seed42_n100.json`
- 100-task subset summary with categories and chosen simulations: `configs/openfoam_benchmark/foamgpt_subset_seed42_n100_summary.json`
- Pilot run dir: `data/openfoam_runs/repo3_openfoam_ablations/openfoam_n100_pilot5_20260526c`
- Raw scorer output: `data/openfoam_runs/repo3_openfoam_ablations/openfoam_n100_pilot5_20260526c/pilot5_scores.json`
- Compact pilot summary: `data/openfoam_runs/repo3_openfoam_ablations/openfoam_n100_pilot5_20260526c/pilot5_summary.json`
- Recomputed token/cost ledger: `data/openfoam_runs/repo3_openfoam_ablations/openfoam_n100_pilot5_20260526c/pilot5_token_cost_recomputed.json`

## Pilot Scope

Model: `deepseek/deepseek-v4-flash`

Run shape:

- 9 SIGA cells
- 5 pilot tasks
- `--num-workers 5`
- `--cell-workers 3`

Pilot tasks:

| Case | Domain | Solver | Required files |
|---|---|---|---:|
| `DLR_A_LTS` | combustion | `reactingFoam` | 2 |
| `T3A` | incompressible | `simpleFoam` | 3 |
| `biconic25-55Run35` | compressible | `rhoCentralFoam` | 1 |
| `dahl` | multiphase | `driftFluxFoam` | 3 |
| `freeSpacePeriodic` | discreteMethods | `dsmcFoam` | 3 |

## Run Outcome

- All 45 task-runs completed successfully.
- Timeouts: 0
- Run wall-clock: 37.4 min
- Aggregate per-task wall time: 4.27 h
- Total tokens across all 45 task-runs: `56,698,685` input, `988,753` output
- Cache-read input tokens reported separately: `980,225`
- Recomputed OpenRouter spend at listed `deepseek/deepseek-v4-flash` pricing: `$5.867619`
- Artifact-emitted `total_cost_usd` sum: `$312.606853` (`53.3x` higher than the token-based recomputation)

Scoring note:

- `all100_mean` is the paper-style failure-as-zero score over the full 100-case subset root.
- Because only 5 of the 100 cases were run in this pilot, 95 cases score 0 by construction.
- `pilot5_mean` is the same file-text-and-coverage metric restricted to the 5 executed cases.

Costing note:

- OpenRouter currently lists `deepseek/deepseek-v4-flash` at `$0.10 / 1M` input tokens and `$0.20 / 1M` output tokens.
- Recomputed cost formula: `(input_tokens * 0.10 + output_tokens * 0.20) / 1,000,000`.
- I treated all reported input tokens as billable input because the model page does not publish a separate cache-read token price.
- If cache-read tokens were free, the total would drop slightly further to `$5.769597`.

## Cell Summary

All cells achieved mean coverage `1.000` on the 5 executed tasks. Differences are therefore driven by text similarity, not missing required files.

| Cell | `pilot5_mean` | `all100_mean` | Recomputed cost | Mean wall/task | Mean tools/task |
|---|---:|---:|---:|---:|---:|
| `s+x+m` | 0.879 | 0.0439 | $1.064 | 505s | 112.0 |
| `s+m` | 0.878 | 0.0439 | $1.192 | 580s | 88.0 |
| `r+s+x+m` | 0.863 | 0.0431 | $0.478 | 289s | 96.4 |
| `r+s` | 0.863 | 0.0431 | $0.318 | 277s | 67.2 |
| `s+x` | 0.852 | 0.0426 | $1.337 | 494s | 114.2 |
| `r+m` | 0.754 | 0.0377 | $0.137 | 172s | 58.8 |
| `r+x` | 0.753 | 0.0376 | $0.349 | 212s | 81.0 |
| `vanilla` | 0.737 | 0.0369 | $0.529 | 292s | 57.6 |
| `x+m` | 0.736 | 0.0368 | $0.463 | 252s | 52.0 |

## Per-Task Breakdown

| Case | Best cell | Best score | Worst cell | Worst score | Mean over 9 cells |
|---|---|---:|---|---:|---:|
| `DLR_A_LTS` | `s+x+m` | 0.901 | `vanilla` / `r+m` / `x+m` / `r+x` | 0.699 | 0.808 |
| `T3A` | `r+s` / `r+s+x+m` | 0.965 | `vanilla` / `r+m` / `x+m` / `r+x` | 0.675 | 0.823 |
| `biconic25-55Run35` | `vanilla` | 0.810 | `s+x` | 0.741 | 0.782 |
| `dahl` | `s+x+m` | 0.948 | `x+m` | 0.729 | 0.872 |
| `freeSpacePeriodic` | `s+m` / `s+x+m` | 0.883 | `vanilla` | 0.685 | 0.777 |

## Takeaways

- Best pilot cell by accuracy: `s+x+m` with `pilot5_mean = 0.879`.
- `s+m` is essentially tied on accuracy (`0.878`) but is slightly more expensive than `s+x+m`.
- `r+s` is a strong efficiency point: `0.863` at `$0.318`, much cheaper than the top two cells.
- `s+x` is the most expensive cell under the recomputation (`$1.337`) and did not beat `s+m` or `s+x+m`.
- Retrieval-only additions were weak on this pilot: `r+m` and `r+x` improved over `vanilla`, but much less than stop-hook-containing cells.
- No full-task exact matches occurred, but some cells achieved partial exact file matches:
  - `r+s` and `r+s+x+m` hit `1/3` exact files on `T3A`.
  - `r+s+x+m` and `s+x+m` hit `1/2` exact files on `DLR_A_LTS`.

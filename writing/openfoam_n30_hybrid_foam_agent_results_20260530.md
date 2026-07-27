# Foam Agent 2.0 — n30_hybrid (token-instrumented re-run)

Evaluation date: 2026-05-30. Model: `deepseek/deepseek-v4-flash` via OpenRouter. Execution mode: lint-only. Benchmark: `foamgpt_subset_seed42_n30_hybrid` (30 tasks). Parallelism: 15 tasks concurrently. Per-task timeout: 1500s. Metric: file-text similarity + required-file coverage. Cost from OpenRouter DeepSeek V4 Flash effective pricing on 2026-05-30: input `$0.0983/M`, output `$0.1966/M` ([source](https://openrouter.ai/deepseek/deepseek-v4-flash)).

This re-run fixes Foam Agent token/tool accounting. Previously its wrapper counted `str(PydanticObject)` for structured-output completions (badly under-counting), reported only one of the several `LLMService` instances it constructs per task, and skipped `print_statistics` when the workflow raised. The patched `LLMService` now: (1) reads **real provider usage metadata** (`usage_metadata` / `response_metadata['token_usage']`) on every call; (2) aggregates across **all** `LLMService` instances in the task process via class-level counters; and (3) writes a running ledger (`llm_stats.json`) after every call so usage survives mid-workflow crashes. `tool_calls` here means real `LLMService.invoke()` calls (`llm_service_calls`).

## Summary

| Metric | Value |
|---|---:|
| Cases | 30 |
| Mean overall score | 0.5157 |
| Mean coverage | 0.6767 |
| Full-coverage cases | 19 |
| Partial-coverage cases | 3 |
| Zero-coverage cases | 8 |
| Zero-score cases | 8 |
| Success / failed / timeout | 21 / 9 / 0 |
| Mean wall time per task | 373.0 s |
| Mean LLM calls per task | 18.73 |
| Total input tokens | 1,899,925 |
| Total output tokens | 596,006 |
| Total tokens | 2,495,931 |
| Estimated OpenRouter cost | $0.3039 |

**Token reliability:** 29/30 tasks are 100% API-sourced with zero tiktoken fallbacks (mean estimated-usage calls per task = 0.0). The lone exception, `periodicCubeArgon`, crashed on its first LLM call and recorded 0 tokens. The earlier run's "140 total output tokens across 30 tasks" figure is fully superseded: the real total is 596,006 output / 1,899,925 input tokens. Mean LLM calls per task rose from the previously-reported 2.0 to **18.73**, because the old counter saw only a single service instance.

## Domain breakdown

| Domain | n | Mean score | Mean coverage |
|---|---:|---:|---:|
| DNS | 1 | 0.875 | 1.000 |
| financial | 1 | 0.874 | 1.000 |
| compressible | 3 | 0.748 | 1.000 |
| lagrangian | 3 | 0.723 | 1.000 |
| incompressible | 4 | 0.662 | 0.750 |
| combustion | 4 | 0.580 | 0.750 |
| mesh | 3 | 0.538 | 0.733 |
| multiphase | 4 | 0.462 | 0.625 |
| molecularDynamics | 2 | 0.231 | 0.500 |
| heatTransfer | 3 | 0.138 | 0.200 |
| discreteMethods | 2 | 0.000 | 0.000 |

## Per-case results

| Case | Domain | Solver | Status | Score | Cov | Sim | Missing | LLM calls | Input tok | Output tok | Total tok | Cost |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aachenBomb | combustion | reactingFoam | success | 0.000 | 0.00 | 0.000 | 2/2 | 34 | 171,117 | 31,895 | 203,012 | $0.0231 |
| angledDuctExplicitFixedCoeff | compressible | rhoSimpleFoam | success | 0.571 | 1.00 | 0.387 | 0/1 | 22 | 67,292 | 29,372 | 96,664 | $0.0124 |
| boxTurb16 | DNS | dnsFoam | success | 0.875 | 1.00 | 0.821 | 0/1 | 18 | 37,633 | 13,032 | 50,665 | $0.0063 |
| cavityClipped | incompressible | icoFoam | success | 0.917 | 1.00 | 0.882 | 0/1 | 15 | 29,877 | 18,951 | 48,828 | $0.0067 |
| channel395 | incompressible | pimpleFoam | success | 0.817 | 1.00 | 0.739 | 0/2 | 22 | 68,933 | 17,121 | 86,054 | $0.0101 |
| coolingSphere | heatTransfer | chtMultiRegionFoam | failed | 0.000 | 0.00 | 0.000 | 1/1 | 2 | 927 | 46 | 973 | $0.0001 |
| cyclone | lagrangian | denseParticleFoam | success | 0.510 | 1.00 | 0.300 | 0/1 | 22 | 66,476 | 16,895 | 83,371 | $0.0099 |
| dahl | multiphase | driftFluxFoam | failed | 0.000 | 0.00 | 0.000 | 3/3 | 2 | 1,042 | 53 | 1,095 | $0.0001 |
| damBreak | multiphase | interFoam | failed | 0.841 | 1.00 | 0.773 | 0/2 | 23 | 70,386 | 35,047 | 105,433 | $0.0138 |
| damBreak4phase | multiphase | compressibleMultiphaseInterFoam | failed | 0.677 | 1.00 | 0.539 | 0/5 | 39 | 250,958 | 30,317 | 281,275 | $0.0306 |
| decompressionTank | compressible | rhoPimpleFoam | success | 0.838 | 1.00 | 0.768 | 0/1 | 20 | 50,723 | 21,789 | 72,512 | $0.0093 |
| europeanCall | financial | financialFoam | success | 0.874 | 1.00 | 0.820 | 0/2 | 14 | 22,235 | 9,297 | 31,532 | $0.0040 |
| externalCoupledCavity | heatTransfer | buoyantFoam | success | 0.414 | 0.60 | 0.334 | 2/5 | 24 | 74,050 | 22,219 | 96,269 | $0.0116 |
| freeSpacePeriodic | discreteMethods | dsmcFoam | success | 0.000 | 0.00 | 0.000 | 3/3 | 16 | 31,347 | 14,394 | 45,741 | $0.0059 |
| hopperEmptying | lagrangian | particleFoam | success | 0.772 | 1.00 | 0.675 | 0/2 | 21 | 54,247 | 34,907 | 89,154 | $0.0122 |
| hopperInitialState | lagrangian | particleFoam | success | 0.887 | 1.00 | 0.839 | 0/2 | 20 | 80,989 | 32,389 | 113,378 | $0.0143 |
| hotRoomBoussinesqSteady | heatTransfer | buoyantFoam | failed | 0.000 | 0.00 | 0.000 | 1/1 | 2 | 1,010 | 47 | 1,057 | $0.0001 |
| LadenburgJet60psi | compressible | rhoCentralFoam | success | 0.834 | 1.00 | 0.764 | 0/2 | 22 | 57,152 | 26,719 | 83,871 | $0.0109 |
| moriyoshiHomogeneous | combustion | XiFoam | failed | 0.845 | 1.00 | 0.778 | 0/2 | 28 | 105,193 | 20,183 | 125,376 | $0.0143 |
| nc7h16 | combustion | chemFoam | success | 0.621 | 1.00 | 0.458 | 0/1 | 17 | 33,337 | 18,267 | 51,604 | $0.0069 |
| periodicCubeArgon | molecularDynamics | mdEquilibrationFoam | failed | 0.000 | 0.00 | 0.000 | 2/2 | 1 | 0 | 0 | 0 | $0.0000 |
| periodicCubeWater | molecularDynamics | mdEquilibrationFoam | success | 0.462 | 1.00 | 0.232 | 0/1 | 18 | 40,687 | 22,432 | 63,119 | $0.0084 |
| porousBlockage | incompressible | pisoFoam | success | 0.915 | 1.00 | 0.878 | 0/1 | 19 | 40,592 | 14,136 | 54,728 | $0.0068 |
| refineFieldDirs | mesh | refineMesh | failed | 0.149 | 0.20 | 0.127 | 4/5 | 13 | 16,295 | 25,002 | 41,297 | $0.0065 |
| simpleShapes | mesh | foamyHexMesh | failed | 0.850 | 1.00 | 0.785 | 0/1 | 17 | 34,229 | 11,907 | 46,136 | $0.0057 |
| sphere7ProjectedEdges | mesh | blockMesh | success | 0.614 | 1.00 | 0.449 | 0/1 | 12 | 18,284 | 24,142 | 42,426 | $0.0065 |
| splashPanel | combustion | buoyantReactingFoam | success | 0.856 | 1.00 | 0.795 | 0/2 | 41 | 312,191 | 40,893 | 353,084 | $0.0387 |
| squareBump | incompressible | shallowWaterFoam | success | 0.000 | 0.00 | 0.000 | 2/2 | 20 | 53,177 | 21,054 | 74,231 | $0.0094 |
| supersonicCorner | discreteMethods | dsmcFoam | success | 0.000 | 0.00 | 0.000 | 4/4 | 15 | 30,173 | 12,277 | 42,450 | $0.0054 |
| throttle3D | multiphase | cavitatingFoam | success | 0.330 | 0.50 | 0.258 | 1/2 | 23 | 79,373 | 31,223 | 110,596 | $0.0139 |

## Failure analysis

- 9/30 tasks exited nonzero: `coolingSphere`, `dahl`, `damBreak`, `damBreak4phase`, `hotRoomBoussinesqSteady`, `moriyoshiHomogeneous`, `periodicCubeArgon`, `refineFieldDirs`, `simpleShapes`.
- Several failed tasks still produced complete, well-scoring file trees before the workflow raised (e.g. `damBreak` 0.841, `moriyoshiHomogeneous` 0.845, `simpleShapes` 0.850) — the nonzero exit is a late structured-output/command-generation schema error, not a generation failure. The per-call gap between `tool_calls` and `api_usage_calls` on those tasks (1 call) is exactly that failing final call.
- The catastrophic zero-score cases are dominated by **missing required files** rather than crashes: `freeSpacePeriodic`, `squareBump`, `supersonicCorner`, and `aachenBomb` completed successfully but omitted required paths; the file-coverage metric penalizes that heavily.
- `coolingSphere`, `dahl`, `hotRoomBoussinesqSteady`, and `periodicCubeArgon` crashed early (1-2 LLM calls), so their token counts are correspondingly tiny — now visible rather than hidden by broken accounting.

## Artifacts

- Run root: `data/openfoam_runs/foam_agent/openfoam_n30_hybrid_foam_agent_lint_20260530_tok`
- Scores: `data/openfoam_runs/foam_agent/openfoam_n30_hybrid_foam_agent_lint_20260530_tok/n30_hybrid_scores.json`
- Run summary: `data/openfoam_runs/foam_agent/openfoam_n30_hybrid_foam_agent_lint_20260530_tok/run_summary.json`
- Per-task token ledger: `<run>/<task>/llm_stats.json`

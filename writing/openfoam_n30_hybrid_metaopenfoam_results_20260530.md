# MetaOpenFOAM — n30_hybrid (token-instrumented re-run)

Evaluation date: 2026-05-30. Model: `deepseek/deepseek-v4-flash` via OpenRouter. Execution mode: lint-only. Benchmark: `foamgpt_subset_seed42_n30_hybrid` (30 tasks). Parallelism: 15 tasks concurrently. Per-task timeout: 1500s. Metric: file-text similarity + required-file coverage. Cost from OpenRouter DeepSeek V4 Flash effective pricing on 2026-05-30: input `$0.0983/M`, output `$0.1966/M` ([source](https://openrouter.ai/deepseek/deepseek-v4-flash)).

This re-run adds **robust mean tool-call tracking** for MetaOpenFOAM. Its token counts were already real (summed from LangChain `usage_metadata`), but `tool_calls` was a stdout proxy that fired once per run. It is now the count of actual LLM invocations (`metaopenfoam_llm_calls`), parsed from the one `DeepSeek response keys:` line that its deepseek path prints per model call. Cost is computed from the logged input/output tokens.

## Summary

| Metric | Value |
|---|---:|
| Cases | 30 |
| Mean overall score | 0.3794 |
| Mean coverage | 0.4756 |
| Full-coverage cases | 10 |
| Partial-coverage cases | 8 |
| Zero-coverage cases | 12 |
| Zero-score cases | 12 |
| Success / failed / timeout | 27 / 3 / 0 |
| Mean wall time per task | 431.5 s |
| Mean LLM calls per task | 11.43 |
| Total input tokens | 388,420 |
| Total output tokens | 646,566 |
| Total tokens | 1,034,986 |
| Estimated OpenRouter cost | $0.1653 |

**Tool-call tracking:** mean LLM calls per task = 11.43 (range 1–36), versus the previous run's constant proxy of 1. Token accounting is unchanged (already API-sourced) and remains the most directly billable of the three agents at $0.1653 total.

## Domain breakdown

| Domain | n | Mean score | Mean coverage |
|---|---:|---:|---:|
| financial | 1 | 1.000 | 1.000 |
| discreteMethods | 2 | 0.946 | 1.000 |
| multiphase | 4 | 0.483 | 0.617 |
| lagrangian | 3 | 0.444 | 0.500 |
| combustion | 4 | 0.428 | 0.625 |
| incompressible | 4 | 0.331 | 0.375 |
| heatTransfer | 3 | 0.325 | 0.533 |
| compressible | 3 | 0.228 | 0.333 |
| molecularDynamics | 2 | 0.202 | 0.250 |
| mesh | 3 | 0.043 | 0.067 |
| DNS | 1 | 0.000 | 0.000 |

## Per-case results

| Case | Domain | Solver | Status | Score | Cov | Sim | Missing | LLM calls | Input tok | Output tok | Total tok | Cost |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aachenBomb | combustion | reactingFoam | failed | 0.000 | 0.00 | 0.000 | 2/2 | 1 | n/a | n/a | n/a | n/a |
| angledDuctExplicitFixedCoeff | compressible | rhoSimpleFoam | success | 0.683 | 1.00 | 0.548 | 0/1 | 13 | 16,449 | 90,364 | 106,813 | $0.0194 |
| boxTurb16 | DNS | dnsFoam | success | 0.000 | 0.00 | 0.000 | 1/1 | 1 | n/a | n/a | n/a | n/a |
| cavityClipped | incompressible | icoFoam | success | 1.000 | 1.00 | 1.000 | 0/1 | 8 | 7,231 | 3,903 | 11,134 | $0.0015 |
| channel395 | incompressible | pimpleFoam | success | 0.323 | 0.50 | 0.248 | 1/2 | 10 | 13,720 | 25,554 | 39,274 | $0.0064 |
| coolingSphere | heatTransfer | chtMultiRegionFoam | failed | 0.000 | 0.00 | 0.000 | 1/1 | 13 | n/a | n/a | n/a | n/a |
| cyclone | lagrangian | denseParticleFoam | failed | 0.000 | 0.00 | 0.000 | 1/1 | 12 | n/a | n/a | n/a | n/a |
| dahl | multiphase | driftFluxFoam | success | 0.504 | 0.67 | 0.435 | 1/3 | 13 | 17,354 | 27,834 | 45,188 | $0.0072 |
| damBreak | multiphase | interFoam | success | 0.798 | 1.00 | 0.712 | 0/2 | 19 | 25,610 | 32,986 | 58,596 | $0.0090 |
| damBreak4phase | multiphase | compressibleMultiphaseInterFoam | success | 0.628 | 0.80 | 0.554 | 1/5 | 36 | 23,705 | 46,899 | 70,604 | $0.0116 |
| decompressionTank | compressible | rhoPimpleFoam | success | 0.000 | 0.00 | 0.000 | 1/1 | 1 | n/a | n/a | n/a | n/a |
| europeanCall | financial | financialFoam | success | 1.000 | 1.00 | 1.000 | 0/2 | 7 | 10,333 | 11,021 | 21,354 | $0.0032 |
| externalCoupledCavity | heatTransfer | buoyantFoam | success | 0.334 | 0.60 | 0.220 | 2/5 | 18 | 22,689 | 26,580 | 49,269 | $0.0075 |
| freeSpacePeriodic | discreteMethods | dsmcFoam | success | 0.994 | 1.00 | 0.992 | 0/3 | 19 | 14,458 | 19,380 | 33,838 | $0.0052 |
| hopperEmptying | lagrangian | particleFoam | success | 0.838 | 1.00 | 0.768 | 0/2 | 13 | 14,847 | 19,624 | 34,471 | $0.0053 |
| hopperInitialState | lagrangian | particleFoam | success | 0.495 | 0.50 | 0.493 | 1/2 | 12 | 15,140 | 16,265 | 31,405 | $0.0047 |
| hotRoomBoussinesqSteady | heatTransfer | buoyantFoam | success | 0.642 | 1.00 | 0.489 | 0/1 | 16 | 21,941 | 26,499 | 48,440 | $0.0074 |
| LadenburgJet60psi | compressible | rhoCentralFoam | success | 0.000 | 0.00 | 0.000 | 2/2 | 14 | 17,073 | 19,035 | 36,108 | $0.0054 |
| moriyoshiHomogeneous | combustion | XiFoam | success | 0.583 | 1.00 | 0.405 | 0/2 | 20 | 29,452 | 48,510 | 77,962 | $0.0124 |
| nc7h16 | combustion | chemFoam | success | 0.627 | 1.00 | 0.467 | 0/1 | 6 | 11,217 | 6,668 | 17,885 | $0.0024 |
| periodicCubeArgon | molecularDynamics | mdEquilibrationFoam | success | 0.404 | 0.50 | 0.362 | 1/2 | 8 | 13,165 | 18,868 | 32,033 | $0.0050 |
| periodicCubeWater | molecularDynamics | mdEquilibrationFoam | success | 0.000 | 0.00 | 0.000 | 1/1 | 9 | 15,403 | 29,158 | 44,561 | $0.0072 |
| porousBlockage | incompressible | pisoFoam | success | 0.000 | 0.00 | 0.000 | 1/1 | 1 | n/a | n/a | n/a | n/a |
| refineFieldDirs | mesh | refineMesh | success | 0.128 | 0.20 | 0.097 | 4/5 | 5 | 10,365 | 23,133 | 33,498 | $0.0056 |
| simpleShapes | mesh | foamyHexMesh | success | 0.000 | 0.00 | 0.000 | 1/1 | 11 | 16,334 | 20,664 | 36,998 | $0.0057 |
| sphere7ProjectedEdges | mesh | blockMesh | success | 0.000 | 0.00 | 0.000 | 1/1 | 1 | n/a | n/a | n/a | n/a |
| splashPanel | combustion | buoyantReactingFoam | success | 0.500 | 0.50 | 0.500 | 1/2 | 16 | 21,027 | 26,329 | 47,356 | $0.0072 |
| squareBump | incompressible | shallowWaterFoam | success | 0.000 | 0.00 | 0.000 | 2/2 | 9 | 13,351 | 20,709 | 34,060 | $0.0054 |
| supersonicCorner | discreteMethods | dsmcFoam | success | 0.899 | 1.00 | 0.856 | 0/4 | 20 | 20,868 | 53,027 | 73,895 | $0.0125 |
| throttle3D | multiphase | cavitatingFoam | success | 0.000 | 0.00 | 0.000 | 2/2 | 11 | 16,688 | 33,556 | 50,244 | $0.0082 |

## Notes

- Failed (nonzero exit): `aachenBomb`, `coolingSphere`, `cyclone`. Their files under `inputs/` are still scored.
- As before, most low scores are missing-required-file penalties on otherwise plausible case trees rather than LLM crashes; compressible and mesh domains remain the weakest.

## Artifacts

- Run root: `data/openfoam_runs/metaopenfoam/metaopenfoam_n30_hybrid_deepseek_v4_flash_20260530_tok`
- Scores: `data/openfoam_runs/metaopenfoam/metaopenfoam_n30_hybrid_deepseek_v4_flash_20260530_tok/n30_hybrid_scores.json`
- Run summary: `data/openfoam_runs/metaopenfoam/metaopenfoam_n30_hybrid_deepseek_v4_flash_20260530_tok/run_summary.json`

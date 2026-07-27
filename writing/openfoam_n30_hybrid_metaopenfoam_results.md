# MetaOpenFOAM on OpenFOAM n30 Hybrid

Evaluation date: 2026-05-30. Model: `deepseek/deepseek-v4-flash` via OpenRouter. Execution mode: lint-only OpenFOAM execution, matching the prior Foam Agent eval style. Parallelism: 15 tasks concurrently. Per-task timeout: 1500s.

Cost is recomputed from actual logged input/output token counts using OpenRouter DeepSeek V4 Flash effective pricing on 2026-05-30: input `$0.0983/M`, output `$0.1966/M` ([source](https://openrouter.ai/deepseek/deepseek-v4-flash)).

## Summary

| Metric | Value |
|---|---:|
| Cases | 30 |
| Mean overall score | 0.329 |
| Mean coverage | 0.425 |
| Full-coverage cases | 10 |
| Partial-coverage cases | 5 |
| Zero-coverage cases | 15 |
| Zero-score cases | 15 |
| Success / failed / timeout | 27 / 3 / 0 |
| Mean wall time per task | 380.4 s |
| Total input tokens | 439,340 |
| Total output tokens | 606,432 |
| Total tokens | 1,045,772 |
| Estimated OpenRouter cost | $0.1624 |

## Domain Breakdown

| Domain | n | Mean score | Mean coverage |
|---|---:|---:|---:|
| combustion | 4 | 0.159 | 0.250 |
| incompressible | 4 | 0.316 | 0.375 |
| multiphase | 4 | 0.458 | 0.575 |
| compressible | 3 | 0.000 | 0.000 |
| heatTransfer | 3 | 0.262 | 0.333 |
| lagrangian | 3 | 0.438 | 0.667 |
| mesh | 3 | 0.061 | 0.067 |
| discreteMethods | 2 | 0.822 | 0.875 |
| molecularDynamics | 2 | 0.352 | 0.500 |
| DNS | 1 | 0.872 | 1.000 |
| financial | 1 | 0.641 | 1.000 |

## Highest-Scoring Cases

| Case | Domain | Solver | Score | Coverage | Tokens | Cost |
|---|---|---|---:|---:|---:|---:|
| cavityClipped | incompressible | icoFoam | 1.000 | 1.000 | 11,975 | $0.0016 |
| freeSpacePeriodic | discreteMethods | dsmcFoam | 0.999 | 1.000 | 37,483 | $0.0059 |
| damBreak | multiphase | interFoam | 0.873 | 1.000 | 40,603 | $0.0062 |
| boxTurb16 | DNS | dnsFoam | 0.872 | 1.000 | 29,930 | $0.0044 |
| hopperEmptying | lagrangian | particleFoam | 0.838 | 1.000 | 40,224 | $0.0066 |
| hotRoomBoussinesqSteady | heatTransfer | buoyantFoam | 0.785 | 1.000 | 52,999 | $0.0080 |
| periodicCubeArgon | molecularDynamics | mdEquilibrationFoam | 0.704 | 1.000 | 31,043 | $0.0046 |
| supersonicCorner | discreteMethods | dsmcFoam | 0.645 | 0.750 | 62,361 | $0.0103 |

## Lowest-Scoring Cases

| Case | Domain | Solver | Status | Score | Coverage | Missing required files |
|---|---|---|---|---:|---:|---:|
| LadenburgJet60psi | compressible | rhoCentralFoam | success | 0.000 | 0.000 | 2 |
| aachenBomb | combustion | reactingFoam | success | 0.000 | 0.000 | 2 |
| angledDuctExplicitFixedCoeff | compressible | rhoSimpleFoam | success | 0.000 | 0.000 | 1 |
| coolingSphere | heatTransfer | chtMultiRegionFoam | success | 0.000 | 0.000 | 1 |
| dahl | multiphase | driftFluxFoam | success | 0.000 | 0.000 | 3 |
| decompressionTank | compressible | rhoPimpleFoam | failed | 0.000 | 0.000 | 1 |
| externalCoupledCavity | heatTransfer | buoyantFoam | success | 0.000 | 0.000 | 5 |
| hopperInitialState | lagrangian | particleFoam | success | 0.000 | 0.000 | 2 |

## Per-Case Results

| Case | Domain | Solver | Status | Score | Coverage | Similarity | Missing | Input tok | Output tok | Total tok | Cost |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LadenburgJet60psi | compressible | rhoCentralFoam | success | 0.000 | 0.000 | 0.000 | 2 | 9,023 | 10,769 | 19,792 | $0.0030 |
| aachenBomb | combustion | reactingFoam | success | 0.000 | 0.000 | 0.000 | 2 | 37,555 | 42,290 | 79,845 | $0.0120 |
| angledDuctExplicitFixedCoeff | compressible | rhoSimpleFoam | success | 0.000 | 0.000 | 0.000 | 1 | 6,242 | 8,719 | 14,961 | $0.0023 |
| boxTurb16 | DNS | dnsFoam | success | 0.872 | 1.000 | 0.817 | 0 | 15,056 | 14,874 | 29,930 | $0.0044 |
| cavityClipped | incompressible | icoFoam | success | 1.000 | 1.000 | 1.000 | 0 | 7,231 | 4,744 | 11,975 | $0.0016 |
| channel395 | incompressible | pimpleFoam | success | 0.264 | 0.500 | 0.163 | 1 | 13,213 | 17,538 | 30,751 | $0.0047 |
| coolingSphere | heatTransfer | chtMultiRegionFoam | success | 0.000 | 0.000 | 0.000 | 1 | 13,323 | 29,661 | 42,984 | $0.0071 |
| cyclone | lagrangian | denseParticleFoam | success | 0.477 | 1.000 | 0.253 | 0 | 18,440 | 30,725 | 49,165 | $0.0079 |
| dahl | multiphase | driftFluxFoam | success | 0.000 | 0.000 | 0.000 | 3 | 25,092 | 31,547 | 56,639 | $0.0087 |
| damBreak | multiphase | interFoam | success | 0.873 | 1.000 | 0.818 | 0 | 17,759 | 22,844 | 40,603 | $0.0062 |
| damBreak4phase | multiphase | compressibleMultiphaseInterFoam | success | 0.605 | 0.800 | 0.521 | 1 | 24,166 | 32,933 | 57,099 | $0.0089 |
| decompressionTank | compressible | rhoPimpleFoam | failed | 0.000 | 0.000 | 0.000 | 1 | 1,088 | 225 | 1,313 | $0.0002 |
| europeanCall | financial | financialFoam | success | 0.641 | 1.000 | 0.487 | 0 | 8,673 | 16,072 | 24,745 | $0.0040 |
| externalCoupledCavity | heatTransfer | buoyantFoam | success | 0.000 | 0.000 | 0.000 | 5 | 26,663 | 23,077 | 49,740 | $0.0072 |
| freeSpacePeriodic | discreteMethods | dsmcFoam | success | 0.999 | 1.000 | 0.999 | 0 | 14,972 | 22,511 | 37,483 | $0.0059 |
| hopperEmptying | lagrangian | particleFoam | success | 0.838 | 1.000 | 0.768 | 0 | 13,522 | 26,702 | 40,224 | $0.0066 |
| hopperInitialState | lagrangian | particleFoam | success | 0.000 | 0.000 | 0.000 | 2 | 13,939 | 18,923 | 32,862 | $0.0051 |
| hotRoomBoussinesqSteady | heatTransfer | buoyantFoam | success | 0.785 | 1.000 | 0.692 | 0 | 25,015 | 27,984 | 52,999 | $0.0080 |
| moriyoshiHomogeneous | combustion | XiFoam | success | 0.000 | 0.000 | 0.000 | 2 | 1,122 | 432 | 1,554 | $0.0002 |
| nc7h16 | combustion | chemFoam | success | 0.636 | 1.000 | 0.480 | 0 | 18,740 | 21,363 | 40,103 | $0.0060 |
| periodicCubeArgon | molecularDynamics | mdEquilibrationFoam | success | 0.704 | 1.000 | 0.576 | 0 | 15,749 | 15,294 | 31,043 | $0.0046 |
| periodicCubeWater | molecularDynamics | mdEquilibrationFoam | success | 0.000 | 0.000 | 0.000 | 1 | 17,562 | 33,707 | 51,269 | $0.0084 |
| porousBlockage | incompressible | pisoFoam | failed | 0.000 | 0.000 | 0.000 | 1 | 4,123 | 7,613 | 11,736 | $0.0019 |
| refineFieldDirs | mesh | refineMesh | success | 0.182 | 0.200 | 0.175 | 4 | 10,940 | 25,681 | 36,621 | $0.0061 |
| simpleShapes | mesh | foamyHexMesh | failed | 0.000 | 0.000 | 0.000 | 1 | 1,071 | 462 | 1,533 | $0.0002 |
| sphere7ProjectedEdges | mesh | blockMesh | success | 0.000 | 0.000 | 0.000 | 1 | 972 | 773 | 1,745 | $0.0002 |
| splashPanel | combustion | buoyantReactingFoam | success | 0.000 | 0.000 | 0.000 | 2 | 23,811 | 23,654 | 47,465 | $0.0070 |
| squareBump | incompressible | shallowWaterFoam | success | 0.000 | 0.000 | 0.000 | 2 | 14,303 | 14,774 | 29,077 | $0.0043 |
| supersonicCorner | discreteMethods | dsmcFoam | success | 0.645 | 0.750 | 0.600 | 1 | 19,504 | 42,857 | 62,361 | $0.0103 |
| throttle3D | multiphase | cavitatingFoam | success | 0.353 | 0.500 | 0.290 | 1 | 20,471 | 37,684 | 58,155 | $0.0094 |

## Notes

- `decompressionTank`, `porousBlockage`, and `simpleShapes` exited nonzero; their generated files were still scored because the standard scorer evaluates files found under `inputs/`.
- Several low scores are not LLM-crash failures; MetaOpenFOAM often generated plausible case trees but missed the exact required file path(s), which the file-coverage metric penalizes heavily.
- `moriyoshiHomogeneous` and `sphere7ProjectedEdges` have low token counts and no lint invocation; they appear to have stopped early after task division rather than completing the full generation/review path.


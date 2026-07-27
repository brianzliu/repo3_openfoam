# OpenFOAM `n30_hybrid` Benchmark Results

## Scope

- Subset: [`foamgpt_subset_seed42_n30_hybrid.json`](/home/brianliu/repo3_openfoam/configs/openfoam_benchmark/foamgpt_subset_seed42_n30_hybrid.json)
- Diversity analysis: [`openfoam_n30_hybrid_diversity_report.md`](/home/brianliu/repo3_openfoam/writing/openfoam_n30_hybrid_diversity_report.md)
- Materialized benchmark root: [`foamgpt_subset_seed42_n30_hybrid`](/home/brianliu/repo3_openfoam/data/openfoam_benchmark/foamgpt_subset_seed42_n30_hybrid)

The `n30_hybrid` subset was built to balance both physics-family diversity and category diversity. It spans all 11 OpenFOAM domains present in the FoamGPT test split, covers 26 solver families, and expands category coverage from 6 categories in the earlier `n30` sample to 9 categories.

## Runs Evaluated

### repo3 OpenFOAM adapter

- Run root: [`openfoam_n30_hybrid_full_20260526`](/home/brianliu/repo3_openfoam/data/openfoam_runs/repo3_openfoam_ablations/openfoam_n30_hybrid_full_20260526)
- Scores: [`n30_hybrid_scores.json`](/home/brianliu/repo3_openfoam/data/openfoam_runs/repo3_openfoam_ablations/openfoam_n30_hybrid_full_20260526/n30_hybrid_scores.json)
- Configuration: 9 cells in parallel, 15 tasks in parallel within each cell, `deepseek/deepseek-v4-flash`

### Foam Agent 2.0 baseline

- Run root: [`openfoam_n30_hybrid_foam_agent_lint_20260526d`](/home/brianliu/repo3_openfoam/data/openfoam_runs/foam_agent/openfoam_n30_hybrid_foam_agent_lint_20260526d)
- Scores: [`n30_hybrid_scores.json`](/home/brianliu/repo3_openfoam/data/openfoam_runs/foam_agent/openfoam_n30_hybrid_foam_agent_lint_20260526d/n30_hybrid_scores.json)
- Run summary: [`run_summary.json`](/home/brianliu/repo3_openfoam/data/openfoam_runs/foam_agent/openfoam_n30_hybrid_foam_agent_lint_20260526d/run_summary.json)
- Configuration: `lint_only`, 15 tasks in parallel, `deepseek/deepseek-v4-flash`

Foam Agent was not already complete in a usable form. I had to fix three compatibility issues before this run was possible:

- `run_foam_agent_eval.py` was launching the wrong Python and not binding the Foam Agent venv correctly.
- Relative prompt paths broke because Foam Agent runs from its own repo root.
- Foam Agent's structured-output JSON extractor was too greedy for DeepSeek responses and failed on trailing text.

I also terminated one runaway Foam Agent task (`coolingSphere`) after 1791.49 seconds to match the 25-minute timeout policy you asked to use going forward.

## Headline Results

### repo3 cell leaderboard

| Cell | Mean score | Mean coverage | Mean wall s/task | Mean tools/task | Zero-score tasks |
| --- | ---: | ---: | ---: | ---: | ---: |
| `r_plus_s` | `0.8871` | `1.0000` | `370.0` | `79.9` | `0` |
| `s_plus_x` | `0.8732` | `1.0000` | `372.2` | `82.9` | `0` |
| `r_plus_s_plus_x_plus_m` | `0.8726` | `1.0000` | `459.7` | `102.8` | `0` |
| `s_plus_m` | `0.8702` | `1.0000` | `358.6` | `79.3` | `0` |
| `s_plus_x_plus_m` | `0.8672` | `1.0000` | `382.4` | `81.6` | `0` |
| `r_plus_x` | `0.6791` | `1.0000` | `252.9` | `65.6` | `0` |
| `vanilla` | `0.6777` | `1.0000` | `266.2` | `60.4` | `0` |
| `r_plus_m` | `0.6767` | `1.0000` | `273.2` | `65.0` | `0` |
| `x_plus_m` | `0.6619` | `1.0000` | `300.6` | `65.3` | `0` |

### Foam Agent 2.0

| Run | Mean score | Mean coverage | Mean wall s/task | Mean tools/task | Zero-score tasks |
| --- | ---: | ---: | ---: | ---: | ---: |
| `foam_agent_lint` | `0.5908` | `0.7883` | `494.0` | `2.0` | `4` |

### Immediate comparison

- repo3 completed all `270/270` task-runs successfully across the full 9-cell matrix.
- Foam Agent completed `20/30` tasks successfully and failed `10/30`.
- Foam Agent beat repo3 `vanilla` on `11/30` tasks, but beat the best repo3 cell on only `1/30` task: `sphere7ProjectedEdges`.
- Every repo3 cell maintained full file coverage on all 30 tasks. Foam Agent's mean coverage dropped to `0.7883`, and its score collapses are mostly missing-file failures rather than mild textual mismatches.

## Per-Task Comparison Notes

### Tasks where Foam Agent beat repo3 `vanilla`

- `decompressionTank`: `0.8398` vs `0.7509`
- `periodicCubeArgon`: `0.7343` vs `0.6402`
- `europeanCall`: `0.8538` vs `0.6970`
- `channel395`: `0.7817` vs `0.6231`
- `simpleShapes`: `0.8497` vs `0.6731`
- `sphere7ProjectedEdges`: `0.8021` vs `0.6143`
- `boxTurb16`: `0.8940` vs `0.6938`
- `aachenBomb`: `0.8494` vs `0.6423`
- `porousBlockage`: `0.8560` vs `0.6326`
- `hotRoomBoussinesqSteady`: `0.8022` vs `0.5720`
- `hopperInitialState`: `0.9033` vs `0.6131`

### Largest Foam Agent deficits versus the best repo3 cell

- `squareBump`: Foam Agent `0.0000` vs repo3 best `0.9407` (`s_plus_m`)
- `splashPanel`: Foam Agent `0.0000` vs repo3 best `0.8897` (`r_plus_s`)
- `freeSpacePeriodic`: Foam Agent `0.0000` vs repo3 best `0.8828` (`s_plus_m`)
- `supersonicCorner`: Foam Agent `0.1584` vs repo3 best `0.9878` (`r_plus_s`)
- `throttle3D`: Foam Agent `0.0000` vs repo3 best `0.7202` (`r_plus_s`)
- `periodicCubeWater`: Foam Agent `0.4484` vs repo3 best `1.0000` (`s_plus_x`)
- `LadenburgJet60psi`: Foam Agent `0.4867` vs repo3 best `0.9870` (`s_plus_x`)

### Hardest tasks for repo3 on average across all 9 cells

- `coolingSphere`: average `0.5903`
- `throttle3D`: average `0.5922`
- `refineFieldDirs`: average `0.5934`
- `sphere7ProjectedEdges`: average `0.7031`
- `hotRoomBoussinesqSteady`: average `0.7219`

### Easiest tasks for repo3 on average across all 9 cells

- `angledDuctExplicitFixedCoeff`: average `0.9068`
- `cavityClipped`: average `0.8840`
- `nc7h16`: average `0.8724`
- `dahl`: average `0.8723`
- `externalCoupledCavity`: average `0.8668`

## Foam Agent Failure Analysis

### Final outcome counts

- `20` successes
- `9` workflow failures with `returncode=1`
- `1` manual timeout with `returncode=-15` (`coolingSphere`)

### Dominant failure modes

#### 1. Structured-output schema mismatch during rewrite / command generation

This remained the main failure class even after the JSON extractor fix. Two representative traces:

- `LadenburgJet60psi`: rewrite step returned a single-file dict where `FoamPydantic` expected `list_foamfile`
- `freeSpacePeriodic`: command-generation step returned a bare JSON list like `["blockMesh", "dsmcInitialise", "dsmcFoam"]`, but Foam Agent expected a wrapped object matching `CommandsPydantic`

These are not retrieval failures. They are schema-contract failures between DeepSeek output and Foam Agent's typed planner/input-writer interface.

#### 2. Missing-file failures after otherwise successful workflow completion

Several Foam Agent runs exited successfully but still scored poorly because required benchmark files were absent or renamed:

- `freeSpacePeriodic`: missing `0/boundaryT`, `0/iDof`, `0/rhoN`
- `supersonicCorner`: missing `0/boundaryU`, `0/fD`, `0/momentum`
- `squareBump`: missing `0/hU.orig`, `constant/gravitationalProperties`
- `splashPanel`: missing `constant/momentumTransport`, `system/decomposeParDict`
- `damBreak4phase`: missing `0/alpha.oil.orig`, `0/alpha.water.orig`

This is the main reason Foam Agent's mean coverage fell to `0.7883` even when its successful cases were often fairly strong.

#### 3. Long-tail reviewer/lint loops on complex multi-file cases

`coolingSphere` is the clearest example. It generated 33 file events, 38 saved-file events, 3 review loops, and 3 lint-checker invocations before being terminated at the 25-minute policy boundary. The task did not fail at first-file generation; it failed to converge in the review/lint loop quickly enough.

## Interpretation

### What the `n30_hybrid` run says about repo3

- The best-performing repo3 cell on this subset is `r_plus_s`, not the full `r+s+x+m` stack.
- The stop-hook cells remain the dominant quality lift. Every top-5 cell includes `s`.
- The `x` and `m` factors are not uniformly additive on this subset. They can help, but `r+s` was the strongest mean-score point.
- repo3's major advantage over Foam Agent on this benchmark is not just higher mean similarity. It is its ability to maintain complete required-file coverage across all 270 evaluated task-runs.

### What the run says about Foam Agent 2.0

- Foam Agent can produce good cases on a nontrivial fraction of tasks. Its wins over `vanilla` are real, and some are large.
- Its ceiling is not the problem here. Its floor is. The combination of structured-output brittleness and missing required files creates too many catastrophic score drops.
- On this benchmark, DeepSeek-v4-flash is workable for Foam Agent only after compatibility fixes, and even then the interface is still fragile relative to repo3's adapterized harness.

## Caveats

- Foam Agent was evaluated in `lint_only` mode because that is the stable comparison path already used in the OpenFOAM study notes.
- The Foam Agent runner required harness-side fixes plus a parser fix in Foam Agent itself before this benchmark was runnable at all.
- The final `coolingSphere` result was forcibly terminated to honor the 25-minute timeout policy. That score should be read as a timeout-bound failure, not a naturally completed run.
- Foam Agent's token counters are not a trustworthy API-cost ledger for this run. They reflect internal service accounting in its wrapper, not a validated OpenRouter billing reconstruction.

## Artifact Index

- Diversity report: [`openfoam_n30_hybrid_diversity_report.md`](/home/brianliu/repo3_openfoam/writing/openfoam_n30_hybrid_diversity_report.md)
- repo3 scores: [`n30_hybrid_scores.json`](/home/brianliu/repo3_openfoam/data/openfoam_runs/repo3_openfoam_ablations/openfoam_n30_hybrid_full_20260526/n30_hybrid_scores.json)
- Foam Agent scores: [`n30_hybrid_scores.json`](/home/brianliu/repo3_openfoam/data/openfoam_runs/foam_agent/openfoam_n30_hybrid_foam_agent_lint_20260526d/n30_hybrid_scores.json)
- Foam Agent run summary: [`run_summary.json`](/home/brianliu/repo3_openfoam/data/openfoam_runs/foam_agent/openfoam_n30_hybrid_foam_agent_lint_20260526d/run_summary.json)

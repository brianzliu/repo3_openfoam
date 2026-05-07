# OpenFOAM Repo3 Adaptation: Methods, Experiments, Results, and Analysis

## Scope

This document summarizes the full OpenFOAM work carried out in `repo3_openfoam` as an adaptation of the original GEOS-oriented `repo_3` Claude Code plugin stack. It covers:

- the benchmark construction
- the OpenFOAM plugin adaptation from the original GEOS `R/S/X/M` design
- the ablation harness and experiment design
- the Foam-Agent comparison setup
- the exact quantitative results tables
- an in-depth analysis of what helped, what did not, and why

The main intent was not to reproduce the GEOS paper mechanically, but to port the same adaptation logic into an OpenFOAM case-authoring setting and see which components survive that transfer.

## Repositories and adaptation lineage

The relevant repositories were:

- Current OpenFOAM adaptation repo: `/home/brianliu/repo3_openfoam`
- Original GEOS-oriented source repo used as the adaptation template: `/home/brianliu/repo_3`
- External baseline repo: `/home/brianliu/Foam-Agent`

The OpenFOAM work in this repo is best understood as a direct adaptation of the GEOS-side plugin architecture from `repo_3`:

- GEOS retrieval MCP: `/home/brianliu/repo_3/plugin/scripts/geos_rag_mcp.py`
- GEOS schema validator MCP: `/home/brianliu/repo_3/plugin/scripts/xmllint_mcp.py`
- GEOS stop-hook verifier: `/home/brianliu/repo_3/plugin/hooks/verify_outputs.py`
- OpenFOAM retrieval MCP: `plugin/scripts/openfoam_rag_mcp.py`
- OpenFOAM validator MCP: `plugin/scripts/openfoam_validate_mcp.py`
- OpenFOAM stop-hook verifier: `plugin/hooks/verify_outputs.py`
- OpenFOAM case checker shared by hook and validator: `plugin/hooks/openfoam_case_check.py`

The design was intentionally analogous:

- `R`: retrieval over simulator-facing documentation/examples
- `S`: forced end-of-turn self-refinement via a stop hook
- `X`: agent-callable validator MCP
- `M`: always-on interface primer / memory-style prompt augmentation

What changed is the substrate. GEOS has XML plus an official XSD schema and `xmllint`. OpenFOAM has case dictionaries, tutorial cases, command help, and no equivalent single canonical schema. That difference forced the biggest method change: `X` in OpenFOAM is not schema validation, but heuristic case validation.

## Benchmark and task subset

The OpenFOAM benchmark path is documented in `docs/openfoam_benchmark.md`. The benchmark subset was materialized from FoamGPT into:

- `data/openfoam_benchmark/foamgpt_subset_seed42`

The subset manifest is:

- `data/openfoam_benchmark/foamgpt_subset_seed42/manifest.json`

This subset contains 5 tasks, sampled with seed 42:

| Case | Solver | Domain | Category | Required files |
|---|---|---|---|---|
| `boundaryWallFunctionsProfile` | `boundaryFoam` | `incompressible` | `None` | `0/epsilon`, `0/k`, `0/omega`, `constant/physicalProperties.template` |
| `Grossetete` | `multiphaseEulerFoam` | `multiphase` | `RAS` | `0/T.liquid`, `constant/physicalProperties.gas`, `system/fvSolution` |
| `helmholtzResonance` | `rhoPimpleFoam` | `compressible` | `laminar` | `0/U`, `constant/physicalProperties` |
| `externalCoupledCavity` | `buoyantFoam` | `heatTransfer` | `None` | `0/nut`, `0/p`, `constant/pRef`, `constant/physicalProperties`, `system/blockMeshDict` |
| `damBreakWithObstacle` | `interFoam` | `multiphase` | `laminar` | `constant/momentumTransport`, `system/blockMeshDict`, `system/setFieldsDict` |

This is a small benchmark. It is useful for adaptation sanity-checking and comparative ablations, but it is not large enough to support GEOS-paper-style variance or held-out-distribution claims.

## Evaluation metric

OpenFOAM evaluation is implemented in:

- `scripts/openfoam/evaluate_openfoam_runs.py`

This is not the GEOS TreeSim scorer. The current OpenFOAM metric is a file-text similarity metric with failures-as-zero behavior:

- normalize each ground-truth and generated file
- score file similarity with `difflib.SequenceMatcher`
- assign score `0` for any missing required file
- compute per-case:
  - `mean_similarity = mean(file_scores)`
  - `coverage = 1 - missing_required_files / required_files`
  - `overall_score = 0.7 * mean_similarity + 0.3 * coverage`

This means the metric is structurally analogous to failures-as-zero aggregation in the GEOS paper, but it is not tree-aware and not semantically specific to OpenFOAM dictionaries. It rewards textual closeness and file presence, not execution correctness.

## Experiment harness

The main OpenFOAM ablation runner is:

- `scripts/openfoam/run_repo3_openfoam_ablation.py`

The main Foam-Agent runner is:

- `scripts/openfoam/run_foam_agent_eval.py`

Both were wired to the same 5-task subset and the same backbone model:

- `deepseek/deepseek-v4-flash`

For the Claude Code path, the OpenFOAM ablations were run through OpenRouter using the Anthropic-compatible Claude Code interface:

- `ANTHROPIC_BASE_URL=https://openrouter.ai/api`
- `ANTHROPIC_AUTH_TOKEN=$OPENROUTER_API_KEY`
- `ANTHROPIC_API_KEY=""`
- `ANTHROPIC_CUSTOM_MODEL_OPTION=deepseek/deepseek-v4-flash`

For Foam-Agent, the runner configured:

- `FOAMAGENT_MODEL_PROVIDER=openai`
- `FOAMAGENT_MODEL_VERSION=deepseek/deepseek-v4-flash`
- `OPENAI_API_KEY=$OPENROUTER_API_KEY`
- `OPENAI_BASE_URL=https://openrouter.ai/api/v1`

## OpenFOAM `R/S/X/M` adaptation

### `R`: Retrieval adaptation

The original GEOS retrieval server in `repo_3` used three Chroma collections:

- `geos_navigator`
- `geos_technical`
- `geos_schema`

It was built around GEOS RST documentation, technical docs, and XML/schema material, with OpenAI/OpenRouter embeddings by default and contamination blocking for forbidden XML/RST references.

The OpenFOAM adaptation replaced that with an OpenFOAM-specific retrieval server:

- `plugin/scripts/openfoam_rag_mcp.py`

It exposes these tools:

- `search_tutorials(query, n_results=5)`
- `search_cases(query, n_results=5)`
- `search_commands(query, n_results=5)`
- `healthcheck()`

The OpenFOAM collections are:

| Collection | Stored content | Source corpus |
|---|---|---|
| `openfoam_tutorials` | tutorial-level structure and case-layout summaries | `Foam-Agent/database/raw/openfoam_tutorials_structure.txt` |
| `openfoam_cases` | detailed case snippets and Allrun-derived context | `Foam-Agent/database/raw/openfoam_tutorials_details.txt`, `Foam-Agent/database/raw/openfoam_allrun_scripts.txt` |
| `openfoam_commands` | command lists and command-help text | `Foam-Agent/database/raw/openfoam_commands.txt`, `Foam-Agent/database/raw/openfoam_command_help.txt` |

The DB builder is:

- `scripts/openfoam/build_openfoam_chromadb.py`

Important differences from GEOS:

- The OpenFOAM DB defaults to a local deterministic 256-dimensional hash embedding.
- The GEOS DB used OpenAI/OpenRouter embeddings by default.
- OpenFOAM retrieval is tutorial-and-command centric, not schema centric.
- OpenFOAM retrieval does not currently implement the same contamination blocking logic as GEOS RAG.

The current persisted DB path is:

- `data/openfoam_benchmark/chromadb_openfoam`

The collections were built with the following chunk counts:

| Collection | Chunks |
|---|---:|
| `openfoam_tutorials` | 497 |
| `openfoam_cases` | 40640 |
| `openfoam_commands` | 161 |

Sample tutorial-structure content stored in `openfoam_tutorials` includes entries like:

```text
case name: boundaryWallFunctionsProfile
case domain: incompressible
case solver: boundaryFoam
```

Sample detailed case content stored in `openfoam_cases` includes dictionary snippets like:

```text
outlet
{
    type            pressureInletOutletVelocity;
    value           $internalField;
}
```

Sample command-help content stored in `openfoam_commands` includes entries like:

```text
<command>setFields</command>
Usage: setFields [OPTIONS]
```

This is the OpenFOAM analogue of the GEOS interface retrieval layer.

### `M`: Primer / memory adaptation

The GEOS-side `M` condition in the original paper was a distilled interface cheatsheet with concrete XML element names, constitutive blocks, solver-family mappings, and common attributes. It was a compact domain memory dump.

The OpenFOAM `M` adaptation is lighter. It is implemented as prompt-level primer substitution rather than a large distilled vocabulary artifact.

Files:

- `plugin/OPENFOAM_PRIMER_absolute_min.md`
- `plugin/OPENFOAM_PRIMER_minimal.md`
- `plugin/OPENFOAM_PRIMER_minimal_vanilla.md`

The ablation runner uses them as follows:

- no `M`: `OPENFOAM_PRIMER_absolute_min.md`
- `M` without `R`: `OPENFOAM_PRIMER_minimal_vanilla.md`
- `M` with `R`: `OPENFOAM_PRIMER_minimal.md`

The minimal primers add:

- the standard OpenFOAM case skeleton `0/`, `constant/`, `system/`
- the authoritative tutorial/source locations
- an explicit reminder to write all outputs under `/workspace/inputs`
- in the `R`-enabled version, explicit MCP retrieval instructions

This means the OpenFOAM `M` condition is closer to an interface primer than to the richer GEOS distilled cheatsheet. It still matters experimentally, but it is a less ambitious memory artifact.

### `S`: Self-refinement / forced verification adaptation

The GEOS `S` condition relied on a stop hook that blocked turn completion if:

- no XML was written
- XML parse failed
- optional `xmllint --schema` validation failed

The GEOS stop-hook logic lives in:

- `/home/brianliu/repo_3/plugin/hooks/verify_outputs.py`

The OpenFOAM adaptation keeps the same control-flow idea:

- `plugin/hooks/verify_outputs.py`
- `plugin/hooks/verify_openfoam_post_write.py`
- `plugin/hooks/openfoam_case_check.py`

The core OpenFOAM validation logic is in `validate_case(...)` and `validate_openfoam_file(...)` inside `openfoam_case_check.py`.

The stop-hook behavior is:

- block if `/workspace/inputs` has no outputs
- load `task_manifest.json`
- block if any required benchmark file is missing
- validate every file that does exist

The post-write hook adds faster local checks whenever files are written or edited.

The file-level validation is heuristic and OpenFOAM-specific. It checks for:

- UTF-8 readability
- non-empty files
- balanced `{}`, `()`, and `[]`
- presence of `FoamFile` for non-script files
- obvious missing line terminators
- required sections for key file types:
  - `system/blockMeshDict`: `vertices`, `blocks`, `boundary`
  - `system/fvSchemes`: `ddtSchemes`, `divSchemes`
  - `system/fvSolution`: `solvers`
  - `0/*`: `dimensions`, `internalField`, `boundaryField`

This is the OpenFOAM analogue to GEOS stop-hook self-refinement. It is not semantic execution, but it is a hard end-of-turn gate.

### `X`: Validator-MCP adaptation

The GEOS `X` condition exposed `xmllint --schema` to the agent through:

- `/home/brianliu/repo_3/plugin/scripts/xmllint_mcp.py`

That tool was a thin wrapper around the same validator used by the stop hook.

The OpenFOAM analogue is:

- `plugin/scripts/openfoam_validate_mcp.py`

It exposes:

- `validate_openfoam_case()`
- `validate_openfoam_file(file_path)`

Unlike GEOS, this is not a schema validator. OpenFOAM does not have a single canonical XSD-like source for these case dictionaries. Instead, the validator MCP reuses the same heuristic case checker that powers the hook:

- missing required files
- missing `FoamFile`
- unbalanced delimiters
- missing mandatory blocks in key files

So the OpenFOAM `X` condition is best described as a case-structure validator, not a schema validator.

### What was not ported

The GEOS paper also discussed:

- `SE-prose`
- `SE`
- self-evolved monolithic plugin variants

Those were not implemented as OpenFOAM cells in this repo. The OpenFOAM work implemented the direct `R/S/X/M` analogue and the factorial-style ablation cells, but not an OpenFOAM self-evolved monolithic plugin.

## Experiment matrix

The OpenFOAM ablation cells were:

| Cell | R | S | X | M |
|---|---:|---:|---:|---:|
| `vanilla` | 0 | 0 | 0 | 0 |
| `r+m` | 1 | 0 | 0 | 1 |
| `s+m` | 0 | 1 | 0 | 1 |
| `r+s` | 1 | 1 | 0 | 0 |
| `x+m` | 0 | 0 | 1 | 1 |
| `r+x` | 1 | 0 | 1 | 0 |
| `s+x` | 0 | 1 | 1 | 0 |
| `r+s+x+m` | 1 | 1 | 1 | 1 |
| `s+x+m` | 0 | 1 | 1 | 1 |

This is the direct OpenFOAM analogue of the GEOS-style `R/S/X/M` ablation design, with an additional `s+x+m` completion cell.

## Foam-Agent comparison and the execute-vs-lint issue

The Foam-Agent comparison needs a precise framing.

Foam-Agent was not originally designed as a lint-only generator. Its native workflow is a fuller software loop that includes:

- planning
- input writing
- local or HPC execution
- reviewer-driven repair loops
- optional visualization

That structure is visible in:

- `/home/brianliu/Foam-Agent/src/main.py`
- `/home/brianliu/Foam-Agent/src/router_func.py`
- `/home/brianliu/Foam-Agent/foambench_main.py`

In particular:

- `foambench_main.py` exposes `--execution_mode {execute, lint_only}`
- `router_func.py` routes `lint_only` to `lint_checker`
- otherwise it routes through `local_runner` or `hpc_runner`, and then to `reviewer` if there are execution errors

So the original Foam-Agent design is software-in-the-loop refinement, not just syntax/lint checking.

For this OpenFOAM comparison, however, the successful baseline run was:

- `foam_agent_lint`

not execute mode.

That matters. The main comparison in this document is therefore:

- repo3-style Claude Code ablation cells for case authoring
- versus a restricted Foam-Agent lint-only run

This is still a useful baseline, but it is narrower than Foam-Agent’s intended workflow. Execute-mode runs were not used for the final comparison table because they failed in this environment and produced unusable benchmark outputs.

## Main quantitative results

The evaluated aggregate JSON is:

- `data/openfoam_runs/repo3_openfoam_ablations/openfoam_ablation_or_20260506/eval_all_finished_vs_foam_agent.json`

### Cell summary table

| Cell | Mean score | Δ vs Foam-Agent | Pass@0.7 | Full coverage | Exact cases | Task-score std | Mean wall s | Mean tools/task |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `r+s` | 0.8711 | +0.3023 | 5/5 | 5/5 | 0 | 0.0822 | 380.19 | 86.0 |
| `r+s+x+m` | 0.8623 | +0.2935 | 5/5 | 5/5 | 0 | 0.1027 | 1419.00 | 113.4 |
| `s+x` | 0.8487 | +0.2799 | 5/5 | 5/5 | 0 | 0.0851 | 1020.30 | 91.8 |
| `s+x+m` | 0.8220 | +0.2532 | 5/5 | 5/5 | 0 | 0.0734 | 1147.37 | 89.4 |
| `s+m` | 0.7865 | +0.2178 | 4/5 | 5/5 | 0 | 0.1252 | 1481.66 | 73.8 |
| `r+m` | 0.7357 | +0.1669 | 2/5 | 5/5 | 1 | 0.1603 | 1275.89 | 58.0 |
| `x+m` | 0.7120 | +0.1433 | 4/5 | 5/5 | 0 | 0.0971 | 1643.58 | 83.8 |
| `foam_agent_lint` | 0.5688 | 0.0000 | 1/5 | 3/5 | 0 | 0.2048 | 546.62 | 3.0 |
| `vanilla` | 0.4660 | -0.1028 | 3/5 | 3/5 | 0 | 0.3811 | 1920.72 | 86.0 |
| `r+x` | 0.1448 | -0.4240 | 1/5 | 1/5 | 0 | 0.2896 | 777.55 | 97.4 |

### Per-task score table

| Cell | `boundaryWallFunctionsProfile` | `Grossetete` | `helmholtzResonance` | `externalCoupledCavity` | `damBreakWithObstacle` |
|---|---:|---:|---:|---:|---:|
| `vanilla` | 0.7510 | 0.8170 | 0.0000 | 0.7619 | 0.0000 |
| `r+m` | 0.6497 | 0.8165 | 0.6806 | 1.0000 | 0.5318 |
| `s+m` | 0.8603 | 0.9661 | 0.7884 | 0.5954 | 0.7226 |
| `r+s` | 0.9074 | 0.9681 | 0.8576 | 0.8995 | 0.7226 |
| `x+m` | 0.7194 | 0.8204 | 0.7269 | 0.7619 | 0.5315 |
| `r+x` | 0.7239 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `s+x` | 0.9651 | 0.8695 | 0.7866 | 0.8993 | 0.7228 |
| `r+s+x+m` | 0.9636 | 0.9666 | 0.7602 | 0.8993 | 0.7216 |
| `s+x+m` | 0.8071 | 0.7880 | 0.8499 | 0.9431 | 0.7216 |
| `foam_agent_lint` | 0.6569 | 0.1651 | 0.6494 | 0.6364 | 0.7359 |

### Factor-style main effects

The following are the factor-style averages computed over the 8-cell fractional-style subset only. This is `n=1`, so these are descriptive only.

#### Mean score effects

| Factor | Δ mean score | On mean | Off mean |
|---|---:|---:|---:|
| `S` | +0.3275 | 0.8421 | 0.5146 |
| `M` | +0.1915 | 0.7741 | 0.5826 |
| `R` | -0.0499 | 0.6534 | 0.7033 |
| `X` | -0.0729 | 0.6419 | 0.7148 |

#### Pass@0.7 effects

| Factor | Δ Pass@0.7 | On mean | Off mean |
|---|---:|---:|---:|
| `S` | +0.45 | 0.95 | 0.50 |
| `X` | +0.05 | 0.75 | 0.70 |
| `M` | +0.05 | 0.75 | 0.70 |
| `R` | -0.15 | 0.65 | 0.80 |

## Failure analysis

### Why some tasks scored zero

The zero scores came from the evaluator’s failures-as-zero behavior. If a required file was missing, that file received score `0`. If all required files for a task were missing, the task score collapsed to `0`.

The hard zero-score cases were:

| Cell | Task | Missing required files |
|---|---|---|
| `vanilla` | `helmholtzResonance` | `0/U`, `constant/physicalProperties` |
| `vanilla` | `damBreakWithObstacle` | `constant/momentumTransport`, `system/blockMeshDict`, `system/setFieldsDict` |
| `r+x` | `Grossetete` | `0/T.liquid`, `constant/physicalProperties.gas`, `system/fvSolution` |
| `r+x` | `helmholtzResonance` | `0/U`, `constant/physicalProperties` |
| `r+x` | `externalCoupledCavity` | all required files missing |
| `r+x` | `damBreakWithObstacle` | all required files missing |

These are not “bad but partial” outputs. They are hard output misses.

### What `S` appears to have fixed

This benchmark gives one especially clear result: `S` was the strongest reliability component.

Evidence:

- none of the `S` cells had any zero-score tasks
- the zero-score collapses were concentrated in `vanilla` and `r+x`
- `S` cells all achieved full required-file coverage on all 5 tasks

This matches the implementation. The stop hook explicitly checks `task_manifest.json` and blocks end-of-turn completion if required files are missing. In other words, `S` is not just a reminder; it is a forcing function.

On this benchmark, that forcing function mattered more than anything else.

## Interpretation by factor

### `S` was the strongest positive component

`S` has the clearest positive signal in the factor-style readout:

- `+0.3275` mean-score effect
- `+0.45` Pass@0.7 effect

That is consistent with the failure patterns:

- `S` eliminated the hard missing-file failures seen in `vanilla`
- `S` prevented the catastrophic collapse of the `r+x` style condition

The practical interpretation is straightforward. In this OpenFOAM setup, a stop-hook that verifies required outputs exists is worth more than optional validation tools or retrieval alone.

### `M` helped, but in a lightweight way

`M` is positive:

- `+0.1915` mean-score effect
- `+0.05` Pass@0.7 effect

This is notable because the OpenFOAM `M` condition was only a minimal primer, not a rich cheatsheet. That suggests even lightweight prompt-level interface grounding can help if it correctly reminds the model about:

- where files go
- the standard case skeleton
- which reference locations to consult

The OpenFOAM result therefore supports the GEOS paper’s broader claim that always-on interface guidance matters, even though the OpenFOAM memory artifact here was simpler.

### `R` was mildly negative

`R` was slightly negative:

- `-0.0499` mean-score effect
- `-0.15` Pass@0.7 effect

This broadly rhymes with the GEOS paper’s result that retrieval can be negative or at least not clearly positive in some settings.

There are at least three plausible reasons here:

1. The OpenFOAM retrieval corpora are large and heterogeneous, especially the `openfoam_cases` collection. That can increase distraction.
2. The current retrieval DB uses hash embeddings by default, not higher-quality semantic embeddings. That likely lowers retrieval precision.
3. The measured MCP call counts in the repo3-style runs were `0.0` on average, even for `R` cells. That suggests either:
   - the agent often did not actually invoke the retrieval tools, or
   - the current accounting path did not capture those MCP calls correctly

Either way, there is no evidence here that retrieval became a strong positive contributor.

### `X` underperformed

`X` is the most surprising negative:

- `-0.0729` mean-score effect
- only `+0.05` Pass@0.7 effect

This is easy to explain structurally.

The OpenFOAM validator MCP is optional. It does not force a retry. If the agent does not use it effectively, or uses it too late, it cannot prevent end-of-turn failure in non-`S` cells. That is exactly what `r+x` demonstrates:

- optional retrieval plus optional validator
- no forced stop hook
- catastrophic required-file misses

So `X` without `S` is weak. This is the same kind of lesson the GEOS paper emphasizes: agent-callable validators are not equivalent to hard control-flow gates.

## Cell-by-cell analysis

### `r+s` was the strongest overall condition

`r+s` was the best-performing OpenFOAM cell:

- best mean score: `0.8711`
- full coverage: `5/5`
- Pass@0.7: `5/5`
- mean wall time: `380.19s`

This is the most important practical result in the batch. The best OpenFOAM condition was not the fullest stack. It was a simpler combination:

- retrieval available
- stop-hook forced verification
- no validator MCP
- no primer `M`

That likely means the hard gain came from reliability control, not from stacking every available adapter.

### `r+s+x+m` and `s+x` were competitive, but more expensive

The next-best cells were:

- `r+s+x+m`: `0.8623`
- `s+x`: `0.8487`

Both had perfect Pass@0.7 and full coverage, but neither beat `r+s`. They were also slower or more tool-heavy:

- `r+s+x+m`: `1419.00s`, `113.4 tools/task`
- `s+x`: `1020.30s`, `91.8 tools/task`
- `r+s`: `380.19s`, `86.0 tools/task`

So there is no evidence here that the fuller stacks raised the ceiling.

### `r+x` was the catastrophic failure cell

`r+x` is the clearest negative result:

- mean score: `0.1448`
- only `1/5` Pass@0.7
- only `1/5` full coverage
- four task collapses

This is the OpenFOAM analogue of a “looks instrumented, still fails” condition. It confirms that:

- optional validation is not enough
- retrieval without hard completion checks can be actively fragile

### `vanilla` was weak but not uniformly bad

`vanilla` scored `0.4660`, below `foam_agent_lint` and well below the best `S` cells. Still, it was not uniformly poor:

- `boundaryWallFunctionsProfile`: `0.7510`
- `Grossetete`: `0.8170`
- `externalCoupledCavity`: `0.7619`

The problem was not universal inability. The problem was brittle completeness:

- two tasks collapsed to zero because required files were not written

That is exactly the kind of reliability failure the stop hook is designed to suppress.

### Foam-Agent `lint_only` was a middling baseline, not a strong one

`foam_agent_lint` scored:

- mean score: `0.5688`
- Pass@0.7: `1/5`
- full coverage: `3/5`

It was slightly better than `vanilla` overall, but clearly below the strong repo3-style `S` cells.

It did have one relative advantage:

- on `damBreakWithObstacle`, `foam_agent_lint` scored `0.7359`
- the best repo3-style cells were around `0.722`

So Foam-Agent linting was not uniformly dominated. But across the full subset it was substantially behind the best adapted Claude Code cells.

## Efficiency analysis

This section should be read carefully because the efficiency counters are not measuring exactly the same thing across systems.

For repo3-style Claude Code runs:

- tool counts come from Claude stream-JSON tool-use blocks

For Foam-Agent:

- tool counts are LLM service calls plus workflow-event-derived counters such as retrieval queries, reviewer loops, and lint invocations

So the numbers are useful, but not perfectly apples-to-apples.

Still, two efficiency conclusions are clear.

First, `r+s` is unusually strong:

- it was the best-quality cell
- it had perfect coverage
- it was also faster than `foam_agent_lint`

Second, `foam_agent_lint` used very few counted “tools”:

- mean tools/task: `3.0`

but that is partly because its accounting model differs from the Claude Code stream accounting. It should not be misread as a proof that Foam-Agent is more computationally efficient in a like-for-like sense.

## Important caveats

### This is not TreeSim

The OpenFOAM scorer is a file-text similarity metric, not a tree-aware structural metric like the GEOS XML scorer. The OpenFOAM results are therefore analogous to the GEOS results, not numerically or methodologically identical.

### `n=1` per cell

Unlike the GEOS paper’s 3-seed reporting, these OpenFOAM ablations are single-run cells. That means:

- no seed standard deviation across runs
- no robust reliability variance estimates
- only descriptive factor-effect analogues

The `task_score_std` column is within-cell task dispersion, not across-seed variance.

### `mcp_calls` were recorded as zero

The repo3-style run summaries show:

- `mean_mcp_calls_per_task = 0.0`

even in `R` and `X` cells.

That means one of two things happened:

1. the agent rarely or never actually used the MCP tools, or
2. the current stream parser did not capture those calls correctly

Either interpretation matters. If it is true non-usage, then OpenFOAM reproduces a negative pattern seen in parts of the GEOS work: simply exposing retrieval/validation tools does not guarantee the agent will use them. If it is an accounting gap, then tool-usage analysis here is incomplete.

### Foam-Agent comparison is to `lint_only`, not native execute mode

This is the most important baseline caveat.

The reported Foam-Agent comparison is against:

- `foam_agent_lint`

not against its original execute-and-review path.

So the current comparison is best read as:

- adapted Claude Code case-authoring stack
- versus Foam-Agent restricted to lint-only benchmarking mode

not as a full end-to-end defeat of Foam-Agent’s intended workflow.

## Bottom-line conclusions

The OpenFOAM adaptation supports four main conclusions.

First, the direct `R/S/X/M` transfer from `repo_3` is viable. The plugin architecture is portable across simulators, but the substrate matters. XML-schema validation ports cleanly in GEOS; OpenFOAM requires heuristic dictionary-and-required-file validation instead.

Second, the strongest OpenFOAM gain came from `S`, the forced stop-hook self-refinement. On this subset, `S` was the clearest reliability intervention and eliminated the zero-score missing-file collapses that hurt `vanilla` and `r+x`.

Third, retrieval and optional validation were not enough on their own. `R` was mildly negative, `X` was slightly negative on mean score, and `r+x` was the worst ablation cell by far. This is strong evidence that optional tools are much weaker than hard control-flow gates.

Fourth, the best OpenFOAM cell here was `r+s`, not the fullest stack. That result argues against assuming that more instrumentation is automatically better. In this setup, the highest-value intervention was making completion robust.

## Artifact paths

Primary implementation files:

- `plugin/scripts/openfoam_rag_mcp.py`
- `plugin/scripts/openfoam_validate_mcp.py`
- `plugin/hooks/openfoam_case_check.py`
- `plugin/hooks/verify_outputs.py`
- `plugin/hooks/verify_openfoam_post_write.py`
- `plugin/OPENFOAM_PRIMER_absolute_min.md`
- `plugin/OPENFOAM_PRIMER_minimal.md`
- `plugin/OPENFOAM_PRIMER_minimal_vanilla.md`

Benchmark and run harness:

- `scripts/openfoam/materialize_foamgpt_subset.py`
- `scripts/openfoam/build_openfoam_chromadb.py`
- `scripts/openfoam/run_repo3_openfoam_eval.py`
- `scripts/openfoam/run_repo3_openfoam_ablation.py`
- `scripts/openfoam/run_foam_agent_eval.py`
- `scripts/openfoam/evaluate_openfoam_runs.py`

Benchmark assets:

- `data/openfoam_benchmark/foamgpt_subset_seed42/manifest.json`
- `data/openfoam_benchmark/chromadb_openfoam`

Run outputs:

- `data/openfoam_runs/repo3_openfoam_ablations/openfoam_ablation_or_20260506`
- `data/openfoam_runs/repo3_openfoam_ablations/openfoam_ablation_or_20260506/eval_all_finished_vs_foam_agent.json`

Comparison baseline repo:

- `/home/brianliu/Foam-Agent`

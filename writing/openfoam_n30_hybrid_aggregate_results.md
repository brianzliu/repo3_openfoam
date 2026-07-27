# OpenFOAM n30 Hybrid Results: Repo3 SIGA, Foam Agent, and MetaOpenFOAM

All rows use the same `foamgpt_subset_seed42_n30_hybrid` benchmark and the same file-text-and-coverage metric. The MetaOpenFOAM row was run on 2026-05-30 with `deepseek/deepseek-v4-flash`; Foam Agent and repo3 rows are the previously completed n30 hybrid runs. Cost is only reported where accurate input/output token counts are present in logs; Foam Agent internal token counters are treated as unreliable for this run. OpenRouter DeepSeek V4 Flash effective pricing used for recomputation: input `$0.0983/M`, output `$0.1966/M` ([source](https://openrouter.ai/deepseek/deepseek-v4-flash)).

## Leaderboard

| Experiment | Mean score | Mean coverage | Full coverage | Zero score | Mean wall s | Mean tools | Input tok | Output tok | Total tok | Est. cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| repo3 r_plus_s | 0.887 | 1.000 | 30/30 | 0/30 | 370.0 | 79.9 | n/a | n/a | n/a | n/a |
| repo3 s_plus_x | 0.873 | 1.000 | 30/30 | 0/30 | 372.2 | 82.9 | n/a | n/a | n/a | n/a |
| repo3 r_plus_s_plus_x_plus_m | 0.873 | 1.000 | 30/30 | 0/30 | 459.7 | 102.8 | n/a | n/a | n/a | n/a |
| repo3 s_plus_m | 0.870 | 1.000 | 30/30 | 0/30 | 358.6 | 79.3 | n/a | n/a | n/a | n/a |
| repo3 s_plus_x_plus_m | 0.867 | 1.000 | 30/30 | 0/30 | 382.4 | 81.6 | n/a | n/a | n/a | n/a |
| repo3 r_plus_x | 0.679 | 1.000 | 30/30 | 0/30 | 252.9 | 65.6 | n/a | n/a | n/a | n/a |
| repo3 vanilla | 0.678 | 1.000 | 30/30 | 0/30 | 266.2 | 60.4 | n/a | n/a | n/a | n/a |
| repo3 r_plus_m | 0.677 | 1.000 | 30/30 | 0/30 | 273.2 | 65.0 | n/a | n/a | n/a | n/a |
| repo3 x_plus_m | 0.662 | 1.000 | 30/30 | 0/30 | 300.6 | 65.3 | n/a | n/a | n/a | n/a |
| Foam Agent 2.0 lint-only | 0.591 | 0.788 | 21/30 | 4/30 | 494.0 | 2.0 | unreliable | unreliable | unreliable | unreliable |
| MetaOpenFOAM lint-only | 0.329 | 0.425 | 10/30 | 15/30 | 380.4 | 1.3 | 439,340 | 606,432 | 1,045,772 | $0.1624 |

## Interpretation

- Best repo3 cell remains `r_plus_s` with mean score `0.887`.
- Foam Agent 2.0 lint-only scored `0.591`, substantially below the strongest repo3 SIGA cells but above MetaOpenFOAM on this file-coverage metric. Its internal token counters are not a reliable billing ledger in this run: the wrapper reports only `140` total output tokens across 30 tasks, which is inconsistent with the generated files and stdout. I therefore do not report a Foam Agent cost here.
- MetaOpenFOAM scored `0.329`. Its main weakness was exact required-file coverage: `15` zero-score cases and only `10` full-coverage cases, despite 27/30 subprocesses exiting successfully.
- MetaOpenFOAM recorded `1,045,772` tokens and an estimated DeepSeek V4 Flash OpenRouter cost of `$0.1624`. The repo3 Claude Code stream-json logs report zero token usage for OpenRouter-routed messages, so I did not fabricate a cost for those cells.

## Artifacts

- MetaOpenFOAM run: `/home/brianliu/repo3_openfoam/data/openfoam_runs/metaopenfoam/metaopenfoam_n30_hybrid_deepseek_v4_flash_20260530`
- MetaOpenFOAM scores: `/home/brianliu/repo3_openfoam/data/openfoam_runs/metaopenfoam/metaopenfoam_n30_hybrid_deepseek_v4_flash_20260530/n30_hybrid_scores.json`
- repo3 scores: `/home/brianliu/repo3_openfoam/data/openfoam_runs/repo3_openfoam_ablations/openfoam_n30_hybrid_full_20260526/n30_hybrid_scores.json`
- Foam Agent scores: `/home/brianliu/repo3_openfoam/data/openfoam_runs/foam_agent/openfoam_n30_hybrid_foam_agent_lint_20260526d/n30_hybrid_scores.json`


# OpenFOAM n30_hybrid Results: repo3 SIGA, Foam Agent, and MetaOpenFOAM (token-instrumented re-run)

All rows use the same `foamgpt_subset_seed42_n30_hybrid` benchmark (30 tasks) and the same file-text-and-coverage metric (`0.7*similarity + 0.3*coverage`). All three agents were re-run on 2026-05-30 on `deepseek/deepseek-v4-flash` via OpenRouter, as parallel as possible (repo3: 9 cells × 15 tasks; Foam Agent: 15 tasks; MetaOpenFOAM: 15 tasks), with **robust token and tool-call instrumentation added to all three** before the run. Cost is recomputed for every row from logged input/output tokens at OpenRouter DeepSeek V4 Flash effective pricing: input `$0.0983/M`, output `$0.1966/M` ([source](https://openrouter.ai/deepseek/deepseek-v4-flash)).

## What changed in instrumentation

- **repo3** — tokens now parsed from the Claude Code stream-json terminal `result` event (per-message `usage` is zeroed on the OpenRouter route). The deepseek agent model is separated from the haiku helper; the agent-model tokens are reported. Claude Code's `total_cost_usd` is Anthropic-priced and **not** real billing, so it is relabeled `claude_reported_cost_usd_not_billing` and not used.
- **Foam Agent** — token counts now come from **real provider usage metadata** on every call, aggregated across **all** `LLMService` instances per task (it builds several) via class-level counters, and persisted to a ledger that survives mid-workflow crashes. `tool_calls` = real `LLMService.invoke()` calls. This supersedes the prior run's broken "140 output tokens / 2.0 tools" figures.
- **MetaOpenFOAM** — `tool_calls` is now the real per-call LLM count (`DeepSeek response keys:` markers), not a once-per-run proxy. Tokens were already API-sourced.

Tool-call columns are **not** directly comparable across agents (different definitions): repo3 = Claude Code stream-json `tool_use` blocks; Foam Agent = internal `LLMService.invoke()` calls; MetaOpenFOAM = deepseek LLM invocations. They are kept in one column for compactness but labeled per row.

## Leaderboard

| Experiment | Mean score | Mean cov | Full cov | Zero score | Mean wall s | Tools/task (definition) | Input tok | Output tok | Total tok | Est. cost |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|
| repo3 `r+s` | 0.8704 | 1.000 | 30/30 | 0/30 | 263.5 | 75.1 (claude tool blocks) | 25,224,599 | 654,253 | 25,878,852 | $2.6082 |
| repo3 `s+x` | 0.8664 | 1.000 | 30/30 | 0/30 | 469.8 | 69.5 (claude tool blocks) | 35,863,351 | 766,415 | 36,629,766 | $3.6760 |
| repo3 `r+s+x+m` | 0.8536 | 1.000 | 30/30 | 0/30 | 376.9 | 86.2 (claude tool blocks) | 37,060,663 | 851,930 | 37,912,593 | $3.8106 |
| repo3 `s+x+m` | 0.8472 | 1.000 | 30/30 | 0/30 | 495.4 | 85.4 (claude tool blocks) | 35,384,735 | 850,088 | 36,234,823 | $3.6454 |
| repo3 `s+m` | 0.8345 | 1.000 | 30/30 | 0/30 | 429.5 | 72.8 (claude tool blocks) | 31,375,823 | 1,038,282 | 32,414,105 | $3.2884 |
| repo3 `x+m` | 0.6968 | 1.000 | 30/30 | 0/30 | 236.0 | 57.5 (claude tool blocks) | 19,583,026 | 567,500 | 20,150,526 | $2.0366 |
| repo3 `r+m` | 0.6888 | 1.000 | 30/30 | 0/30 | 220.8 | 68.0 (claude tool blocks) | 11,014,104 | 345,651 | 11,359,755 | $1.1506 |
| repo3 `r+x` | 0.6853 | 1.000 | 30/30 | 0/30 | 179.2 | 55.2 (claude tool blocks) | 15,776,065 | 373,881 | 16,149,946 | $1.6243 |
| repo3 `vanilla` | 0.6809 | 1.000 | 30/30 | 0/30 | 196.3 | 53.8 (claude tool blocks) | 12,950,299 | 464,482 | 13,414,781 | $1.3643 |
| Foam Agent 2.0 lint-only | 0.5157 | 0.677 | 19/30 | 8/30 | 373.0 | 18.7 (LLM calls) | 1,899,925 | 596,006 | 2,495,931 | $0.3039 |
| MetaOpenFOAM lint-only | 0.3794 | 0.476 | 10/30 | 12/30 | 431.5 | 11.4 (LLM calls) | 388,420 | 646,566 | 1,034,986 | $0.1653 |

## Interpretation

- Best repo3 cell is `r+s` (mean score 0.8704); the stop-hook (`s`) factor appears in all top-5 cells. Every repo3 cell held 30/30 full coverage and 0 zero-score tasks.
- Foam Agent scored 0.5157 (21/30 success), above MetaOpenFOAM but well below the strongest repo3 cells. Its score collapses are mostly missing-required-file failures, not textual mismatch; its mean coverage is 0.677.
- MetaOpenFOAM scored 0.3794 (27/30 success). Its weakness remains exact required-file coverage (12 zero-score, 10/30 full coverage).
- **Token/cost is now reported for every row.** repo3 is by far the most expensive per task — total **$23.2045** across all 9 cells (270 task-runs) — because its agentic loop resends the growing context each tool turn and the OpenRouter deepseek route reports zero prompt-cache reads. Foam Agent ($0.3039 total) and MetaOpenFOAM ($0.1653 total) are roughly an order of magnitude cheaper per task, trading cost for the coverage/quality that repo3's harness buys with more context.
- The headline scores shifted modestly from the prior (pre-instrumentation) run — repo3 `r+s` 0.887→0.870, Foam Agent 0.591→0.516, MetaOpenFOAM 0.329→0.379 — within the expected run-to-run variance of a stochastic model; the instrumentation change does not affect scoring, only token/cost/tool accounting.

## Artifacts

- repo3 run / scores: `data/openfoam_runs/repo3_openfoam_ablations/openfoam_n30_hybrid_full_20260530_tok` · `data/openfoam_runs/repo3_openfoam_ablations/openfoam_n30_hybrid_full_20260530_tok/n30_hybrid_scores.json`
- Foam Agent run / scores: `data/openfoam_runs/foam_agent/openfoam_n30_hybrid_foam_agent_lint_20260530_tok` · `data/openfoam_runs/foam_agent/openfoam_n30_hybrid_foam_agent_lint_20260530_tok/n30_hybrid_scores.json`
- MetaOpenFOAM run / scores: `data/openfoam_runs/metaopenfoam/metaopenfoam_n30_hybrid_deepseek_v4_flash_20260530_tok` · `data/openfoam_runs/metaopenfoam/metaopenfoam_n30_hybrid_deepseek_v4_flash_20260530_tok/n30_hybrid_scores.json`
- Per-agent reports: `openfoam_n30_hybrid_repo3_results_20260530.md`, `openfoam_n30_hybrid_foam_agent_results_20260530.md`, `openfoam_n30_hybrid_metaopenfoam_results_20260530.md`

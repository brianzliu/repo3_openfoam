# repo3 OpenFOAM SIGA Ablations — n30_hybrid (token-instrumented re-run)

Evaluation date: 2026-05-30. Model: `deepseek/deepseek-v4-flash` via OpenRouter. Benchmark: `foamgpt_subset_seed42_n30_hybrid` (30 tasks). Metric: file-text similarity + required-file coverage (`0.7*mean_similarity + 0.3*coverage`). Configuration: all 9 R/S/X/M cells in parallel, 15 tasks in parallel within each cell, 25-min per-task timeout.

This run adds **robust token tracking** for repo3: token counts are parsed from the Claude Code stream-json terminal `result` event (per-message `usage` blocks are zeroed on the OpenRouter route, but the `result` event carries the true totals plus a per-model breakdown). The benchmark agent model (deepseek) is separated from Claude Code's internal helper model (haiku, used for titling/quota). Cost is computed from the deepseek tokens at OpenRouter DeepSeek V4 Flash effective pricing on 2026-05-30: input `$0.0983/M`, output `$0.1966/M` ([source](https://openrouter.ai/deepseek/deepseek-v4-flash)). Claude Code's own `total_cost_usd` is Anthropic-priced and therefore **not** real billing for an OpenRouter-routed model; it is retained per task as `claude_reported_cost_usd_not_billing` but not used here.

## Cell leaderboard

| Cell | Mean score | Mean cov | Full cov | Zero | Mean wall s | Mean tools | Input tok | Output tok | Total tok | Est. cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `r+s` | 0.8704 | 1.000 | 30/30 | 0 | 263.5 | 75.1 | 25,224,599 | 654,253 | 25,878,852 | $2.6082 |
| `s+x` | 0.8664 | 1.000 | 30/30 | 0 | 469.8 | 69.5 | 35,863,351 | 766,415 | 36,629,766 | $3.6760 |
| `r+s+x+m` | 0.8536 | 1.000 | 30/30 | 0 | 376.9 | 86.2 | 37,060,663 | 851,930 | 37,912,593 | $3.8106 |
| `s+x+m` | 0.8472 | 1.000 | 30/30 | 0 | 495.4 | 85.4 | 35,384,735 | 850,088 | 36,234,823 | $3.6454 |
| `s+m` | 0.8345 | 1.000 | 30/30 | 0 | 429.5 | 72.8 | 31,375,823 | 1,038,282 | 32,414,105 | $3.2884 |
| `x+m` | 0.6968 | 1.000 | 30/30 | 0 | 236.0 | 57.5 | 19,583,026 | 567,500 | 20,150,526 | $2.0366 |
| `r+m` | 0.6888 | 1.000 | 30/30 | 0 | 220.8 | 68.0 | 11,014,104 | 345,651 | 11,359,755 | $1.1506 |
| `r+x` | 0.6853 | 1.000 | 30/30 | 0 | 179.2 | 55.2 | 15,776,065 | 373,881 | 16,149,946 | $1.6243 |
| `vanilla` | 0.6809 | 1.000 | 30/30 | 0 | 196.3 | 53.8 | 12,950,299 | 464,482 | 13,414,781 | $1.3643 |

Total estimated OpenRouter cost across all 9 cells (270 task-runs): **$23.2045**. Tool counts are Claude Code stream-json `tool_use` blocks (`claude_stream_json_tool_use_blocks`). Token counts are the deepseek agent model only; the haiku helper averaged ~177 input / ~5094 output tokens per task and is excluded.

## Token-accounting notes

- All 270 task-runs except one (`r+m/LadenburgJet60psi`, which timed out before emitting a terminal `result` event) carry real token usage; 269/270 have `token_usage_found=true`.
- repo3's input-token totals are large (tens of millions per cell) because the agentic loop resends the growing context on every tool turn and the OpenRouter deepseek route reports **zero** prompt-cache reads (`cache_read_input_tokens=0`). This is the dominant cost driver and is the main reason repo3 is far more expensive per task than Foam Agent or MetaOpenFOAM despite similar output-token volume.
- 13 of 270 task-runs hit the 25-min timeout (mostly in the verification-heavy `s+x`/`s+x+m` cells); they still wrote required files before being killed, so coverage stayed 1.000.

## Hardest tasks (mean score across all 9 cells)

- `coolingSphere`: 0.5228
- `throttle3D`: 0.6447
- `sphere7ProjectedEdges`: 0.6723
- `refineFieldDirs`: 0.6852
- `hotRoomBoussinesqSteady`: 0.6898

## Easiest tasks (mean score across all 9 cells)

- `cavityClipped`: 0.8926
- `angledDuctExplicitFixedCoeff`: 0.8819
- `europeanCall`: 0.8618
- `externalCoupledCavity`: 0.8595
- `nc7h16`: 0.8541

## Interpretation

- Best cell on this re-run is `r+s` (mean score 0.8704), consistent with the prior n30_hybrid run. The stop-hook (`s`) factor is in all top-5 cells.
- Every cell held full required-file coverage (30/30) and produced zero zero-score tasks — repo3's defining strength on this benchmark.
- `r+s` is also near the cost/quality sweet spot: it is the cheapest of the high-scoring `s`-cells ($2.6082) because it avoids the long validation loops that inflate `s+x`/`s+x+m` wall time and input tokens.

## Artifacts

- Run root: `data/openfoam_runs/repo3_openfoam_ablations/openfoam_n30_hybrid_full_20260530_tok`
- Scores: `data/openfoam_runs/repo3_openfoam_ablations/openfoam_n30_hybrid_full_20260530_tok/n30_hybrid_scores.json`
- Batch summary: `data/openfoam_runs/repo3_openfoam_ablations/openfoam_n30_hybrid_full_20260530_tok/batch_summary.json`

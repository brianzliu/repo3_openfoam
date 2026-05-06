# OpenFOAM Benchmark Setup

This repo now contains an OpenFOAM-specific benchmark path for comparing:

- `repo3_openfoam` using the Claude Code plugin in this repo
- `Foam-Agent`

Both are wired to the same 5-case FoamGPT subset defined in:

- `configs/openfoam_benchmark/foamgpt_subset_seed42.json`

The materialized benchmark assets live under:

- `data/openfoam_benchmark/foamgpt_subset_seed42`

## 1. Materialize the subset

```bash
python3 scripts/openfoam/materialize_foamgpt_subset.py
```

## 2. Build a fresh OpenFOAM Chroma DB

Fast local hash embedding:

```bash
uv run --script scripts/openfoam/build_openfoam_chromadb.py --force
```

OpenRouter embedding mode:

```bash
OPENROUTER_API_KEY=... \
OPENFOAM_EMBEDDING_PROVIDER=openai \
uv run --script scripts/openfoam/build_openfoam_chromadb.py --force --embedding-provider openai
```

This writes to:

- `data/openfoam_benchmark/chromadb_openfoam`

It does not modify the old GEOS vector DB.

## 3. Dry-run the repo3_openfoam benchmark

```bash
python3 scripts/openfoam/run_repo3_openfoam_eval.py \
  --run-name dsv4_seed42 \
  --dry-run
```

Runtime defaults:

- model: `deepseek/deepseek-v4-flash`
- endpoint: `https://openrouter.ai/api/anthropic`

For a real run, export `OPENROUTER_API_KEY`.

## 4. Dry-run Foam-Agent on the same subset

```bash
python3 scripts/openfoam/run_foam_agent_eval.py \
  --run-name dsv4_seed42 \
  --dry-run
```

Foam-Agent is routed through OpenRouter by setting:

- `FOAMAGENT_MODEL_PROVIDER=openai`
- `FOAMAGENT_MODEL_VERSION=deepseek/deepseek-v4-flash`
- `OPENAI_API_KEY=$OPENROUTER_API_KEY`
- `OPENAI_BASE_URL=https://openrouter.ai/api/v1`

## 5. Evaluate both runs

```bash
python3 scripts/openfoam/evaluate_openfoam_runs.py \
  --agent-run repo3=data/openfoam_runs/repo3_openfoam/dsv4_seed42 \
  --agent-run foam_agent=data/openfoam_runs/foam_agent/dsv4_seed42 \
  --output data/openfoam_runs/dsv4_seed42_eval.json
```

## Output layout

- `data/openfoam_runs/repo3_openfoam/<run>/<case>/...`
- `data/openfoam_runs/foam_agent/<run>/<case>/...`

Each case directory stores:

- `inputs/` for generated case files
- `stdout.txt`
- `stderr.txt`
- `status.json`
- `metadata.json`

This keeps the two agents easy to compare and makes future ablations easy to add by changing:

- subset manifest
- model flag
- vector DB path
- plugin/hook enablement

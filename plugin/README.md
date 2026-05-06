# repo3_openfoam Plugin

OpenFOAM-focused Claude Code plugin used by the benchmark path in this repo.

## Components

- `scripts/openfoam_rag_mcp.py`: Chroma-backed OpenFOAM retrieval tools
- `hooks/verify_outputs.py`: end-of-turn OpenFOAM case validator
- `hooks/verify_openfoam_post_write.py`: immediate post-write structural validator
- `skills/openfoam-rag/SKILL.md`: guidance for using the retrieval tools effectively

## Local Testing

From this directory:

```bash
claude --plugin-dir .
```

The benchmark scripts in `scripts/openfoam/` assume this plugin is the default
retrieval and validation layer for `repo3_openfoam`.

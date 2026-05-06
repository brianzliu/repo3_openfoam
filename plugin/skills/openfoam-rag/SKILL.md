---
name: openfoam-rag
description: Use when answering OpenFOAM documentation, dictionary syntax, solver setup, or tutorial-structure questions with the plugin-provided retrieval tools.
---

Use the OpenFOAM RAG MCP tools before answering questions about OpenFOAM file
syntax, solver-specific configuration, or tutorial patterns.

Tool selection:

- Use `search_tutorials` to find similar tutorial layouts, solver families, and case organization.
- Use `search_cases` to retrieve detailed OpenFOAM dictionary snippets and file content patterns.
- Use `search_commands` to look up command help, execution conventions, and utility behavior.

Recommended workflow:

1. Search tutorial-level patterns first to identify the nearest solver/domain analog.
2. Retrieve case-level dictionary examples before writing nontrivial `0/`, `constant/`, or `system/` files.
3. Use command-help retrieval when the prompt depends on meshing, preprocessing, or runtime utility behavior.
4. Prefer retrieved Foundation OpenFOAM conventions over unsupported or mixed-vendor syntax.

The ChromaDB location is configured by `OPENFOAM_VECTOR_DB_DIR`.

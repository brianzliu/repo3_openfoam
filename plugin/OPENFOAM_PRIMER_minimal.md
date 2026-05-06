# OpenFOAM Primer (minimal)

OpenFOAM is an open-source CFD / multiphysics simulator. Tasks require authoring one or more OpenFOAM case files using the usual case structure (`0/`, `constant/`, `system/`). Values are typically in SI units unless the case dictionary explicitly rescales them.

## Where things live (inside the workspace / host mount)

- `/data/brianliu/OpenFOAM-13/tutorials/` — authoritative tutorial cases and directory patterns. Treat these as the primary reference.
- `/data/brianliu/OpenFOAM-13/src/` and `/data/brianliu/OpenFOAM-13/applications/` — source code and solver/utility definitions when you need exact keyword or model names.
- `/workspace/inputs/` — where you must write the final case files.

## Standard case skeleton
```text
inputs/
  0/           # initial and boundary fields
  constant/    # physical properties, turbulence / transport models
  system/      # controlDict, fvSchemes, fvSolution, mesh dictionaries
```

## Additional MCP tools
Find a similar tutorial or case via MCP retrieval (`search_tutorials` for tutorial structure; `search_cases` for detailed dictionary snippets; `search_commands` for utility and command behavior). Use those results before guessing solver-specific syntax or file patterns.

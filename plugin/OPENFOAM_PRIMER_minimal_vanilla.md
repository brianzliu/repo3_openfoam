# OpenFOAM Primer (minimal, vanilla-CC-compatible)

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

## Recommended workflow
1. Find the nearest matching tutorial using `Glob`, `Grep`, and `Read` against `/data/brianliu/OpenFOAM-13/tutorials/` and `/data/brianliu/OpenFOAM-13/src/`.
2. Read the matching tutorial files and mirror their structure for the requested solver family.
3. Write the required files under `/workspace/inputs/<folder>/<file>`.
4. Check that cross-file assumptions are consistent: solver family, patch names, turbulence model, field names, and numerics blocks.

That's it.

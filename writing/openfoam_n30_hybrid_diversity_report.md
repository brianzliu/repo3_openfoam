# OpenFOAM `n30_hybrid` Diversity Report

Date: 2026-05-26 UTC

## Artifacts

- Config: `configs/openfoam_benchmark/foamgpt_subset_seed42_n30_hybrid.json`
- Summary: `configs/openfoam_benchmark/foamgpt_subset_seed42_n30_hybrid_summary.json`
- Materialized benchmark root: `data/openfoam_benchmark/foamgpt_subset_seed42_n30_hybrid`

## Scope

This report analyzes the current `foamgpt_subset_seed42_n30_hybrid` benchmark subset as its own 30-task evaluation set. The focus is the subset's internal diversity across OpenFOAM domains, category labels, solver families, and required-file structure.

## High-Level Summary

The `n30_hybrid` subset contains:

- `30` tasks
- `11` represented domains
- `9` represented `case_category` labels
- `26` solver families

The subset is broad in physics-family and solver coverage, with deliberate representation from rare domains such as `DNS`, `financial`, `discreteMethods`, and `molecularDynamics`. It is not category-balanced in a strict sense; `case_category = None` remains the largest bucket with `17/30` tasks. Even so, the subset still includes meaningful coverage of rarer labeled categories such as `LES`, `Lagrangian`, `hopper`, `damBreak`, and `decompressionTank`.

## Domain Coverage

Domain distribution:

| Domain | Count |
| --- | ---: |
| `combustion` | 4 |
| `incompressible` | 4 |
| `multiphase` | 4 |
| `compressible` | 3 |
| `heatTransfer` | 3 |
| `lagrangian` | 3 |
| `mesh` | 3 |
| `discreteMethods` | 2 |
| `molecularDynamics` | 2 |
| `DNS` | 1 |
| `financial` | 1 |

Assessment:

- All major OpenFOAM task families present in the FoamGPT test split are represented.
- The subset avoids collapsing into only the large mainstream buckets such as incompressible or multiphase.
- The smallest domains are still present, which is useful for transfer and robustness testing.

## Category Coverage

Category distribution:

| Category | Count |
| --- | ---: |
| `None` | 17 |
| `Lagrangian` | 2 |
| `LES` | 2 |
| `RAS` | 2 |
| `laminar` | 2 |
| `hopper` | 2 |
| `cavity` | 1 |
| `damBreak` | 1 |
| `decompressionTank` | 1 |

Assessment:

- The subset spans a wider range of labeled task styles than a purely domain-stratified sample would.
- `None` is still dominant, so the subset should be understood as domain-diverse first and category-diverse second.
- Rare categories are represented by at least one concrete case instead of being absent entirely.

## Solver-Family Coverage

The subset covers `26` solver families across `30` tasks.

Solver counts:

| Solver | Count |
| --- | ---: |
| `buoyantFoam` | 2 |
| `dsmcFoam` | 2 |
| `particleFoam` | 2 |
| `mdEquilibrationFoam` | 2 |
| `rhoCentralFoam` | 1 |
| `reactingFoam` | 1 |
| `rhoSimpleFoam` | 1 |
| `dnsFoam` | 1 |
| `icoFoam` | 1 |
| `pimpleFoam` | 1 |
| `chtMultiRegionFoam` | 1 |
| `denseParticleFoam` | 1 |
| `driftFluxFoam` | 1 |
| `interFoam` | 1 |
| `compressibleMultiphaseInterFoam` | 1 |
| `rhoPimpleFoam` | 1 |
| `financialFoam` | 1 |
| `XiFoam` | 1 |
| `chemFoam` | 1 |
| `pisoFoam` | 1 |
| `refineMesh` | 1 |
| `foamyHexMesh` | 1 |
| `blockMesh` | 1 |
| `buoyantReactingFoam` | 1 |
| `shallowWaterFoam` | 1 |
| `cavitatingFoam` | 1 |

Assessment:

- Solver breadth is strong relative to subset size: `26` solver families for `30` tasks leaves little redundancy.
- Duplicate solver counts mostly occur where they add useful within-family variation rather than accidental repetition.
- The subset includes both mainstream flow solvers and specialized interfaces such as `financialFoam`, `dsmcFoam`, `mdEquilibrationFoam`, and meshing-only workflows.

## Case Inventory

| Case | Domain | Category | Solver |
| --- | --- | --- | --- |
| `LadenburgJet60psi` | `compressible` | `None` | `rhoCentralFoam` |
| `aachenBomb` | `combustion` | `Lagrangian` | `reactingFoam` |
| `angledDuctExplicitFixedCoeff` | `compressible` | `None` | `rhoSimpleFoam` |
| `boxTurb16` | `DNS` | `None` | `dnsFoam` |
| `cavityClipped` | `incompressible` | `cavity` | `icoFoam` |
| `channel395` | `incompressible` | `LES` | `pimpleFoam` |
| `coolingSphere` | `heatTransfer` | `None` | `chtMultiRegionFoam` |
| `cyclone` | `lagrangian` | `None` | `denseParticleFoam` |
| `dahl` | `multiphase` | `RAS` | `driftFluxFoam` |
| `damBreak` | `multiphase` | `damBreak` | `interFoam` |
| `damBreak4phase` | `multiphase` | `laminar` | `compressibleMultiphaseInterFoam` |
| `decompressionTank` | `compressible` | `decompressionTank` | `rhoPimpleFoam` |
| `europeanCall` | `financial` | `None` | `financialFoam` |
| `externalCoupledCavity` | `heatTransfer` | `None` | `buoyantFoam` |
| `freeSpacePeriodic` | `discreteMethods` | `None` | `dsmcFoam` |
| `hopperEmptying` | `lagrangian` | `hopper` | `particleFoam` |
| `hopperInitialState` | `lagrangian` | `hopper` | `particleFoam` |
| `hotRoomBoussinesqSteady` | `heatTransfer` | `None` | `buoyantFoam` |
| `moriyoshiHomogeneous` | `combustion` | `RAS` | `XiFoam` |
| `nc7h16` | `combustion` | `None` | `chemFoam` |
| `periodicCubeArgon` | `molecularDynamics` | `None` | `mdEquilibrationFoam` |
| `periodicCubeWater` | `molecularDynamics` | `None` | `mdEquilibrationFoam` |
| `porousBlockage` | `incompressible` | `laminar` | `pisoFoam` |
| `refineFieldDirs` | `mesh` | `None` | `refineMesh` |
| `simpleShapes` | `mesh` | `None` | `foamyHexMesh` |
| `sphere7ProjectedEdges` | `mesh` | `None` | `blockMesh` |
| `splashPanel` | `combustion` | `Lagrangian` | `buoyantReactingFoam` |
| `squareBump` | `incompressible` | `None` | `shallowWaterFoam` |
| `supersonicCorner` | `discreteMethods` | `None` | `dsmcFoam` |
| `throttle3D` | `multiphase` | `LES` | `cavitatingFoam` |

## All Experiments

The full set of experiments in `n30_hybrid` is:

- `LadenburgJet60psi`
- `aachenBomb`
- `angledDuctExplicitFixedCoeff`
- `boxTurb16`
- `cavityClipped`
- `channel395`
- `coolingSphere`
- `cyclone`
- `dahl`
- `damBreak`
- `damBreak4phase`
- `decompressionTank`
- `europeanCall`
- `externalCoupledCavity`
- `freeSpacePeriodic`
- `hopperEmptying`
- `hopperInitialState`
- `hotRoomBoussinesqSteady`
- `moriyoshiHomogeneous`
- `nc7h16`
- `periodicCubeArgon`
- `periodicCubeWater`
- `porousBlockage`
- `refineFieldDirs`
- `simpleShapes`
- `sphere7ProjectedEdges`
- `splashPanel`
- `squareBump`
- `supersonicCorner`
- `throttle3D`

## Structural Diversity

The subset is also diverse in the shape of the required outputs:

- some tasks require only `1` benchmark file
- others require multi-file outputs with `2`, `3`, `4`, or `5` required files
- the set includes ordinary field dictionaries, multiphase initial states, meshing inputs, conjugate heat-transfer layouts, DSMC boundary data, and utility-specific control files

Representative structural variety:

- single-file tasks: `boxTurb16`, `cavityClipped`, `coolingSphere`, `simpleShapes`, `sphere7ProjectedEdges`
- medium multi-file tasks: `LadenburgJet60psi`, `channel395`, `freeSpacePeriodic`, `squareBump`, `throttle3D`
- broader case assemblies: `damBreak4phase`, `externalCoupledCavity`, `refineFieldDirs`

This matters because benchmark difficulty is not only about physics category. It also depends on how much file-level coordination a case demands.

## Pilot-5 Slice

The designated pilot-5 within this subset is:

- `aachenBomb`
- `cavityClipped`
- `damBreak`
- `refineFieldDirs`
- `sphere7ProjectedEdges`

This pilot slice spans:

- `5` different domains
- `5` different solver families
- both labeled and unlabeled categories
- both compact and multi-file case structures

So it is a reasonable miniature probe of the larger `n30_hybrid` set, though it is still lighter than the full subset on heat-transfer, molecular-dynamics, and financial cases.

## Overall Assessment

The `n30_hybrid` subset is a strong general-purpose OpenFOAM benchmark slice for agent evaluation because it combines:

- full domain coverage across the dataset's 11 domains
- high solver-family breadth for only 30 tasks
- nontrivial category variation, including several rare labeled categories
- structural variation in file-count and case-layout demands

Its main limitation is category skew:

- `None` still accounts for more than half the subset
- some rare categories are represented by only one case

That said, for a 30-task benchmark, the set is meaningfully diverse. It is broad enough to test transfer across solver families and simulation styles, while still compact enough to run as a practical evaluation suite.

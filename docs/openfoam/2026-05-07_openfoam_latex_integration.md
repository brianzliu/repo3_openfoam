# OpenFOAM Results Integration for the GEOS SIGA Paper

This file contains recommended LaTeX edits to incorporate the new OpenFOAM transfer results into the GEOS paper draft.

Design choice:

- Keep the main paper focused on GEOS.
- Add only the strongest OpenFOAM takeaway in the main text: the adapter recipe transfers at small scale, and `S` is again the dominant reliability mechanism.
- Push most OpenFOAM detail to the appendix because:
  - it is a different metric than TreeSim
  - it is only a 5-task subset
  - it is single-seed per cell
  - the Foam-Agent comparison is against `lint_only`, not Foam-Agent's original execute-and-review mode

## 1. Replace the Contributions paragraph

Replace the current `\paragraph{Contributions.}` block in the Introduction with the following:

```latex
\paragraph{Contributions.}
\textbf{(i)} We introduce a held-out GEOS deck-authoring benchmark for coupled multiphysics subsurface simulation setup, scored by a tree-aware structural-similarity metric (TreeSim, \S\ref{subsec:metric}).
\textbf{(ii)} We define and evaluate \textbf{Simulator-Interface Grounding Adapters (SIGA)} as wrapper-level grounding around an existing coding harness, using a Resolution-IV factorial over four adapter components plus a self-evolved monolithic variant.
\textbf{(iii)} We show that adapter gains are concentrated on a hard tail of compound multiphysics tasks: the best cells mainly reduce catastrophic failures and across-seed variance, while leaving easy tasks and strictly perfect decks largely unchanged.
\textbf{(iv)} We provide a bottleneck analysis that decomposes adapter wins and surviving errors into structural categories, showing that schema-based grounding helps block presence but does not solve attribute-level semantic mistakes.
\textbf{(v)} We report two negative or cautionary findings for scientific-agent design: procedural memory exposed only as a retrieval tool is never invoked in our task--model pairs, and an explicit human-consultation channel is rarely used when an executable example library is available as an alternative oracle.
\textbf{(vi)} We add a preliminary cross-simulator transfer study to OpenFOAM case authoring, showing that the same adapter recipe transfers beyond GEOS XML decks: on a small 5-task subset, the stop-hook component is again the dominant reliability intervention, and the best OpenFOAM cell outperforms both vanilla Claude Code and a constrained Foam-Agent lint-only baseline (App.~\ref{app:openfoam-transfer}).
```

## 2. Add a main-paper Results subsection

Insert the following subsection in the main paper after `\subsection{Cross-model and cross-harness}` and before `\subsection{Harness-less one-shot: a model-class lower bound}`.

```latex
\subsection{Cross-simulator transfer: OpenFOAM}
\label{subsec:openfoam-transfer}

To test whether SIGA-style adaptations transfer beyond GEOS XML authoring, we ported the same $\{R,S,X,M\}$ recipe to OpenFOAM case authoring on a 5-task FoamGPT-derived subset (App.~\ref{app:openfoam-transfer}). The OpenFOAM port replaces GEOS-specific assets with three retrieval collections over tutorial structure, detailed case snippets, and command/help text; a lightweight always-on case-structure primer; and a heuristic validator/stop-hook that checks required files, balanced delimiters, \texttt{FoamFile} headers, and key dictionary sections. Because the OpenFOAM benchmark uses a file-text-and-coverage metric rather than TreeSim and is single-seed per cell, we treat it as transfer evidence rather than a second headline benchmark.

Even under that stricter framing, the qualitative lesson transfers. The best OpenFOAM cell, $R{+}S$, reaches $0.871$ on the 5-task subset, compared with $0.466$ for vanilla Claude Code and $0.569$ for Foam-Agent in \emph{lint-only} mode. More importantly, every $S$-enabled OpenFOAM cell achieves full required-file coverage (5/5 tasks) and no zero-score failures, whereas vanilla covers only 3/5 tasks and the $R{+}X$ cell only 1/5. A factor-style readout on the 8-cell OpenFOAM subset assigns the largest effect to $S$ ($+0.328$ mean score and $+0.45$ Pass@0.7), with $M$ positive and $R/X$ slightly negative (App.~\ref{app:openfoam-transfer}). We read this as small-scale external evidence that the SIGA recipe is not specific to XML-backed simulator interfaces: the dominant transferable mechanism is again forced end-of-turn verification rather than optional retrieval or optional validation tools.
```

## 3. Add a Discussion caveat paragraph

Insert the following paragraph into `\section{Discussion and limitations}` after the cross-model / cross-harness paragraph or near the end of the limitations list.

```latex
\paragraph{OpenFOAM transfer is supportive, not headline-grade.}
The OpenFOAM transfer study in App.~\ref{app:openfoam-transfer} is deliberately framed as external evidence rather than a second benchmark of equal weight to GEOS. It uses a different metric (file-text similarity plus required-file coverage rather than TreeSim), only 5 tasks, and one run per cell. The Foam-Agent comparison is also constrained: Foam-Agent's native design is full execute-and-review, but the stable comparison we could obtain in our environment was \texttt{lint\_only}. We therefore interpret the OpenFOAM result narrowly: it supports the portability of the SIGA recipe, especially the stop-hook component, but does not establish a definitive head-to-head ranking against OpenFOAM-native agent frameworks.
```

## 4. Add a brief OpenFOAM sentence in the Conclusion

Append the following sentence near the end of the Conclusion, before the final sentence if you want the paper to end on the broader framing.

```latex
A small transfer study on OpenFOAM case authoring supports the broader claim that the recipe is not GEOS-specific: on a 5-task subset, the same stop-hook-heavy adaptation pattern again dominates vanilla Claude Code and a constrained Foam-Agent lint-only baseline.
```

## 5. Add a new appendix section

Insert the following appendix section after `\section{Cross-model and cross-harness — full panels}` or after `\section{Additional results}`. The label is new, so make sure the contribution and main-text references above match it.

```latex
\section{OpenFOAM transfer study}
\label{app:openfoam-transfer}

\paragraph{Motivation.}
The main paper studies SIGA on GEOS, where the executable interface is a structured XML deck with an explicit XSD schema. To test whether the same adapter recipe transfers beyond GEOS and beyond XML-backed simulator interfaces, we ran a small OpenFOAM case-authoring companion study in a separate repository path (\texttt{repo3\_openfoam}). We treat the result as transfer evidence rather than a second benchmark because the setup differs in both metric and scale.

\paragraph{OpenFOAM adaptation of \texorpdfstring{$R/S/X/M$}{R/S/X/M}.}
We ported the same four binary factors to OpenFOAM case authoring. \textbf{R} replaced the GEOS RAG collections with three ChromaDB collections over OpenFOAM tutorial structure, detailed case snippets, and command/help text. \textbf{M} replaced the GEOS memory cheatsheet with a lightweight always-on primer describing the standard OpenFOAM case skeleton (\texttt{0/}, \texttt{constant/}, \texttt{system/}) and the relevant tutorial/source-tree locations. \textbf{S} replaced the GEOS XML stop-hook with an OpenFOAM stop-hook that blocks turn completion if required files are missing or if generated dictionaries fail heuristic structural checks. \textbf{X} replaced the \texttt{xmllint} MCP with an agent-callable OpenFOAM validator using the same case checks as the hook. Because OpenFOAM lacks a canonical XSD-style schema for the benchmark dictionaries, the OpenFOAM validator checks required-file presence, balanced delimiters, \texttt{FoamFile} headers, and key dictionary sections rather than schema compliance.

\paragraph{Benchmark and metric.}
The OpenFOAM subset contains 5 tasks sampled from a FoamGPT-derived benchmark: \texttt{boundaryWallFunctionsProfile}, \texttt{Grossetete}, \texttt{helmholtzResonance}, \texttt{externalCoupledCavity}, and \texttt{damBreakWithObstacle}. Each task specifies a set of required files. We score a run using a file-text-and-coverage metric: each missing required file receives score 0; present files are compared to ground truth via normalized text similarity; and the case score is
\[
\mathrm{Score} = 0.7 \cdot \mathrm{mean\_similarity} + 0.3 \cdot \mathrm{coverage}.
\]
This is analogous to failures-as-zero reporting but is not TreeSim.

\paragraph{Foam-Agent baseline.}
The OpenFOAM-native baseline is Foam-Agent. We emphasize a caveat that matters for interpretation: Foam-Agent's native workflow is not lint-only, but a fuller plan--write--execute--review loop. The stable comparison available in our environment used \texttt{execution\_mode=lint\_only}; execute-mode runs failed to yield usable benchmark outputs. We therefore compare against \emph{Foam-Agent$_{\text{lint}}$} and treat the result as a constrained baseline rather than a full head-to-head against Foam-Agent's intended execution-coupled workflow.

\begin{table}[t]
  \caption{OpenFOAM transfer-study summary on the 5-task subset. Mean score is the file-text-and-coverage metric described above. \emph{Full coverage} is the number of tasks for which all required files were produced; \emph{Pass@0.7} is the number of tasks with score $\geq 0.7$.}
  \label{tab:openfoam-summary}
  \centering
  \small
  \begin{tabular}{lcccccc}
    \toprule
    \textbf{Cell} & \textbf{Mean score} & \textbf{$\Delta$ vs Vanilla} & \textbf{$\Delta$ vs Foam-Agent$_{\text{lint}}$} & \textbf{Pass@0.7} & \textbf{Full coverage} & \textbf{Wall s} \\
    \midrule
    Vanilla                  & 0.466 & ---    & $-0.103$ & 3/5 & 3/5 & 1921 \\
    R$+$M                    & 0.736 & $+0.270$ & $+0.167$ & 2/5 & 5/5 & 1276 \\
    S$+$M                    & 0.787 & $+0.321$ & $+0.218$ & 4/5 & 5/5 & 1482 \\
    R$+$S                    & \textbf{0.871} & \textbf{$+0.405$} & \textbf{$+0.302$} & \textbf{5/5} & \textbf{5/5} & \textbf{380} \\
    X$+$M                    & 0.712 & $+0.246$ & $+0.143$ & 4/5 & 5/5 & 1644 \\
    R$+$X                    & 0.145 & $-0.321$ & $-0.424$ & 1/5 & 1/5 & 778 \\
    S$+$X                    & 0.849 & $+0.383$ & $+0.280$ & \textbf{5/5} & \textbf{5/5} & 1020 \\
    R$+$S$+$X$+$M            & 0.862 & $+0.396$ & $+0.294$ & \textbf{5/5} & \textbf{5/5} & 1419 \\
    S$+$X$+$M                & 0.822 & $+0.356$ & $+0.253$ & \textbf{5/5} & \textbf{5/5} & 1147 \\
    Foam-Agent$_{\text{lint}}$ & 0.569 & $+0.103$ & ---       & 1/5 & 3/5 & 547 \\
    \bottomrule
  \end{tabular}
\end{table}

\paragraph{Headline.}
The main OpenFOAM result is qualitative rather than statistical: the same component that matters most in GEOS reliability is again the strongest signal here. The best OpenFOAM cell is $R{+}S$ at 0.871, well above vanilla Claude Code (0.466) and Foam-Agent$_{\text{lint}}$ (0.569). More importantly, every $S$-enabled cell achieves full required-file coverage and no zero-score tasks, while vanilla covers only 3/5 tasks and $R{+}X$ only 1/5.

\paragraph{Factor-style readout.}
Using the 8-cell OpenFOAM subset only and reporting single-run descriptive effects, the factor-style main-effect analogue is:
\[
R: -0.050,\quad
S: +0.328,\quad
X: -0.073,\quad
M: +0.192
\]
on mean score, and
\[
R: -0.15,\quad
S: +0.45,\quad
X: +0.05,\quad
M: +0.05
\]
on Pass@0.7. This again points to $S$ as the dominant reliability intervention and suggests that optional retrieval or optional validation, without a hard end-of-turn gate, are weaker.

\begin{table}[t]
  \caption{Per-task OpenFOAM transfer-study scores. The catastrophic failures are concentrated in non-$S$ cells, especially Vanilla and $R{+}X$.}
  \label{tab:openfoam-per-task}
  \centering
  \footnotesize
  \begin{tabular}{lccccc}
    \toprule
    \textbf{Cell} & \textbf{boundaryWallFunctionsProfile} & \textbf{Grossetete} & \textbf{helmholtzResonance} & \textbf{externalCoupledCavity} & \textbf{damBreakWithObstacle} \\
    \midrule
    Vanilla                  & 0.751 & 0.817 & 0.000 & 0.762 & 0.000 \\
    R$+$M                    & 0.650 & 0.817 & 0.681 & 1.000 & 0.532 \\
    S$+$M                    & 0.860 & 0.966 & 0.788 & 0.595 & 0.723 \\
    R$+$S                    & 0.907 & 0.968 & 0.858 & 0.900 & 0.723 \\
    X$+$M                    & 0.719 & 0.820 & 0.727 & 0.762 & 0.531 \\
    R$+$X                    & 0.724 & 0.000 & 0.000 & 0.000 & 0.000 \\
    S$+$X                    & 0.965 & 0.870 & 0.787 & 0.899 & 0.723 \\
    R$+$S$+$X$+$M            & 0.964 & 0.967 & 0.760 & 0.899 & 0.722 \\
    S$+$X$+$M                & 0.807 & 0.788 & 0.850 & 0.943 & 0.722 \\
    Foam-Agent$_{\text{lint}}$ & 0.657 & 0.165 & 0.649 & 0.636 & 0.736 \\
    \bottomrule
  \end{tabular}
\end{table}

\paragraph{Zero-score failures.}
The zero scores in the OpenFOAM study are failures-as-zero in the literal sense: required output files were missing. Vanilla drops to 0 on \texttt{helmholtzResonance} and \texttt{damBreakWithObstacle}; $R{+}X$ drops to 0 on 4 of 5 tasks. No $S$-enabled cell exhibits a zero-score failure. This is the clearest OpenFOAM analogue to the GEOS reliability story: the stop hook prevents the agent from ending the turn with structurally incomplete deliverables.

\paragraph{Interpretation.}
We do not claim the OpenFOAM result has the same evidentiary weight as the GEOS benchmark. It is smaller, single-seed, and scored differently. What it does show is that the SIGA recipe is not obviously tied to XML or to GEOS-specific assets. The transferable piece is the workflow logic: retrieval and procedural guidance matter somewhat, but the dominant and most portable intervention is forced end-of-turn verification that prevents silent incompleteness.
```

## 6. Optional: add one sentence to the Abstract

I would only do this if you want the paper to make a broader “not GEOS-only” claim in the abstract. If you want to keep the abstract strictly about GEOS, skip this.

Possible insertion near the end of the abstract:

```latex
A small OpenFOAM transfer study further suggests that the same adapter recipe is not specific to GEOS XML decks: on a 5-task subset, the stop-hook component again dominates reliability.
```

## 7. Why this packaging is the safest framing

This packaging is conservative and paper-appropriate because it preserves the current paper's center of gravity:

- GEOS remains the headline benchmark.
- OpenFOAM appears as transfer evidence, not as an equal-weight second benchmark.
- The strongest OpenFOAM result is reported in the main text.
- The quantitative table burden and metric caveats are moved to the appendix.
- The Foam-Agent execute-vs-lint caveat is made explicit, which avoids overstating the comparison.

## 8. Recommended minimal adoption

If you want the least invasive version, apply only:

1. the new contribution bullet
2. the new main-text OpenFOAM transfer subsection
3. the appendix section `\ref{app:openfoam-transfer}`

That is enough to integrate the new findings cleanly without forcing a major rewrite of the existing draft.

# Placenta showcase (frozen)

A real `autoreview` run on a non-trivial analysis: a comparative characterization
of two integrated human placenta scRNA-seq atlases - **first trimester vs term** -
from the open-ended prompt *"what do you notice?"*. It is kept here as a
real-world demonstration of the full plan -> execute -> review pipeline. Read
`.autoreview/REPORT.md` for the complete two-track output.

## The data (not bundled - on Zenodo)

The two inputs are openly deposited:

> Hong, Jiang; Deng, Qiaolin. *Integrated and annotated human placenta scRNA-seq
> matrices.* Zenodo, 2024.
> DOI: [10.5281/zenodo.11103744](https://doi.org/10.5281/zenodo.11103744) (CC BY 4.0).
> Files: `first_trimester_final.h5ad` (1.0 GB), `term_final.h5ad` (349.8 MB).

Raw data is never committed here. The bundled `.autoreview/manifest.json` records
the sha256 of each input, so after downloading you can confirm you have the exact
matrices that were reviewed (place them at the recorded paths, then
`autoreview guard verify`).

## Re-verify the numbers with no data

The deterministic track does not need the matrices: the numeric/logic checks run
on the numbers each claim recorded. So the entire numeric review reproduces from
this folder alone:

```bash
cd examples/placenta_showcase
autoreview status                                          # 12 claims, both tracks
autoreview check run --specs extra.json --force --dry-run  # re-run every invariant
autoreview report                                          # regenerate REPORT.md
```

`extra.json` holds the task-specific invariants the `reviewer-numeric` agent
authored - cross-claim identities, sum-to-N, `count == round(frac*N)`, orderings,
and sign-consistency of log2 ratios. All 12 claims pass the numeric track.

## What the run found

- **Shape.** First trimester is larger by cells (35,461 x 5,000 HVG; raw 27,526
  genes); term keeps its full gene set (23,378 x 25,777) and ships no raw matrix.
- **A raw-data asymmetry the review pins down.** Term `layers['counts']` is genuine
  raw integer UMIs while term `X` is log-normalized; first trimester has **no**
  genuine raw counts - its `X`, `layers['counts']`, and `raw.X` are all
  non-integer/log-normalized, so its `counts` layer is misnamed relative to term.
  Pseudobulk/DE assuming integer counts cannot be done symmetrically across the two.
- **Composition shift.** Both are CTB (cytotrophoblast)-led, but from first
  trimester to term the CTB fraction falls while Hofbauer cells (placental
  macrophages) and stroma rise - a redistribution (deltas sum to 0) consistent with
  placental maturation. The `reviewer-literature` track rates this directional claim
  only *partial / low confidence* - an honest example of the literature reviewer
  declining to over-claim.
- **Namespaces.** The 5,000-HVG set meets term's 25,777 genes in 3,491 genes
  (18,480 using first trimester's full raw set); after normalizing a `Hofbaucer`
  spelling typo in term's labels, both atlases share a clean 7-compartment scheme.

## What is bundled

```
plan.json              the planner's plan: question, inputs, 5 steps, the claims each will assert
scripts/step-1..5.py   the executor's analysis code (one script per step)
results/*.csv          the executor's outputs (small tables behind the claims)
extra.json             the reviewer-numeric's task-specific check specs
.autoreview/
  claims.jsonl         every claim with its recorded numbers and seed checks
  verdicts.jsonl       the numeric and literature verdicts
  manifest.json        sha256 of inputs + output CSVs (the integrity guard)
  REPORT.md            the rendered two-track review
```

## Re-running the analysis half

To regenerate `results/` from scratch you need the matrices. Download both files
from the Zenodo record above, install the analysis deps (`uv add scanpy anndata`,
which pulls numpy/scipy/pandas/h5py), and run the step scripts. Note: the bundled
scripts and ledger keep the **absolute paths of the original run** as a frozen
provenance record - point them at your local copy of the `.h5ad` files to
re-execute. The generalized, fully self-contained runnable example is
`examples/toy/`.

# PVNS showcase (frozen)

This is the original prototype the framework grew out of: a review of a
single-cell RNA-seq annotation of pigmented villonodular synovitis / tenosynovial
giant cell tumour (PVNS / TGCT). It is kept here as a **real-world demonstration**
of the approach on a non-trivial analysis - read `REPORT.md` for the full output.

It is frozen on purpose and is **not runnable from this repo**: the scripts read a
large `.h5ad` (`results/annotated_data_2r_relabeled.h5ad`) and other result files
that live in the original analysis workspace and are not bundled here (raw data is
never committed). The generalized, runnable example is `examples/toy/`.

## What it demonstrates

`REPORT.md` reviews 18 claims, each split into a data fact (recomputed straight
from the `.h5ad`, never trusting the analyst's quoted number) and a biological
interpretation (checked against the literature with citations and caveats). The
caveats are the point - e.g. the review catches that NKG7/GNLY/KLRD1 are
pan-cytotoxic markers, not NK-specific, so a "T/NK mixed" cluster is more likely
cytotoxic T cells. That is exactly the kind of refinement `reviewer-literature` is
meant to produce.

## How it maps to the generalized framework

| prototype (here) | framework (`src/autoreview/`) |
|---|---|
| `scripts/claimlog.py` | `ledger.py` (de-domained, two-hash tracks) |
| `scripts/verify_data.py` (hardcoded h5ad metrics) | the executor recomputing numbers + `checks/numeric.py` invariants |
| `scripts/make_report.py` | `report.py` |
| `scripts/auto_verify.sh` (hardcoded `WS=` path) | `.claude/hooks/autoreview_stop.sh` (no hardcoded paths) |
| hand-written `scripts/log_lit_verdicts.py` | the `reviewer-literature` agent |
| `scripts/seed_claims.py` / `log_rescue_claims.py` | the `executor` logging claims as it makes them |

The prototype's "data" verdicts were a fixed set of h5ad-specific recompute
metrics. The framework replaces that with the executor recording the numbers it
computes and the `reviewer-numeric` agent authoring task-specific logic checks the
deterministic engine runs - so coverage is no longer limited to the metrics
someone hardcoded.

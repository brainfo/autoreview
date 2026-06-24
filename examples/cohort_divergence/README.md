# Cohort divergence — the deviation loop

A self-contained, synthetic walkthrough of the **conditional loop**: a question
whose plan rests on a false assumption, surfaced mid-run as a *contract
deviation*, re-planned, and answered honestly on a second loop. Deterministic
core only (no LLM, standard library only).

```bash
./run.sh
```

## The question

> *"Across `cohortA.csv` and `cohortB.csv`, does disease raise macrophage
> infiltration consistently? **Pool the cohorts** and compare disease vs
> control."*

The instruction to *pool* is the trap. The two files share the same columns
(`sample, group, Mac, Fb, T, Other`), so a planner naturally writes a step that
concatenates them and asserts `disease > control`. But the data is rigged:

- `cohortA.csv` holds **raw counts** — each row sums to ~300.
- `cohortB.csv` holds **fractions** — each row already sums to 1.

Pooling raw "counts" across the two is dominated by cohort A and is meaningless.

## What the loop does

1. **overseer** guards both inputs.
2. **executor (loop 1)** tries the planned pooled step. Computing per-row totals,
   it discovers the scale mismatch. Rather than fabricate a pooled number it
   (a) logs the one thing it *can* establish — `claim-cohort-scale` — and
   (b) records a **contract / forward deviation** (`dev-step3-scale`) against
   `claim-pooled-mac`, and skips that claim. *Capture, not enact:* it records the
   problem; it does not edit the plan.
3. **reviewer-numeric** runs the checks. (Note the `warn`-severity `scales-differ`
   check fails but does **not** turn the verdict into a violation — a warning is
   surfaced, not blocking.)
4. **overseer (deviation gate)** sees an open contract deviation → **NO-GO**, and
   that is the **loop signal**.
5. **planner re-plan** resolves the deviation (`accepted`, `enacted_in loop-2`)
   and replaces the pooled step with a within-cohort comparison (`plan_v2.json`).
6. **executor (loop 2)** computes per-sample Mac fractions *within* each cohort
   and compares disease vs control — logging `claim-mac-cohortA`,
   `claim-mac-cohortB`, and `claim-mac-consistency` at `loop: 2`.
7. **reviewer-numeric** runs the checks (all consistent).
8. **overseer** gate is now clear → **GO**; inputs verified intact.

## The honest answer

The deviation forces the question open: disease **raises** the macrophage
fraction in cohort A (Δ = +0.31) but **lowers** it in cohort B (Δ = −0.12). The
`claim-mac-consistency` check multiplies the two deltas and asserts the product is
negative — a machine-verified statement that *the cohorts move in opposite
directions*. The originally requested pooled answer would have masked this.

## Why this matters for the design

`claim-cohort-scale` and the loop-2 claims all pass their numeric checks. **The
numeric track alone never flags the design flaw** — a pooled number can be
perfectly self-consistent and still be the wrong thing to compute. The deviation
record is what carries "this plan assumption is invalid," and the gate + loop are
what act on it. The ledger (`deviations.jsonl` + `verdicts.jsonl`) is the memory
between loops; there is no separate "lessons learned" file.

## Files

- `data/cohortA.csv`, `data/cohortB.csv` — the rigged inputs.
- `plan_v1.json` — the naive pooled plan; `plan_v2.json` — the re-planned,
  stratified plan, with an `amends` note pointing back at the deviation.
- `analyze.py` — the executor stand-in (`pass 1` records the deviation; `pass 2`
  does the within-cohort comparison).
- `run.sh` — drives the full two-loop pipeline against the real `autoreview` CLI.

## See sign-off blocked

Comment out the `deviation resolve` line in `run.sh` and re-run: the second
deviation gate stays **NO-GO** and `autoreview deviation list --open` exits
non-zero — an unresolved contract deviation blocks sign-off, exactly as intended.

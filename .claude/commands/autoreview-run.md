---
description: Run the full plan / execute / review pipeline on an analysis question, with the overseer gating each checkpoint.
argument-hint: "<analysis question> [input files...]"
---

Drive the autoreview pipeline for: $ARGUMENTS

You are the conductor. Run the stages below in order, launching each agent with
the Agent tool. Between stages, launch the `overseer` and proceed only on GO; on
NO-GO, stop and report exactly which agent left which artifact missing or
inconsistent. The deterministic state lives in the ledger and the manifest, not
in any agent's context - pass artifact paths between stages, not prose.

Set the ledger directory once for the run (default `.autoreview`); export
`AUTOREVIEW_DIR` so every `autoreview` call shares it.

1. overseer (pre-flight): confirm the named input files exist and are readable.
   GO/NO-GO.

2. planner: design the plan for the question and write `plan.json`.

3. overseer (post-plan): `plan.json` parses; its inputs exist; register all
   inputs in the manifest. GO/NO-GO.

4. executor: implement and run each plan step; log the promised claims with their
   numbers, checks, and input/output hashes.

5. overseer (post-exec): each step's outputs exist, every promised claim id is in
   the ledger, no input mutated during the run. GO/NO-GO.

6. reviewer-numeric: author the task-specific invariants and run `autoreview
   check run`. Then overseer: `autoreview pending --kind numeric` is empty;
   surface any `violation` verdicts.

7. reviewer-literature: judge each interpretation and log literature verdicts with
   citations. Then overseer: `autoreview pending --kind literature` is empty;
   spot-check citation URLs.

8. Regenerate the report (`autoreview report`) and give the user a concise
   summary: the claims, the numeric verdicts (highlighting any violation), the
   literature verdicts with confidence, and a pointer to `REPORT.md`. Do not
   declare the analysis sound if any checkpoint was NO-GO or any check was a
   violation - report those plainly instead.

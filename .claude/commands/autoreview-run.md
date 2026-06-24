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

## One pass

Run these in order, passing the current loop number `N` (start at 1):

1. overseer (pre-flight, loop 1 only): confirm the named input files exist and are
   readable. GO/NO-GO.

2. planner: on loop 1, design the plan for the question and write `plan.json` with
   `"loop": 1`. On loop N>1, run the planner in **re-plan mode** — it reads the
   prior loop's open deviations and any violation / refuted / uncertain verdicts
   and writes the next `plan.json` with `"loop": N` and an `amends` note.

3. overseer (post-plan): `plan.json` parses; its inputs exist; register all
   inputs in the manifest. GO/NO-GO.

4. executor: implement and run each plan step; log the promised claims (with
   `--loop N`) and their numbers, checks, and input/output hashes. It records a
   **deviation** for any plan assumption it finds broken, and skips only the
   claims a deviation names.

5. overseer (post-exec + deviation gate): each step's outputs exist; every
   promised claim id is in the ledger *or* named by a deviation; no input mutated;
   `autoreview deviation list --open` is empty of untriaged contract deviations.
   GO/NO-GO.

6. reviewer-numeric: author the task-specific invariants and run `autoreview
   check run`. Then overseer: `autoreview pending --kind numeric` is empty;
   surface any `violation` verdicts.

7. reviewer-literature: judge each interpretation and log literature verdicts with
   citations. Then overseer: `autoreview pending --kind literature` is empty;
   spot-check citation URLs.

## The loop (conditional — only if a pass surfaces a reason)

After a pass, gather the **loop signal**:

- any numeric `violation` verdict,
- any literature `refuted` or `uncertain` verdict,
- any contract deviation that is open or accepted-but-not-yet-enacted
  (`autoreview deviation list` — `blocking` or `loop_pending` true).

If the signal is **empty → stop.** The initial plan was sufficient; do not loop
for its own sake. Otherwise increment `N` and run another pass from step 2 (the
planner re-plans to address exactly those signals). **Cap at 3 loops**; if signal
remains after the cap, stop and report what is still unresolved rather than
looping further. The ledger — `deviations.jsonl` and `verdicts.jsonl` — is the
memory carried between loops; there is no separate notes file.

## Sign-off

Regenerate the report (`autoreview report`) and give the user a concise summary:
the claims (noting which loop produced each), the numeric verdicts (highlighting
any violation), the literature verdicts with confidence, any deviations and how
each was resolved, and a pointer to `REPORT.md`. State how many loops ran and why.
Do not declare the analysis sound if any checkpoint was NO-GO, any check was a
violation, or any contract deviation is still open - report those plainly instead.

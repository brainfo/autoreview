#!/usr/bin/env bash
# End-to-end walkthrough of the *conditional loop*, driving only the deterministic
# core (no LLM). A question is asked whose plan rests on a false assumption; the
# executor surfaces a contract deviation instead of fabricating a number, the gate
# refuses sign-off, the plan is re-planned, and a second loop produces the honest
# answer. It mirrors what the agents do:
#   overseer  -> guard the inputs
#   executor (loop 1) -> attempt the planned pooled step; record what it can, and
#                        record a contract deviation against the claim it cannot
#   reviewer-numeric  -> run the logic checks
#   overseer  -> deviation gate: an open contract deviation is a NO-GO -> loop
#   planner   -> re-plan: resolve the deviation, enact in loop 2
#   executor (loop 2) -> the honest within-cohort comparison
#   overseer  -> deviation gate now clear -> GO ; verify inputs intact
#   report
set -uo pipefail
cd "$(dirname "$0")"

PY="${PY:-$(command -v python || command -v python3)}"
LEDGER="./ledger"
rm -rf "$LEDGER"
export AUTOREVIEW_DIR="$LEDGER"

echo "== overseer: guard inputs =="
autoreview guard register data/cohortA.csv data/cohortB.csv --role input

echo
echo "== LOOP 1: executor — attempt the pooled comparison the plan asked for =="
"$PY" analyze.py 1 claims     | autoreview claim add --loop 1 -
"$PY" analyze.py 1 deviations | autoreview deviation add --loop 1 -

echo
echo "== reviewer-numeric =="
autoreview check run || true

echo
echo "== overseer: deviation gate =="
if autoreview deviation list --open >/dev/null; then
  echo "GO: no open contract deviations"
else
  echo "NO-GO: open contract deviation(s) -> the pooled comparison is invalid; re-planning."
fi

echo
echo "== planner re-plan: accept the deviation, enact the fix in loop 2 =="
autoreview deviation resolve dev-step3-scale --decision accepted --enacted-in loop-2 \
  --by planner --notes "cohorts on different scales; replace the pooled step with a within-cohort comparison"

echo
echo "== LOOP 2: executor — the honest within-cohort comparison =="
"$PY" analyze.py 2 claims | autoreview claim add --loop 2 -

echo
echo "== reviewer-numeric =="
autoreview check run || true

echo
echo "== overseer: deviation gate (expect GO now) =="
if autoreview deviation list --open >/dev/null; then
  echo "GO: no open contract deviations"
else
  echo "NO-GO: still blocked"
fi

echo
echo "== overseer: verify inputs intact =="
autoreview guard verify

echo
echo "== report =="
autoreview report

echo
echo "== status =="
autoreview status

echo
echo "Conclusion: the disease effect on macrophages is NOT consistent across cohorts."
echo "The deviation loop turned an un-answerable pooled question into an honest"
echo "stratified one. See $LEDGER/REPORT.md and $LEDGER/deviations.jsonl"

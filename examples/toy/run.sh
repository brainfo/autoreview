#!/usr/bin/env bash
# End-to-end walkthrough of the pipeline on synthetic data, driving only the
# deterministic core (no LLM). It mirrors what the agents do:
#   overseer  -> guard the input file (record its sha256)
#   executor  -> run analysis code, emit claims with numbers + checks
#   reviewer-numeric -> run the logic checks, log numeric verdicts
#   overseer  -> verify the input was not mutated during the run
#   (reviewer-literature would add literature verdicts here)
#   report    -> render REPORT.md
#
# The literature track is left pending on purpose: that half needs an agent.
set -euo pipefail
cd "$(dirname "$0")"

LEDGER="./ledger"
rm -rf "$LEDGER"
export AUTOREVIEW_DIR="$LEDGER"

echo "== overseer: guard input =="
autoreview guard register data/counts.csv --role input

echo
echo "== executor: run analysis, log claims =="
python analyze.py | autoreview claim add -

echo
echo "== reviewer-numeric: run logic checks =="
autoreview check run

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
echo "(literature track is pending - that half needs the reviewer-literature agent)"
echo "See $LEDGER/REPORT.md"

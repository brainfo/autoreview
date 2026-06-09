#!/usr/bin/env bash
# Stop hook: auto-verify the DATA half of any pending analysis claims (deterministic and
# cheap) and surface claims still needing LITERATURE verification. No-op when nothing is
# pending, so it is near-free on unrelated turns.
#
# Literature checks are deliberately NOT auto-spawned here: they are networked and cost
# tokens, and a shell hook cannot launch Claude sub-agents. Instead the pending list is
# surfaced so Claude/you can launch the literature verifier agents on demand.
set -uo pipefail
WS="/mnt/run/jh/projects/pnvs/workspace"
cd "$WS" || exit 0

# Avoid re-entrancy if a previous stop-hook pass already triggered a continuation.
input="$(cat 2>/dev/null || true)"
case "$input" in *'"stop_hook_active":true'*) exit 0 ;; esac

pending="$(uv run python claims/claimlog.py pending 2>/dev/null || echo '[]')"
[ "$pending" = "[]" ] && exit 0

# Deterministic data verification + refresh the report (both safe to run automatically).
uv run python claims/verify_data.py >/tmp/claims_verify.log 2>&1 || true
uv run python claims/make_report.py >/dev/null 2>&1 || true

lit="$(uv run python - <<'PY' 2>/dev/null
import sys; sys.path.insert(0, "claims")
from claimlog import pending
print(",".join(c["id"] for c in pending("literature") if c.get("bio_assertion")))
PY
)"

if [ -n "$lit" ]; then
  printf '{"systemMessage": "Claim ledger: data facts auto-verified (see claims/REPORT.md). Pending LITERATURE verification: %s . Launch the literature verifier agents to complete."}\n' "$lit"
fi
exit 0

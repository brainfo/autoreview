from autoreview.ledger import Ledger
from autoreview import report as report_mod


def test_log_deviation_idempotent(tmp_path):
    led = Ledger(tmp_path)
    a = led.log_deviation("d1", "cohortB is fractions not counts", affects_step="step-3")
    b = led.log_deviation("d1", "cohortB is fractions not counts", affects_step="step-3")
    assert a["hash"] == b["hash"]
    # one deviation record on disk (idempotent), regardless of resolutions
    assert sum(1 for r in led.load_deviations() if r.get("record") == "deviation") == 1


def test_contract_deviation_blocks_until_resolved(tmp_path):
    led = Ledger(tmp_path)
    led.log_deviation("d1", "pooling invalid", affects_step="step-3",
                      kind="contract", scope="forward")
    assert {d["id"] for d in led.open_deviations()} == {"d1"}
    assert {d["id"] for d in led.loop_pending_deviations()} == {"d1"}

    led.resolve_deviation("d1", "accepted", enacted_in="loop-2", by="planner")
    # triaged -> no longer blocks sign-off, and enacted -> no longer a loop signal
    assert led.open_deviations() == []
    assert led.loop_pending_deviations() == []


def test_method_deviation_never_blocks(tmp_path):
    led = Ledger(tmp_path)
    led.log_deviation("m1", "column named annotate_general not annotation",
                      affects_step="step-3", kind="method", scope="in-step")
    assert led.open_deviations() == []
    assert led.loop_pending_deviations() == []


def test_accepted_but_not_enacted_still_loops(tmp_path):
    led = Ledger(tmp_path)
    led.log_deviation("d1", "needs a new step", affects_step="step-4", kind="contract")
    led.resolve_deviation("d1", "accepted")  # no enacted_in yet
    assert led.open_deviations() == []          # triaged, not blocking
    assert {d["id"] for d in led.loop_pending_deviations()} == {"d1"}  # but loop still owed


def test_deferred_and_rejected_do_not_loop(tmp_path):
    led = Ledger(tmp_path)
    led.log_deviation("d1", "out of scope", affects_step="step-9", kind="contract")
    led.log_deviation("d2", "not a real problem", affects_step="step-8", kind="contract")
    led.resolve_deviation("d1", "deferred", notes="next loop")
    led.resolve_deviation("d2", "rejected", notes="false alarm")
    assert led.open_deviations() == []
    assert led.loop_pending_deviations() == []


def test_latest_resolution_wins(tmp_path):
    led = Ledger(tmp_path)
    led.log_deviation("d1", "x", affects_step="step-1", kind="contract")
    led.resolve_deviation("d1", "deferred")
    led.resolve_deviation("d1", "accepted", enacted_in="loop-2")
    (d, r), = led.deviation_rows()
    assert r["decision"] == "accepted" and r["enacted_in"] == "loop-2"


def test_claim_carries_loop_stamp(tmp_path):
    led = Ledger(tmp_path)
    c1 = led.log_claim("c1", "v1 claim", numbers={"n": 1}, loop=1)
    assert c1["loop"] == 1
    # changed numbers in loop 2 -> new record stamped loop 2, numeric re-opens
    c2 = led.log_claim("c1", "v1 claim", numbers={"n": 2}, loop=2)
    assert c2["loop"] == 2 and c2["nhash"] != c1["nhash"]


def test_report_renders_deviations(tmp_path):
    led = Ledger(tmp_path)
    led.log_claim("c1", "a claim", numbers={"n": 1})
    led.log_deviation("d1", "cohortB is fractions not counts", affects_step="step-3",
                      kind="contract", scope="forward",
                      proposed_action="stratify by cohort")
    led.resolve_deviation("d1", "accepted", enacted_in="loop-2", by="planner",
                          notes="re-planned step-3")
    n, path = report_mod.render(tmp_path)
    text = path.read_text()
    assert "Deviations & amendments" in text
    assert "d1" in text and "stratify by cohort" in text
    assert "enacted in loop-2" in text

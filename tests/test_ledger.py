from autoreview.ledger import Ledger


def test_log_claim_idempotent(tmp_path):
    led = Ledger(tmp_path)
    a = led.log_claim("c1", "Macrophages enriched", interpretation="bio")
    b = led.log_claim("c1", "Macrophages enriched", interpretation="bio")
    assert a["hash"] == b["hash"]
    assert len(led.load_claims()) == 1


def test_hash_decoupling(tmp_path):
    led = Ledger(tmp_path)
    c = led.log_claim("c1", "claim text", interpretation="bio",
                      numbers={"n": 1}, checks=[{"kind": "bounds"}])
    # editing numbers changes nhash but not the literature hash
    c2 = led.log_claim("c1", "claim text", interpretation="bio",
                       numbers={"n": 2}, checks=[{"kind": "bounds"}])
    assert c2["hash"] == c["hash"]
    assert c2["nhash"] != c["nhash"]


def test_pending_tracks_two_independent_tracks(tmp_path):
    led = Ledger(tmp_path)
    c = led.log_claim("c1", "claim", interpretation="bio",
                      numbers={"n": 1}, checks=[{"id": "k", "kind": "bounds",
                                                 "values": ["n"], "lo": 0, "hi": 10}])
    assert {x["id"] for x in led.pending("numeric")} == {"c1"}
    assert {x["id"] for x in led.pending("literature")} == {"c1"}

    led.log_verdict("c1", c["nhash"], "numeric", "consistent")
    assert led.pending("numeric") == []
    assert {x["id"] for x in led.pending("literature")} == {"c1"}

    led.log_verdict("c1", c["hash"], "literature", "supported", confidence="high")
    assert led.pending() == []


def test_editing_numbers_reopens_numeric_only(tmp_path):
    led = Ledger(tmp_path)
    c = led.log_claim("c1", "claim", interpretation="bio", numbers={"n": 1})
    led.log_verdict("c1", c["nhash"], "numeric", "consistent")
    led.log_verdict("c1", c["hash"], "literature", "supported")
    assert led.pending() == []
    # change the number -> numeric re-opens, literature stays settled
    led.log_claim("c1", "claim", interpretation="bio", numbers={"n": 2})
    assert {x["id"] for x in led.pending("numeric")} == {"c1"}
    assert led.pending("literature") == []


def test_cross_analysis_numbers_lookup(tmp_path):
    led = Ledger(tmp_path)
    led.log_claim("a", "n cells in A", numbers={"n_cells": 1925})
    assert led.claim_numbers("a") == {"n_cells": 1925}
    assert led.claim_numbers("missing") is None

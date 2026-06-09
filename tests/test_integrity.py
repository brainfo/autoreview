from autoreview.checks.integrity import sha256_file, register, verify, Manifest


def test_sha256_missing_file(tmp_path):
    assert sha256_file(tmp_path / "nope.txt") is None


def test_verify_detects_change_and_missing(tmp_path):
    f = tmp_path / "input.csv"
    f.write_text("a,b\n1,2\n")
    manifest = register([f], role="input")
    ok, results = verify(manifest)
    assert ok and results[0]["status"] == "ok"

    f.write_text("a,b\n9,9\n")  # mutate the input
    ok, results = verify(manifest)
    assert not ok and results[0]["status"] == "changed"

    f.unlink()
    ok, results = verify(manifest)
    assert not ok and results[0]["status"] == "missing"


def test_output_appears(tmp_path):
    out = tmp_path / "result.csv"
    manifest = register([out], role="output")  # not produced yet
    ok, results = verify(manifest)
    assert not ok and results[0]["status"] == "missing"

    out.write_text("done\n")
    ok, results = verify(manifest)
    assert ok and results[0]["status"] == "appeared"


def test_manifest_roundtrip_and_dedup(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("hi")
    man = Manifest(tmp_path / "manifest.json")
    man.add([f], role="input")
    man.add([f], role="input")  # idempotent
    assert len(man.load()) == 1
    ok, _ = man.verify()
    assert ok

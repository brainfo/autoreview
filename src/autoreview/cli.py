"""Command-line interface to the ledger, the numeric check engine and the
integrity guard. Every agent role drives the pipeline through this one entry
point so the deterministic state lives in files, not in any agent's context.

    autoreview claim add  <file|->         log one or more claims (JSON)
    autoreview verdict add <file|->        log one or more verdicts (JSON)
    autoreview check run  [--specs f]      run numeric/logic checks, log verdicts
    autoreview deviation add <file|->      record plan deviation(s) (executor)
    autoreview deviation resolve <id>      triage a deviation (gate only)
    autoreview deviation list [--open]     list deviations; non-zero if any block
    autoreview guard register <files...>   record files + sha256 in the manifest
    autoreview guard verify                re-hash the manifest, report drift
    autoreview report                      (re)generate REPORT.md
    autoreview status                      one line per claim, both tracks
    autoreview pending [--kind ...]        claims still needing review
"""
import argparse
import json
import os
import sys
from pathlib import Path

from .ledger import Ledger
from .checks import run_checks, Manifest
from . import report as report_mod


def _default_dir():
    return os.environ.get("AUTOREVIEW_DIR", ".autoreview")


def _load_json(arg):
    text = sys.stdin.read() if arg == "-" else Path(arg).read_text()
    data = json.loads(text)
    return data if isinstance(data, list) else [data]


def _led(args):
    return Ledger(args.dir)


# -- commands -----------------------------------------------------------
def cmd_claim_add(args):
    led = _led(args)
    n = 0
    for c in _load_json(args.source):
        rec = led.log_claim(
            id=c["id"], claim=c["claim"], interpretation=c.get("interpretation"),
            numbers=c.get("numbers"), checks=c.get("checks"),
            ctype=c.get("type", "data+interpretation"), source=c.get("source"),
            inputs=c.get("inputs"), outputs=c.get("outputs"),
            search_terms=c.get("search_terms"), loop=c.get("loop", args.loop))
        print(f"claim {rec['id']} [{rec['hash']}/{rec['nhash']}]")
        n += 1
    print(f"logged {n} claim(s)")
    return 0


def cmd_verdict_add(args):
    led = _led(args)
    n = 0
    for v in _load_json(args.source):
        rec = led.log_verdict(
            id=v["id"], hash=v["hash"], kind=v["kind"], verdict=v["verdict"],
            confidence=v.get("confidence"), citations=v.get("citations"),
            checks=v.get("checks"), notes=v.get("notes"))
        print(f"verdict {rec['id']} {rec['kind']} -> {rec['verdict']}")
        n += 1
    print(f"logged {n} verdict(s)")
    return 0


def cmd_check_run(args):
    led = _led(args)
    extra = {}
    if args.specs:
        for s in _load_json(args.specs):
            extra.setdefault(s.get("claim"), []).append(s)

    violations = 0
    ran = 0
    for c in led.load_claims():
        specs = list(c.get("checks") or []) + list(extra.get(c["id"], []))
        if not specs:
            continue
        if not args.force and (c["id"], c.get("nhash"), "numeric") in led.verdict_index():
            continue
        ok, results = run_checks(specs, c.get("numbers"), led.claim_numbers)
        verdict = "consistent" if ok else "violation"
        ran += 1
        if not ok:
            violations += 1
        print(f"\n[{c['id']}] -> {verdict}")
        for r in results:
            flag = "ok " if r["passed"] else "FAIL"
            print(f"  [{flag}] ({r['severity']}) {r['id']} [{r['kind']}]: {r['detail']}")
        if not args.dry_run:
            led.log_verdict(c["id"], c["nhash"], "numeric", verdict, checks=results)
    print(f"\nran numeric review on {ran} claim(s); {violations} with violations")
    return 1 if violations else 0


def cmd_deviation_add(args):
    led = _led(args)
    n = 0
    for d in _load_json(args.source):
        rec = led.log_deviation(
            id=d["id"], observed=d["observed"], affects_step=d.get("affects_step"),
            affects_claims=d.get("affects_claims"), kind=d.get("kind", "contract"),
            scope=d.get("scope", "forward"), proposed_action=d.get("proposed_action"),
            loop=d.get("loop", args.loop))
        print(f"deviation {rec['id']} [{rec['hash']}] {rec['kind']}/{rec['scope']} "
              f"-> {rec.get('affects_step')}")
        n += 1
    print(f"logged {n} deviation(s)")
    return 0


def cmd_deviation_resolve(args):
    led = _led(args)
    rec = led.resolve_deviation(args.id, args.decision, enacted_in=args.enacted_in,
                                by=args.by, notes=args.notes)
    print(f"deviation {rec['deviation_id']} -> {rec['decision']}"
          + (f" (enacted in {rec['enacted_in']})" if rec.get("enacted_in") else ""))
    return 0


def cmd_deviation_list(args):
    led = _led(args)
    blocking = {d["id"] for d in led.open_deviations()}
    looping = {d["id"] for d in led.loop_pending_deviations()}
    rows = []
    for d, r in led.deviation_rows():
        if args.open and d["id"] not in blocking:
            continue
        rows.append({
            "id": d["id"], "loop": d.get("loop"), "kind": d.get("kind"),
            "scope": d.get("scope"), "affects_step": d.get("affects_step"),
            "decision": (r or {}).get("decision"),
            "enacted_in": (r or {}).get("enacted_in"),
            "blocking": d["id"] in blocking, "loop_pending": d["id"] in looping,
        })
    print(json.dumps(rows, indent=2))
    # non-zero when something still blocks sign-off, so the overseer can gate on it
    return 1 if blocking else 0


def cmd_guard_register(args):
    man = Manifest(args.manifest or Path(args.dir) / "manifest.json")
    entries = man.add(args.files, role=args.role)
    for e in entries[-len(args.files):]:
        state = "present" if e["exists"] else "MISSING"
        print(f"{e['role']:6s} {state:8s} {e['path']} {e['sha256'] or ''}")
    print(f"manifest: {man.path}")
    return 0


def cmd_guard_verify(args):
    man = Manifest(args.manifest or Path(args.dir) / "manifest.json")
    ok, results = man.verify()
    for r in results:
        print(f"  [{'ok' if r['status'] == 'ok' else r['status'].upper():8s}] "
              f"{r['role']:6s} {r['path']}")
    print(f"\nintegrity: {'OK' if ok else 'FAILED'} ({len(results)} file(s))")
    return 0 if ok else 1


def cmd_report(args):
    n, path = report_mod.render(args.dir)
    print(f"wrote {path} ({n} claims)")
    return 0


def cmd_status(args):
    led = _led(args)
    for c, nv, lv in led.status_rows():
        num = "num:ok" if nv and nv["verdict"] == "consistent" else (
            "num:!!" if nv else ("num:." if (c.get("numbers") or c.get("checks")) else "num:-"))
        lit = "lit:ok" if lv else ("lit:." if c.get("interpretation") else "lit:-")
        print(f"{c['id']:32s} [{c['hash']}/{c.get('nhash')}] {num} {lit}  {c['claim'][:62]}")
    return 0


def cmd_pending(args):
    led = _led(args)
    pend = led.pending(args.kind)
    if args.ids:
        print(",".join(c["id"] for c in pend))
    else:
        print(json.dumps([{"id": c["id"], "kind_needed": args.kind or "either"}
                          for c in pend], indent=2))
    return 0


# -- parser -------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(prog="autoreview", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dir", default=_default_dir(),
                   help="ledger directory (default: $AUTOREVIEW_DIR or .autoreview)")
    sub = p.add_subparsers(dest="cmd", required=True)

    claim = sub.add_parser("claim", help="manage claims").add_subparsers(dest="x", required=True)
    ca = claim.add_parser("add", help="log claim(s) from a JSON file or '-'")
    ca.add_argument("source")
    ca.add_argument("--loop", type=int, default=1,
                    help="loop/version stamp for claims lacking their own (default 1)")
    ca.set_defaults(func=cmd_claim_add)

    verdict = sub.add_parser("verdict", help="manage verdicts").add_subparsers(dest="x", required=True)
    va = verdict.add_parser("add", help="log verdict(s) from a JSON file or '-'")
    va.add_argument("source")
    va.set_defaults(func=cmd_verdict_add)

    check = sub.add_parser("check", help="run numeric/logic checks").add_subparsers(dest="x", required=True)
    cr = check.add_parser("run", help="evaluate claim checks and log numeric verdicts")
    cr.add_argument("--specs", help="extra check specs (JSON list) to run this pass")
    cr.add_argument("--force", action="store_true", help="re-run even if a verdict exists")
    cr.add_argument("--dry-run", action="store_true", help="evaluate but do not log verdicts")
    cr.set_defaults(func=cmd_check_run)

    dev = sub.add_parser("deviation", help="record/resolve plan deviations").add_subparsers(dest="x", required=True)
    da = dev.add_parser("add", help="record deviation(s) from a JSON file or '-'")
    da.add_argument("source")
    da.add_argument("--loop", type=int, default=1,
                    help="loop stamp for deviations lacking their own (default 1)")
    da.set_defaults(func=cmd_deviation_add)
    dre = dev.add_parser("resolve", help="resolve a deviation (gate only)")
    dre.add_argument("id")
    dre.add_argument("--decision", required=True,
                     choices=["accepted", "rejected", "deferred"])
    dre.add_argument("--enacted-in", dest="enacted_in",
                     help="where the fix lands, e.g. loop-2")
    dre.add_argument("--by", help="who resolved it, e.g. planner")
    dre.add_argument("--notes")
    dre.set_defaults(func=cmd_deviation_resolve)
    dl = dev.add_parser("list", help="list deviations (JSON); non-zero if any block")
    dl.add_argument("--open", action="store_true",
                    help="only deviations that still block sign-off")
    dl.set_defaults(func=cmd_deviation_list)

    guard = sub.add_parser("guard", help="file-integrity guard").add_subparsers(dest="x", required=True)
    gr = guard.add_parser("register", help="record files + sha256 in the manifest")
    gr.add_argument("files", nargs="+")
    gr.add_argument("--role", choices=["input", "output"], default="input")
    gr.add_argument("--manifest")
    gr.set_defaults(func=cmd_guard_register)
    gv = guard.add_parser("verify", help="re-hash the manifest and report drift")
    gv.add_argument("--manifest")
    gv.set_defaults(func=cmd_guard_verify)

    rp = sub.add_parser("report", help="(re)generate REPORT.md")
    rp.set_defaults(func=cmd_report)

    st = sub.add_parser("status", help="one line per claim")
    st.set_defaults(func=cmd_status)

    pe = sub.add_parser("pending", help="claims still needing review")
    pe.add_argument("--kind", choices=["numeric", "literature"])
    pe.add_argument("--ids", action="store_true", help="print a comma-separated id list")
    pe.set_defaults(func=cmd_pending)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

"""Owned temporary directories only. Does not find/access any Steam location."""
from pathlib import Path
from datetime import datetime
import ctypes as C
import hashlib
import json
import os
import subprocess
import sys
import time
import threading
import b_warm_staging as stage

P = Path(__file__).resolve().parent
PRIVATE = P.parents[2] / "mod_research"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(value, text):
    if not value:
        raise AssertionError(text)


def setup(run, name):
    root = run / name
    root.mkdir()
    target = root / "target"
    target.mkdir()
    records = root / "records"
    records.mkdir()
    source = root / "source.s14"
    source.write_bytes(b"owned-new-save" * 19)
    (target / stage.NAME).write_bytes(b"owned-existing-save" * 17)
    evidence = root / "owned-retirement-reference.json"
    evidence.write_text('{"diagnostic_reference":true,"native_retirement_proven":false}')
    return root, target, records, source, evidence


def authorize(parts, proposed, number):
    root, target, records, source, evidence = parts
    permit = root / (str(number) + ".authorization.json")
    raw = {"schema": "san14.local-file-overwrite-authorization.v1", "nonce": f"{number:032x}",
           "plan_sha256": stage.digest(stage.canonical(proposed)), "expires_unix": int(time.time()) + 300,
           "retirement_reference": str(evidence), "retirement_sha256": sha(evidence)}
    permit.write_bytes(stage.canonical(raw))
    return permit, sha(permit)


def planned(parts):
    _, target, _, source, _ = parts
    return stage.plan(source, target, sha(source), source.stat().st_size)


def rejected(action):
    try:
        outcome = action()
    except (stage.Refused, OSError):
        return
    check(outcome.get("result") in ("REFUSED", "UNKNOWN_NO_RETRY"), "Expected conservative refusal")


def main():
    run = PRIVATE / "b_warm_staging_runs" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    run.mkdir(parents=True)
    sources = {name: sha(P / name) for name in ("b_warm_staging.py", "b_warm_staging_test.py")}
    rows = []

    def case(name, test):
        try:
            test()
            rows.append({"case": name, "passed": True})
        except BaseException as error:
            rows.append({"case": name, "passed": False, "error": repr(error)})

    def two_generations():
        parts = setup(run, "two-generations")
        root, target, records, source, _ = parts
        original = (target / stage.NAME).read_bytes()
        before = sorted(str(p.relative_to(root)) for p in root.rglob("*"))
        q = planned(parts)
        check(sorted(str(p.relative_to(root)) for p in root.rglob("*")) == before, "Plan wrote files")
        permit, ph = authorize(parts, q, 1)
        one = stage.apply(q, permit, ph, records)
        check(one["result"] == "STAGED" and not one["engine_exclusion_proven"] and not one["load_permitted"], str(one))
        check(Path(one["backup"]).read_bytes() == original and (target / stage.NAME).read_bytes() == source.read_bytes(), "First exact copy/backup")
        rejected(lambda: stage.apply(q, permit, ph, records))
        first = source.read_bytes()
        source.write_bytes(b"owned-second-legal-shape-not-game-proof" * 13)
        q = planned(parts)
        permit, ph = authorize(parts, q, 2)
        two = stage.apply(q, permit, ph, records)
        check(two["result"] == "STAGED" and Path(two["backup"]).read_bytes() == first and (target / stage.NAME).read_bytes() == source.read_bytes(), str(two))
        (root / "receipts.json").write_text(json.dumps([one, two], indent=2))

    def stale_and_hash():
        parts = setup(run, "stale-hash")
        _, target, records, source, _ = parts
        rejected(lambda: stage.plan(source, target, "0" * 64, source.stat().st_size))
        rejected(lambda: stage.plan(source, target, sha(source), True))
        rejected(lambda: stage.plan(source, target, sha(source), float(source.stat().st_size)))
        rejected(lambda: stage.plan(source, target, sha(source), 16 * 1024 * 1024 + 1))
        q = planned(parts)
        permit, ph = authorize(parts, q, 3)
        original = (target / stage.NAME).read_bytes()
        rejected(lambda: stage.apply(q, permit, "0" * 64, records))
        check((target / stage.NAME).read_bytes() == original, "Wrong auth mutated target")
        (target / stage.NAME).write_bytes(b"concurrent-authoritative-change")
        changed = (target / stage.NAME).read_bytes()
        rejected(lambda: stage.apply(q, permit, ph, records))
        check((target / stage.NAME).read_bytes() == changed, "Stale plan overwritten")

    def lock_contention():
        parts = setup(run, "lock-contention")
        _, target, records, _, _ = parts
        q = planned(parts)
        permit, ph = authorize(parts, q, 4)
        lock = target / ".b-warm-staging.lock"
        lock.write_bytes(b"owned-test-lock")
        original = (target / stage.NAME).read_bytes()
        with stage.Handle(lock, share=0):
            rejected(lambda: stage.apply(q, permit, ph, records))
        check((target / stage.NAME).read_bytes() == original, "Lock contention changed target")

    def reader_conflict():
        parts = setup(run, "reader-conflict")
        _, target, records, _, _ = parts
        q = planned(parts)
        permit, ph = authorize(parts, q, 5)
        original = (target / stage.NAME).read_bytes()
        # A real live read handle withholding DELETE sharing must block replacement.
        with stage.Handle(target / stage.NAME, share=1):
            result = stage.apply(q, permit, ph, records)
        check(result["result"] == "UNKNOWN_NO_RETRY" and not result["replaced"], str(result))
        check((target / stage.NAME).read_bytes() == original, "Reader conflict changed target")
        rejected(lambda: stage.apply(q, permit, ph, records))

    def writer_conflict():
        parts = setup(run, "writer-conflict")
        _, target, records, _, _ = parts
        q = planned(parts)
        permit, ph = authorize(parts, q, 6)
        original = (target / stage.NAME).read_bytes()
        with (target / stage.NAME).open("r+b"):
            result = stage.apply(q, permit, ph, records)
        check(result["result"] == "REFUSED" and not result["replaced"], str(result))
        check((target / stage.NAME).read_bytes() == original, "Writer conflict changed target")

    def concurrent_rename():
        parts = setup(run, "concurrent-rename")
        root, target, records, _, _ = parts
        q = planned(parts)
        permit, ph = authorize(parts, q, 7)
        original = (target / stage.NAME).read_bytes()
        outsider = root / "outside-writer-owned.s14"
        outsider.write_bytes(b"concurrent-other-writer-bytes")
        external = outsider.read_bytes()
        real = stage.kernel()

        class Boundary:
            def __getattr__(self, name):
                return getattr(real, name)

            def ReplaceFileW(self, *args):
                failures = []
                def swap():
                    try:
                        if not real.ReplaceFileW(str(target / stage.NAME), str(outsider), str(root / "race-displaced.s14"), 0, None, None):
                            raise C.WinError(C.get_last_error())
                    except BaseException as error:
                        failures.append(error)
                worker = threading.Thread(target=swap)
                worker.start()
                worker.join()
                check(not failures, "Actual concurrent name replacement failed: " + repr(failures))
                return real.ReplaceFileW(*args)

        stage.K = Boundary()
        try:
            result = stage.apply(q, permit, ph, records)
        finally:
            stage.K = real
        check(result["result"] == "UNKNOWN_NO_RETRY" and result["replaced"] and not result["load_permitted"], str(result))
        check(Path(result["backup"]).read_bytes() == external and
              (records / (f"{7:032x}" + ".verified-old.s14")).read_bytes() == original,
              "Both displaced outsider and original planned bytes retained")
        rejected(lambda: stage.apply(q, permit, ph, records))

    def paths():
        parts = setup(run, "paths")
        root, target, records, source, _ = parts
        link = root / "junction"
        proc = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True)
        check(proc.returncode == 0, "Owned junction creation failed")
        rejected(lambda: stage.plan(source, link, sha(source), source.stat().st_size))
        os.link(source, root / "hardlink.s14")
        rejected(lambda: planned(parts))
        rejected(lambda: stage.clean_path(str(source) + ":alternate"))
        rejected(lambda: stage.clean_path(root / ".." / "outside"))
        # Leave junction and all files for review; no recursive delete is used.

    for name, test in (("two-generations", two_generations), ("stale-and-hash", stale_and_hash),
                       ("tool-lock", lock_contention), ("reader-conflict", reader_conflict), ("path-boundaries", paths), ("writer-conflict", writer_conflict), ("concurrent-rename", concurrent_rename)):
        case(name, test)
    unchanged = all(sha(P / name) == value for name, value in sources.items())
    result = {"result": "PASS" if len(rows) == 7 and all(r["passed"] for r in rows) and unchanged else "FAIL",
              "cases": rows, "sources": sources, "sources_unchanged": unchanged,
              "game_access": False, "temporary_owned_directories_only": True,
              "engine_exclusion_proven": False, "load_permitted": False}
    artifacts = {}
    def inventory(folder):
        for path in folder.iterdir():
            if os.lstat(path).st_file_attributes & 0x400:
                continue
            if path.is_dir():
                inventory(path)
            elif path.is_file():
                artifacts[str(path.relative_to(run))] = {"size": path.stat().st_size, "sha256": sha(path)}
    inventory(run)
    result["artifacts"] = artifacts
    out = run / "result.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"result": result["result"], "path": str(out)}))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

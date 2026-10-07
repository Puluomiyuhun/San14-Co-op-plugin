"""Native observer infrastructure checks, not game determinism tests."""
import json
from pathlib import Path
import subprocess
import tempfile
import time
from test_submit_probe import wait_json

ROOT = Path(__file__).resolve().parent
FLAGS = subprocess.CREATE_NO_WINDOW
results = []
for mode in ("three-hits", "timeout", "cancel"):
    with tempfile.TemporaryDirectory(dir=ROOT / "lockstep-fixture") as directory:
        folder = Path(directory)
        ready, go, log = (folder / name for name in ("ready.json", "go", "trace.jsonl"))
        fixture = subprocess.Popen([str(ROOT/"lockstep-fixture"/"submit_probe_fixture.exe"), str(ready), str(go)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=FLAGS)
        observer = None
        try:
            info = wait_json(ready)
            observer = subprocess.Popen([str(ROOT/"observe_combat_gate.exe"), str(info["pid"]),
                                         hex(info["base"]), hex(info["rva"]),
                                         "2" if mode=="timeout" else "15", str(log)],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=FLAGS)
            wait_json(log, "armed")
            if mode=="three-hits": go.write_text("go")
            if mode=="cancel": Path(str(log)+".stop").write_text("stop")
            stdout, stderr = observer.communicate(timeout=20)
            rows = [json.loads(line) for line in log.read_text().splitlines()]
            hits = [row["value"] for row in rows if row["event"]=="fixture_hit"]
            assert hits == ([1, 11, 21] if mode=="three-hits" else []), rows
            assert observer.returncode == (0 if mode=="three-hits" else 4), (stderr,rows)
            assert rows[-1] == {"event":"detached", "captured":mode=="three-hits", "registers_restored":True}, rows
            if mode!="three-hits": go.write_text("go")
            stdout, stderr = fixture.communicate(timeout=5)
            assert fixture.returncode==0, (stdout,stderr)
            actual = json.loads(stdout)
            assert actual=={"calls":3, "value":31}, actual
            results.append({"case":mode, "result":"PASS", "hits":hits, "original_function":actual})
        finally:
            if observer and observer.poll() is None:
                Path(str(log)+".stop").write_text("stop")
                observer.wait(timeout=20)
            if fixture.poll() is None:
                go.write_text("go")
                fixture.wait(timeout=5)
(ROOT/"combat-gate-fixtures.json").write_text(json.dumps(results,indent=2))
print(json.dumps(results))

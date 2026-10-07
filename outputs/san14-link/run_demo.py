"""Launch a separate host and client processes, then verify one demo turn."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time


def run():
    program = Path(__file__).with_name("prototype.py")
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    # Ask the OS for a free loopback port. Startup below detects a binding race.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="san14-protocol-demo-") as temp:
        log_path = Path(temp) / "host.log"
        with log_path.open("w", encoding="utf-8") as log:
            host = subprocess.Popen(
                [sys.executable, "-u", str(program), "host", "--port", str(port)],
                stdout=log, stderr=subprocess.STDOUT, creationflags=flags)
            try:
                deadline = time.monotonic() + 10
                while True:
                    text = log_path.read_text(encoding="utf-8")
                    if "Listening on" in text:
                        break
                    if host.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError("Demo host failed to start")
                    time.sleep(0.05)
                tokens = [line.split("token: ", 1)[1]
                          for line in text.splitlines() if " token: " in line]
                if len(tokens) != 2:
                    raise RuntimeError("Expected two player tokens")

                def client(player, *args):
                    result = subprocess.run(
                        [sys.executable, str(program), "client", "--port", str(port),
                         "--token", tokens[player], *args],
                        capture_output=True, text=True, timeout=15, creationflags=flags,
                        check=True)
                    response = json.loads(result.stdout)
                    if not response.get("ok"):
                        raise RuntimeError(response.get("error", "Client failed"))
                    return response["state"]

                before = client(0)
                client(0, "--action", "orders", "--turn", "1", "--id", "a-order",
                       "--recruit", "10")
                client(1, "--action", "orders", "--turn", "1", "--id", "b-order",
                       "--recruit", "20")
                waiting = client(0, "--action", "ready", "--turn", "1", "--id", "a-ready")
                if waiting["turn"] != 1 or waiting["world"] != before["world"]:
                    raise AssertionError("Host advanced before both players were ready")
                client(1, "--action", "ready", "--turn", "1", "--id", "b-ready")
                after_a = client(0)
                after_b = client(1)
                if after_a["world_hash"] != after_b["world_hash"]:
                    raise AssertionError("Clients received different worlds")
                if after_a["turn"] != 2 or after_b["turn"] != 2:
                    raise AssertionError("Expected turn 2 on both clients")
                expected = {"1": {"gold": 110, "army": 1100},
                            "2": {"gold": 100, "army": 1200}}
                expected.update({str(i): {"gold": 120, "army": 1005} for i in range(3, 7)})
                if after_a["world"] != expected:
                    raise AssertionError("Unexpected resolution result")
                print(json.dumps({
                    "result": "PASS", "real_game_connected": False,
                    "transport": "TCP loopback; separate host and client processes",
                    "before_turn": before["turn"],
                    "after_first_ready_turn": waiting["turn"],
                    "after_both_ready_turn": after_a["turn"],
                    "matching_world_hashes": True, "world": after_a["world"],
                    "world_hash": after_a["world_hash"]}, ensure_ascii=False, indent=2))
            finally:
                if host.poll() is None:
                    host.terminate()
                    try:
                        host.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        host.kill()
                        host.wait(timeout=5)


if __name__ == "__main__":
    run()

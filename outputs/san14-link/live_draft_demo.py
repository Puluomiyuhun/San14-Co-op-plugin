"""Send a real game's read-only draft to a separate local receiver. No replay."""
import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time

MAX_FRAME = 65536


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def receive_line(connection):
    data = bytearray()
    while len(data) < MAX_FRAME:
        chunk = connection.recv(min(4096, MAX_FRAME - len(data)))
        if not chunk:
            raise ValueError("Connection closed before the complete message arrived")
        data.extend(chunk)
        if b"\n" in data:
            line, rest = bytes(data).split(b"\n", 1)
            if rest:
                raise ValueError("Only one message is permitted")
            return json.loads(line)
    raise ValueError("Message exceeds the size limit")


def validate_packet(packet, token):
    if not isinstance(packet, dict) or set(packet) != {"token", "payload_sha256", "payload"}:
        raise ValueError("Invalid packet fields")
    if not isinstance(packet["token"], str) or not hmac.compare_digest(packet["token"], token):
        raise ValueError("Invalid one-use test token")
    payload = packet["payload"]
    digest = hashlib.sha256(canonical(payload)).hexdigest()
    if not isinstance(packet["payload_sha256"], str) or not hmac.compare_digest(packet["payload_sha256"], digest):
        raise ValueError("Draft was altered in transit")
    if not isinstance(payload, dict) or payload.get("schema") != "san14.sortie-draft.v1":
        raise ValueError("Unsupported payload schema")
    if (payload.get("mode") != "read-only-live-game" or payload.get("draft_available") is not True
            or payload.get("submitted") is not False or payload.get("replay_supported") is not False):
        raise ValueError("Receiver accepts read-only unsubmitted drafts only")
    partial_hash = hashlib.sha256(canonical(payload.get("partial_order"))).hexdigest()
    if partial_hash != payload.get("partial_order_sha256"):
        raise ValueError("Semantic draft checksum disagrees")
    # This receipt is evidence of delivery, not host-side gameplay authorization.
    return {"received": True, "applied_to_game": False,
            "payload_sha256": digest,
            "validation_scope": "transport integrity only; game legality and ownership not checked",
            "date": payload["date"], "player": payload["player"],
            "partial_order": payload["partial_order"],
            "missing_fields": payload["missing_fields"]}


def receiver(ready_file, token):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        server.settimeout(20)
        Path(ready_file).write_text(str(server.getsockname()[1]), encoding="ascii")
        connection, _ = server.accept()
        with connection:
            connection.settimeout(10)
            try:
                receipt = validate_packet(receive_line(connection), token)
            except (ValueError, TypeError, KeyError, RecursionError) as error:
                receipt = {"received": False, "applied_to_game": False, "error": str(error)}
            connection.sendall(canonical(receipt) + b"\n")


def run_live_demo():
    # Only the sending process imports the game reader. The receiver never opens the game.
    from sortie_reader import SortieReader
    reader = SortieReader()
    try:
        payload = reader.sortie_snapshot()
        if not payload["draft_available"]:
            raise RuntimeError(payload["reason"])
        digest = hashlib.sha256(canonical(payload)).hexdigest()
        token = secrets.token_urlsafe(32)
        packet = {"token": token, "payload_sha256": digest, "payload": payload}
        data = canonical(packet) + b"\n"
        if len(data) > MAX_FRAME:
            raise RuntimeError("Draft is too large for the test frame")
        with tempfile.TemporaryDirectory(prefix="san14-live-draft-") as temporary:
            ready = Path(temporary) / "receiver.port"
            environment = os.environ.copy()
            environment["SAN14_DRAFT_TEST_TOKEN"] = token
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            with (Path(temporary) / "receiver.log").open("w", encoding="utf-8") as log:
                process = subprocess.Popen(
                    [sys.executable, str(Path(__file__).resolve()), "--receive-once", str(ready)],
                    env=environment, stdout=log, stderr=subprocess.STDOUT, creationflags=flags)
                try:
                    deadline = time.monotonic() + 10
                    port = None
                    while port is None:
                        if process.poll() is not None or time.monotonic() >= deadline:
                            raise RuntimeError("Local receiver failed to start")
                        if ready.exists():
                            value = ready.read_text(encoding="ascii").strip()
                            if value:
                                port = int(value)
                        if port is None:
                            time.sleep(0.05)
                    with socket.create_connection(("127.0.0.1", port), timeout=10) as connection:
                        connection.sendall(data)
                        receipt = receive_line(connection)
                    if (receipt.get("received") is not True or receipt.get("applied_to_game") is not False
                            or receipt.get("payload_sha256") != digest
                            or receipt.get("partial_order") != payload["partial_order"]):
                        raise RuntimeError("Receiver receipt disagrees with the sent draft")
                    if process.wait(timeout=5) != 0:
                        raise RuntimeError("Receiver exited with an error")
                finally:
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=5)
        after = reader.sortie_snapshot()
        unchanged = (after.get("partial_order_sha256") == payload["partial_order_sha256"]
                     and after.get("date") == payload["date"]
                     and after.get("player") == payload["player"])
        return {"result": "PASS", "real_game_draft_read": True,
                "transport": "TCP loopback; separate sender and receiver processes",
                "two_game_clients_tested": False, "applied_to_game": False,
                "sampled_date_player_and_draft_unchanged": unchanged,
                "receipt": receipt}
    finally:
        reader.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--receive-once", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.receive_once:
        receiver(args.receive_once, os.environ["SAN14_DRAFT_TEST_TOKEN"])
        return 0
    try:
        result = run_live_demo()
    except (RuntimeError, OSError, ValueError) as error:
        result = {"result": "FAIL", "error": str(error), "applied_to_game": False}
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    print(encoded)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Two-client protocol experiment. Does NOT attach to or modify SAN14."""
import argparse
import asyncio
import copy
import hashlib
import json
import secrets

MAX_FRAME = 65536


class RuleError(Exception):
    pass


class DemoAdapter:
    """Synthetic world only; deliberately has no game-memory implementation."""
    def __init__(self):
        self.world = {str(i): {"gold": 100, "army": 1000} for i in range(1, 7)}

    def validate(self, force, orders):
        if not isinstance(orders, list) or len(orders) > 32:
            raise RuleError("orders must be a list of at most 32 commands")
        for order in orders:
            if not isinstance(order, dict) or set(order) != {"kind", "amount"}:
                raise RuleError("expected kind and amount only")
            if order["kind"] != "recruit" or type(order["amount"]) is not int:
                raise RuleError("demo supports recruit with an integer amount")
            if not 1 <= order["amount"] <= 100:
                raise RuleError("recruit amount must be 1..100")
        if sum(o["amount"] for o in orders) > self.world[force]["gold"]:
            raise RuleError("insufficient gold")

    def resolve(self, drafts, human_forces):
        # Build a candidate, then commit once. No partial world update on failure.
        for force, orders in drafts.items():
            self.validate(force, orders)
        candidate = copy.deepcopy(self.world)
        for force, orders in drafts.items():
            amount = sum(o["amount"] for o in orders)
            candidate[force]["gold"] -= amount
            candidate[force]["army"] += amount * 10
        for force, values in candidate.items():
            if force not in human_forces:
                values["army"] += 5  # Synthetic AI, not SAN14's AI.
            values["gold"] += 20
        self.world = candidate


class Room:
    def __init__(self, tokens=None):
        self.tokens = tokens or {secrets.token_urlsafe(24): "1", secrets.token_urlsafe(24): "2"}
        self.adapter = DemoAdapter()
        self.turn = 1
        self.drafts = {force: [] for force in self.tokens.values()}
        self.ready = set()
        self.receipts = {}

    def snapshot(self, force):
        world = copy.deepcopy(self.adapter.world)
        return {"demo": True, "turn": self.turn, "your_force": force,
                "world": world, "your_orders": copy.deepcopy(self.drafts[force]),
                "ready_forces": sorted(self.ready),
                "world_hash": hashlib.sha256(json.dumps(world, sort_keys=True).encode()).hexdigest()}

    def handle(self, request):
        if not isinstance(request, dict):
            return {"ok": False, "error": "request must be an object"}
        token = request.get("token")
        if not isinstance(token, str) or token not in self.tokens:
            return {"ok": False, "error": "invalid player token"}
        force = self.tokens[token]
        try:
            action = request.get("action")
            if action == "status":
                return {"ok": True, "state": self.snapshot(force)}
            if action not in ("orders", "ready"):
                raise RuleError("unknown action")
            request_id = request.get("id")
            if not isinstance(request_id, str) or not 1 <= len(request_id) <= 128:
                raise RuleError("mutation requires a request id of 1..128 characters")
            key = (force, request_id)
            fingerprint = json.dumps(request, sort_keys=True)
            if key in self.receipts:
                previous, response = self.receipts[key]
                if previous != fingerprint:
                    raise RuleError("request id was reused with different content")
                return copy.deepcopy(response)
            # Bounded in-memory receipts; fail closed rather than forget a retry.
            if len(self.receipts) >= 10000:
                raise RuleError("demo receipt limit reached; restart a new room")
            if type(request.get("turn")) is not int or request["turn"] != self.turn:
                raise RuleError("stale turn; fetch status")
            if force in self.ready:
                raise RuleError("orders are locked after ready")
            if action == "orders":
                orders = request.get("orders")
                self.adapter.validate(force, orders)
                self.drafts[force] = copy.deepcopy(orders)
            else:
                next_ready = self.ready | {force}
                if next_ready == set(self.drafts):
                    self.adapter.resolve(self.drafts, set(self.drafts))
                    self.turn += 1
                    self.drafts = {f: [] for f in self.drafts}
                    self.ready = set()
                else:
                    self.ready = next_ready
            response = {"ok": True, "state": self.snapshot(force)}
            self.receipts[key] = (fingerprint, copy.deepcopy(response))
            return response
        except RuleError as error:
            return {"ok": False, "error": str(error), "state": self.snapshot(force)}


async def serve_connection(reader, writer, room):
    try:
        while True:
            try:
                line = await asyncio.wait_for(reader.readline(), timeout=60)
            except (ValueError, asyncio.TimeoutError):
                break
            if not line:
                break
            try:
                # No await inside handle: each mutation commits before the next.
                response = room.handle(json.loads(line))
            except (ValueError, RecursionError):
                response = {"ok": False, "error": "invalid JSON"}
            writer.write(json.dumps(response, ensure_ascii=False).encode() + b"\n")
            await writer.drain()
    except (ConnectionError, BrokenPipeError):
        pass
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except ConnectionError:
            pass


async def exchange(host, port, request):
    reader, writer = await asyncio.open_connection(host, port, limit=MAX_FRAME)
    try:
        writer.write(json.dumps(request).encode() + b"\n")
        await writer.drain()
        return json.loads(await asyncio.wait_for(reader.readline(), 10))
    finally:
        writer.close()
        await writer.wait_closed()


async def main(args):
    if args.mode == "host":
        room = Room()
        server = await asyncio.start_server(
            lambda r, w: serve_connection(r, w, room), args.bind, args.port, limit=MAX_FRAME)
        print("DEMO ONLY - no SAN14 connection. Room is lost when host exits.", flush=True)
        for token, force in room.tokens.items():
            print(f"Player {force} token: {token}", flush=True)
        print(f"Listening on {args.bind}:{args.port}", flush=True)
        async with server:
            await server.serve_forever()
    else:
        request = {"token": args.token, "action": args.action}
        if args.action != "status":
            if args.turn is None:
                raise SystemExit("--turn is required for orders/ready")
            request.update(turn=args.turn, id=args.id or secrets.token_hex(12))
        if args.action == "orders":
            request["orders"] = [] if args.recruit == 0 else [{"kind": "recruit", "amount": args.recruit}]
        result = await exchange(args.host, args.port, request)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    host = modes.add_parser("host")
    host.add_argument("--bind", default="127.0.0.1")
    host.add_argument("--port", type=int, default=31414)
    client = modes.add_parser("client")
    client.add_argument("--host", default="127.0.0.1")
    client.add_argument("--port", type=int, default=31414)
    client.add_argument("--token", required=True)
    client.add_argument("--action", choices=["status", "orders", "ready"], default="status")
    client.add_argument("--turn", type=int)
    client.add_argument("--id")
    client.add_argument("--recruit", type=int, default=10)
    asyncio.run(main(parser.parse_args()))

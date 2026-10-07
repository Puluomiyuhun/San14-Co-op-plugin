import asyncio
import unittest
from prototype import Room, exchange, serve_connection, MAX_FRAME


class ProtocolTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.room = Room({"alice": "1", "bob": "2"})
        self.server = await asyncio.start_server(
            lambda r, w: serve_connection(r, w, self.room), "127.0.0.1", 0, limit=MAX_FRAME)
        self.port = self.server.sockets[0].getsockname()[1]

    async def asyncTearDown(self):
        self.server.close()
        await self.server.wait_closed()

    async def send(self, token, action="status", **fields):
        return await exchange("127.0.0.1", self.port, dict(token=token, action=action, **fields))

    async def test_two_clients_ready_and_reconnect(self):
        results = await asyncio.gather(
            self.send("alice", "orders", id="a1", turn=1, orders=[dict(kind="recruit", amount=10)]),
            self.send("bob", "orders", id="b1", turn=1, orders=[dict(kind="recruit", amount=20)]))
        self.assertTrue(all(r["ok"] for r in results))
        a = await self.send("alice", "ready", id="a2", turn=1)
        self.assertEqual(a["state"]["turn"], 1)
        self.assertFalse((await self.send("alice", "orders", id="a3", turn=1, orders=[]))["ok"])
        b = await self.send("bob", "ready", id="b2", turn=1)
        retry = await self.send("bob", "ready", id="b2", turn=1)
        self.assertEqual(b, retry)
        a = await self.send("alice")  # New TCP connection: recover authoritative world.
        self.assertEqual(a["state"]["world_hash"], b["state"]["world_hash"])
        self.assertEqual(a["state"]["turn"], 2)
        world = a["state"]["world"]
        self.assertEqual(world["1"], dict(gold=110, army=1100))
        self.assertEqual(world["2"], dict(gold=100, army=1200))
        self.assertEqual(world["3"], dict(gold=120, army=1005))

    async def test_reject_stale_invalid_and_impersonated_orders(self):
        self.assertFalse((await self.send("unknown"))["ok"])
        self.assertFalse((await self.send("alice", "orders", id="x", turn=0, orders=[]))["ok"])
        self.assertFalse((await self.send("alice", "orders", id="y", turn=1,
                                         orders=[dict(kind="recruit", amount=90)] * 2))["ok"])
        self.assertFalse((await self.send("alice", "orders", id="z", turn=1,
                                         orders=[dict(kind="recruit", amount=1, force="2")]))["ok"])
        self.assertEqual(self.room.drafts["1"], [])

    async def test_private_drafts_and_id_collision(self):
        await self.send("alice", "orders", id="x", turn=1, orders=[dict(kind="recruit", amount=7)])
        bob = await self.send("bob")
        self.assertEqual(bob["state"]["your_orders"], [])
        changed = await self.send("alice", "orders", id="x", turn=1, orders=[])
        self.assertFalse(changed["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

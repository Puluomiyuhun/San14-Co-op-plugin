import asyncio
import unittest
from prototype import MAX_FRAME, exchange, serve_connection
from timeline_protocol import TimelineRoom


class TimelineTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.room = TimelineRoom()
        self.server = await asyncio.start_server(
            lambda r, w: serve_connection(r, w, self.room), "127.0.0.1", 0, limit=MAX_FRAME)
        self.port = self.server.sockets[0].getsockname()[1]
        self.serial = 0

    async def asyncTearDown(self):
        self.server.close()
        await self.server.wait_closed()

    async def send(self, token, action="status", **fields):
        request = dict(token=token, action=action, **fields)
        if action != "status":
            self.serial += 1
            request.setdefault("id", f"request-{self.serial}")
            request.setdefault("turn", self.room.turn)
        return await exchange("127.0.0.1", self.port, request)

    async def accepted(self, token, action, **fields):
        result = await self.send(token, action, **fields)
        self.assertTrue(result["ok"], result)
        return result

    async def ack(self, token):
        barrier = self.room.barrier.copy()
        return await self.accepted(token, "sync_ack", barrier_id=barrier["id"], revision=barrier["revision"])

    async def start(self):
        await self.accepted("alice", "ready")
        await self.accepted("bob", "ready")
        self.assertFalse(self.room.advance_day())
        await self.ack("alice")
        self.assertFalse(self.room.advance_day())
        await self.ack("bob")
        self.assertEqual(self.room.phase, "RUNNING")

    async def task(self, token, target, **fields):
        return await self.accepted(token, "submit", command=dict(kind="recruit", target=target), **fields)

    async def answer(self, token, choice="continue", **fields):
        return await self.accepted(token, "event_response", event_id=self.room.events[0]["id"], choice=choice, **fields)

    def advance_to(self, day):
        while self.room.day < day:
            self.assertTrue(self.room.advance_day())

    async def test_day5_and_day7_event_barriers(self):
        await self.task("alice", "officer_a")
        await self.task("bob", "officer_b")
        await self.start()
        self.advance_to(5)
        a, b = await self.send("alice"), await self.send("bob")
        self.assertEqual(a["state"]["event"]["target"], "officer_a")
        self.assertIsNone(b["state"]["event"])
        self.assertTrue(b["state"]["waiting_for_other_player"])
        self.assertEqual(b["state"]["day"], 5)
        self.assertFalse(self.room.advance_day())
        await self.answer("alice")
        await self.ack("alice")
        self.assertFalse(self.room.advance_day())
        await self.ack("bob")
        self.advance_to(7)
        self.assertEqual((await self.send("bob"))["state"]["event"]["target"], "officer_b")
        self.assertIsNone((await self.send("alice"))["state"]["event"])
        self.assertFalse(self.room.advance_day())
        await self.answer("bob")
        await self.ack("alice")
        await self.ack("bob")
        self.advance_to(10)
        self.assertEqual(self.room.turn, 1)
        await self.ack("alice")
        await self.ack("bob")
        self.assertEqual((self.room.turn, self.room.phase, self.room.day), (2, "PLANNING", 10))
        self.assertEqual(self.room.world["1"]["recruited"], ["officer_a"])
        self.assertEqual(self.room.world["2"]["recruited"], ["officer_b"])
        self.assertTrue(all(self.room.world[str(i)]["ai_days"] == 10 for i in range(3, 7)))
        self.assertEqual(self.room.world["1"]["ai_days"], 0)

    async def test_immediate_and_task_start_apply_before_clock(self):
        first = await self.accepted("alice", "submit", id="instant", command={"kind": "reward"})
        retry = await self.accepted("alice", "submit", id="instant", command={"kind": "reward"})
        self.assertEqual(first["receipt"], retry["receipt"])
        self.assertTrue(retry["replayed"])
        await self.task("alice", "officer_a", id="task")
        await self.task("alice", "officer_a", id="task")
        self.assertEqual((self.room.day, self.room.world["1"]["gold"], self.room.world["1"]["loyalty"]), (0, 80, 95))
        self.assertEqual(len(self.room.tasks), 1)
        self.assertEqual(self.room.world["1"]["recruited"], [])

    async def test_no_client_clock_control_or_owner_impersonation(self):
        for action in ("advance_day", "resume", "skip_event"):
            self.assertFalse((await self.send("alice", action))["ok"])
        self.assertFalse((await self.send("unknown"))["ok"])
        self.assertFalse((await self.send("alice", "submit", command={"kind": "reward"}, force="2"))["ok"])
        self.assertFalse((await self.send("alice", "submit", command={"kind": "recruit", "target": "officer_a", "days": 1}))["ok"])
        self.assertEqual(self.room.day, 0)

    async def test_event_owner_and_options_enforced(self):
        await self.task("alice", "officer_a")
        await self.start()
        self.advance_to(5)
        event = self.room.events[0]["id"]
        self.assertFalse((await self.send("bob", "event_response", event_id=event, choice="continue"))["ok"])
        self.assertFalse((await self.send("alice", "event_response", event_id=event, choice="skip"))["ok"])
        self.assertFalse((await self.send("alice", "event_response", event_id="old", choice="continue"))["ok"])
        self.assertEqual(self.room.phase, "WAITING_EVENT")

    async def test_event_retry_does_not_complete_twice(self):
        await self.task("alice", "officer_a")
        await self.start()
        self.advance_to(5)
        event = self.room.events[0]["id"]
        first = await self.answer("alice", id="answer")
        repeated = await self.accepted("alice", "event_response", id="answer", event_id=event, choice="continue")
        self.assertEqual(first["receipt"], repeated["receipt"])
        self.assertEqual(self.room.world["1"]["recruited"], ["officer_a"])
        self.assertEqual(sum(t["kind"] == "event_answered" for t in self.room.trace), 1)
        self.assertFalse((await self.send("alice", "event_response", id="answer", event_id=event, choice="decline"))["ok"])
        self.assertFalse((await self.send("alice", "event_response", event_id=event, choice="continue"))["ok"])

    async def test_same_day_events_all_resolved_before_time_resumes(self):
        self.room.profiles["officer_b"]["days"] = 5
        await self.task("alice", "officer_a")
        await self.task("bob", "officer_b")
        await self.start()
        self.advance_to(5)
        await self.answer("alice")
        self.assertEqual(self.room.phase, "WAITING_EVENT")
        self.assertFalse(self.room.advance_day())
        self.assertEqual((await self.send("bob"))["state"]["event"]["target"], "officer_b")
        await self.answer("bob")
        self.assertEqual(self.room.phase, "SYNCING")
        self.assertEqual(self.room.day, 5)

    async def test_choices_apply_once_and_only_after_response(self):
        self.room.profiles["officer_a"]["mode"] = "choice"
        await self.task("alice", "officer_a")
        await self.start()
        self.advance_to(5)
        self.assertEqual(self.room.world["1"]["recruited"], [])
        event = self.room.events[0]["id"]
        await self.answer("alice", choice="accept", id="choose")
        await self.accepted("alice", "event_response", id="choose", event_id=event, choice="accept")
        self.assertEqual(self.room.world["1"]["recruited"], ["officer_a"])

    async def test_informational_notice_does_not_pause(self):
        self.room.profiles["officer_a"]["mode"] = "notice"
        await self.task("alice", "officer_a")
        await self.start()
        self.advance_to(6)
        self.assertEqual(self.room.phase, "RUNNING")
        self.assertEqual(len((await self.send("alice"))["state"]["your_notices"]), 1)
        self.assertEqual((await self.send("bob"))["state"]["your_notices"], [])

    async def test_disconnect_keeps_event_for_reconnection(self):
        await self.task("alice", "officer_a")
        await self.start()
        self.advance_to(5)
        event = self.room.events[0].copy()
        self.room.set_connected("1", False)
        self.assertFalse(self.room.advance_day())
        self.assertFalse((await self.send("alice", "event_response", event_id=event["id"], choice="continue"))["ok"])
        self.room.set_connected("1", True)
        self.assertEqual((await self.send("alice"))["state"]["event"], event)
        await self.answer("alice")
        self.assertEqual(self.room.day, 5)

    async def test_disconnect_during_running_requires_new_sync(self):
        await self.start()
        self.advance_to(2)
        self.room.set_connected("2", False)
        self.assertFalse(self.room.advance_day())
        self.room.set_connected("2", True)
        self.assertEqual(self.room.phase, "SYNCING")
        self.assertFalse(self.room.advance_day())
        await self.ack("alice")
        await self.ack("bob")
        self.assertTrue(self.room.advance_day())

    async def test_stale_sync_ack_cannot_resume(self):
        await self.accepted("alice", "ready")
        await self.accepted("bob", "ready")
        old = self.room.barrier.copy()
        await self.ack("alice")
        self.room.set_connected("1", False)
        self.room.set_connected("1", True)
        self.assertNotEqual(old["id"], self.room.barrier["id"])
        self.assertFalse((await self.send("alice", "sync_ack", barrier_id=old["id"], revision=old["revision"]))["ok"])
        current = self.room.barrier
        self.assertFalse((await self.send("alice", "sync_ack", barrier_id=current["id"], revision=current["revision"] + 1))["ok"])
        self.assertFalse((await self.send("alice", "sync_ack", barrier_id=current["id"], revision=True))["ok"])
        await self.ack("bob")
        self.assertFalse(self.room.advance_day())
        await self.ack("alice")
        self.assertTrue(self.room.advance_day())

    async def test_planning_edits_locked_during_event_and_after_ready(self):
        await self.task("alice", "officer_a")
        await self.accepted("alice", "ready")
        self.assertFalse((await self.send("alice", "submit", command={"kind": "reward"}))["ok"])
        await self.accepted("bob", "ready")
        await self.ack("alice")
        await self.ack("bob")
        self.advance_to(5)
        self.assertFalse((await self.send("bob", "submit", command={"kind": "reward"}))["ok"])
        self.assertFalse((await self.send("bob", "ready"))["ok"])

    async def test_private_events_not_in_other_state(self):
        await self.task("alice", "officer_a")
        await self.start()
        self.advance_to(5)
        import json
        other = json.dumps((await self.send("bob"))["state"])
        self.assertNotIn("officer_a", other)
        self.assertNotIn(self.room.events[0]["id"], other)
        self.assertNotIn("success", other)

    async def test_delayed_task_spans_turns(self):
        self.room.profiles["officer_a"]["days"] = 12
        await self.task("alice", "officer_a")
        await self.start()
        self.advance_to(10)
        await self.ack("alice")
        await self.ack("bob")
        self.assertEqual(len(self.room.tasks), 1)
        self.assertEqual(self.room.tasks[0]["due_day"], 12)
        await self.start()
        self.advance_to(12)
        self.assertEqual(self.room.events[0]["target"], "officer_a")
        self.assertEqual(self.room.turn, 2)

    async def test_malformed_request_does_not_mutate(self):
        before = self.room.snapshot("1")
        self.assertFalse((await self.send("alice", [], id="bad"))["ok"])
        self.assertFalse((await self.send("alice", "submit", turn=True, command={"kind": "reward"}))["ok"])
        self.assertFalse((await self.send("alice", "submit", command={"kind": "recruit", "target": []}))["ok"])
        self.assertEqual(before, self.room.snapshot("1"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

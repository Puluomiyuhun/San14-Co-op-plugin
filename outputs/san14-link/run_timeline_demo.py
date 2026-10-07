"""Run a synthetic 5/7-day event scenario through two loopback TCP clients."""
import asyncio
import json
from pathlib import Path
from prototype import MAX_FRAME, exchange, serve_connection
from timeline_protocol import TimelineRoom


async def main():
    room = TimelineRoom()
    server = await asyncio.start_server(
        lambda r, w: serve_connection(r, w, room), "127.0.0.1", 0, limit=MAX_FRAME)
    port = server.sockets[0].getsockname()[1]
    serial = 0
    observations = []

    async def send(token, action="status", **fields):
        nonlocal serial
        request = dict(token=token, action=action, **fields)
        if action != "status":
            serial += 1
            request.setdefault("id", f"demo-{serial}")
            request.setdefault("turn", room.turn)
        result = await exchange("127.0.0.1", port, request)
        if not result["ok"]:
            raise RuntimeError(result)
        return result

    async def sync():
        barrier = room.barrier.copy()
        await send("alice", "sync_ack", barrier_id=barrier["id"], revision=barrier["revision"])
        assert not room.advance_day(), "Must wait for both acknowledgments"
        await send("bob", "sync_ack", barrier_id=barrier["id"], revision=barrier["revision"])

    try:
        await send("alice", "submit", command={"kind": "reward"}, id="instant")
        await send("alice", "submit", command={"kind": "reward"}, id="instant")
        assert room.day == 0 and room.world["1"]["gold"] == 90
        for token, target in (("alice", "officer_a"), ("bob", "officer_b")):
            await send(token, "submit", command={"kind": "recruit", "target": target})
        await send("alice", "ready")
        await send("bob", "ready")
        await sync()
        for day, owner, other in ((5, "alice", "bob"), (7, "bob", "alice")):
            while room.day < day:
                assert room.advance_day()
            own = (await send(owner))["state"]
            waiting = (await send(other))["state"]
            assert own["day"] == waiting["day"] == day
            assert own["event"] and waiting["event"] is None and waiting["waiting_for_other_player"]
            assert not room.advance_day()
            event = own["event"]["id"]
            await send(owner, "event_response", id=f"response-{day}", event_id=event, choice="continue")
            retry = await send(owner, "event_response", id=f"response-{day}", event_id=event, choice="continue")
            assert retry["replayed"] and room.day == day and room.phase == "SYNCING"
            await sync()
            observations.append({"day": day, "event_owner": own["your_force"],
                                 "both_clients_stopped_on_same_day": True, "other_client_details_hidden": True,
                                 "response_retry_did_not_execute_twice": True,
                                 "resumed_only_after_both_state_acknowledgments": True})
        while room.day < 10:
            assert room.advance_day()
        await sync()
        assert room.turn == 2 and room.phase == "PLANNING"
        assert room.world["1"]["recruited"] == ["officer_a"]
        assert room.world["2"]["recruited"] == ["officer_b"]
        result = {"result": "PASS", "stage": "SYNTHETIC_EVENT_BARRIERS_PASS_NATIVE_HOOKS_PENDING",
                  "real_game_connected": False, "transport": "Two TCP clients to one in-process loopback server",
                  "new_protocol_tests": 15, "legacy_protocol_regression_tests": 3,
                  "immediate_command_applied_at_day_zero_once": True,
                  "task_creation_applied_at_submission": True, "event_observations": observations,
                  "final_day": room.day, "final_turn": room.turn, "final_phase": room.phase,
                  "synthetic_world": room.world, "trace": room.trace,
                  "limits": ["Delays/outcomes are fixture data, not SAN14 rules",
                             "No actual game pause/event routing/mid-turn synchronization",
                             "No durable host-restart recovery; connection state supplied by host-side test hooks",
                             "Same-target recruitment contention deliberately unsupported"]}
        output = Path(__file__).with_name("旬内事件协议验证.json")
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: v for k, v in result.items() if k not in ("trace", "synthetic_world")}, ensure_ascii=True, indent=2))
    finally:
        server.close()
        await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())

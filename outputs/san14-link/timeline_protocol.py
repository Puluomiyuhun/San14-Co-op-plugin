"""Synthetic event-barrier protocol; never loads or changes SAN14.

Separate from the original whole-turn experiment. Delays/outcomes below are
fixtures, NOT reverse-engineered game rules. Only the host calls advance_day.
Receipts/events survive client reconnection in this room, not a host restart.
"""
import copy
import json
from prototype import RuleError


class TimelineRoom:
    def __init__(self, tokens=None, profiles=None):
        self.tokens = tokens or {"alice": "1", "bob": "2"}
        if len(self.tokens) != 2 or len(set(self.tokens.values())) != 2:
            raise ValueError("Exactly two distinct human forces required")
        self.humans = set(self.tokens.values())
        self.connected = set(self.humans)
        self.world = {str(i): {"gold": 100, "loyalty": 90, "recruited": [], "ai_days": 0}
                      for i in range(1, 7)}
        if not self.humans <= self.world.keys():
            raise ValueError("Unsupported synthetic force")
        # Server-owned test definitions; clients cannot select a duration/outcome.
        self.profiles = profiles or {
            "officer_a": {"days": 5, "cost": 10, "mode": "confirm"},
            "officer_b": {"days": 7, "cost": 10, "mode": "confirm"},
        }
        for profile in self.profiles.values():
            if (type(profile.get("days")) is not int or not 1 <= profile["days"] <= 1000
                    or type(profile.get("cost")) is not int or not 0 <= profile["cost"] <= 100
                    or profile.get("mode") not in ("confirm", "choice", "notice")):
                raise ValueError("Invalid synthetic task profile")
        self.turn = 1
        self.day = 0  # Absolute synthetic day; not a SAN14 calendar decoder.
        self.turn_end = 10
        self.phase = "PLANNING"
        self.revision = 0
        self.ready = set()
        self.tasks = []
        self.targets = set()
        self.events = []
        self.notices = {f: [] for f in self.humans}
        self.receipts = {}
        self.sequence = 0
        self.barrier = None
        self.acks = set()
        self.after_sync = None
        self.trace = []

    def _id(self, prefix):
        self.sequence += 1
        return f"{prefix}-{self.sequence}"

    def _log(self, kind, **fields):
        self.trace.append(dict(kind=kind, day=self.day, phase=self.phase, **fields))

    def snapshot(self, force):
        event = self.events[0] if self.events else None
        owns_event = event is not None and event["owner"] == force
        return {
            "demo": True, "real_game_connected": False, "turn": self.turn,
            "day": self.day, "phase": self.phase, "world_revision": self.revision,
            "your_force": force, "your_state": copy.deepcopy(self.world[force]),
            "your_tasks": [copy.deepcopy(t) for t in self.tasks if t["owner"] == force],
            "your_notices": copy.deepcopy(self.notices[force]),
            "ready_forces": sorted(self.ready), "disconnected_forces": sorted(self.humans - self.connected),
            "event": copy.deepcopy(event) if owns_event else None,
            # The other player sees neither target, outcome nor options.
            "waiting_for_other_player": event is not None and not owns_event,
            "sync_barrier": copy.deepcopy(self.barrier), "sync_acknowledged": force in self.acks,
        }

    def _start_sync(self, next_phase):
        self.phase = "SYNCING"
        self.after_sync = next_phase
        self.acks = set()
        self.barrier = {"id": self._id("barrier"), "revision": self.revision, "day": self.day}
        self._log("sync_required", barrier=copy.deepcopy(self.barrier))

    def set_connected(self, force, connected):
        """Host-side transport notification, not a client permission switch."""
        if force not in self.humans:
            raise ValueError("Unknown player")
        if connected:
            was_missing = force not in self.connected
            self.connected.add(force)
            if was_missing and self.phase == "RUNNING":
                self._start_sync("RUNNING")
        else:
            was_connected = force in self.connected
            self.connected.discard(force)
            self.acks.discard(force)
            if was_connected and self.phase == "SYNCING":
                self._start_sync(self.after_sync)
        self._log("connection", force=force, connected=connected)

    def advance_day(self):
        """Host-only synthetic tick. False means do not call the next game step.

        A real adapter must stop at the native event continuation BEFORE moving
        past that event, including events within a day. This daily fixture is
        not evidence that pausing the actual game has been implemented.
        """
        if self.phase != "RUNNING" or self.connected != self.humans:
            return False
        self.day += 1
        self.revision += 1
        for force in self.world.keys() - self.humans:
            self.world[force]["ai_days"] += 1
        due = [t for t in self.tasks if t["due_day"] <= self.day]
        self.tasks = [t for t in self.tasks if t["due_day"] > self.day]
        for task in due:
            mode = task["mode"]
            if mode in ("confirm", "notice"):
                # The result exists at the event date; closing its notice does
                # not run the completed task or grant the officer a second time.
                self.world[task["owner"]]["recruited"].append(task["target"])
            event = {"id": self._id("event"), "owner": task["owner"], "day": self.day,
                     "task_id": task["id"], "target": task["target"], "mode": mode,
                     "options": ["accept", "decline"] if mode == "choice" else ["continue"],
                     "synthetic_result": "pending_choice" if mode == "choice" else "success"}
            if mode == "notice":
                self.notices[task["owner"]].append(event)
            else:
                self.events.append(event)
        self._log("day_advanced", completed_tasks=len(due))
        if self.events:
            self.phase = "WAITING_EVENT"
            self._log("event_paused", event_id=self.events[0]["id"])
        elif self.day == self.turn_end:
            self._start_sync("PLANNING")
        return True

    def _apply(self, force, request):
        action = request.get("action")
        base = {"token", "action", "id", "turn"}
        fields = {"submit": {"command"}, "ready": set(),
                  "event_response": {"event_id", "choice"}, "sync_ack": {"barrier_id", "revision"}}
        if type(action) is not str or action not in fields or set(request) != base | fields[action]:
            raise RuleError("Unknown action or unexpected fields")
        if type(request["turn"]) is not int or request["turn"] != self.turn:
            raise RuleError("Stale turn")
        if force not in self.connected:
            raise RuleError("Player must reconnect before mutation")
        if action in ("submit", "ready"):
            if self.phase != "PLANNING" or force in self.ready:
                raise RuleError("Planning commands are locked")
            if action == "ready":
                self.ready.add(force)
                if self.ready == self.humans:
                    # Clients must apply accepted immediate effects/task starts
                    # before the authority starts its clock.
                    self._start_sync("RUNNING")
                return {"ready": True}
            command = request["command"]
            if type(command) is not dict:
                raise RuleError("Expected command object")
            values = self.world[force]
            if command == {"kind": "reward"}:
                if values["gold"] < 10 or values["loyalty"] >= 100:
                    raise RuleError("Synthetic reward unavailable")
                values["gold"] -= 10
                values["loyalty"] = min(100, values["loyalty"] + 5)
                self.revision += 1
                self._log("immediate_committed", force=force)
                return {"committed_revision": self.revision}
            if set(command) != {"kind", "target"} or command["kind"] != "recruit":
                raise RuleError("Unsupported synthetic command")
            target = command["target"]
            if type(target) is not str or target not in self.profiles:
                raise RuleError("Unknown synthetic target")
            profile = self.profiles[target]
            # Deliberately independent targets. Shared-target contention needs
            # native game rules, not a first-packet-wins multiplayer rule.
            if target in self.targets:
                raise RuleError("Shared target contention not supported in this fixture")
            if values["gold"] < profile["cost"]:
                raise RuleError("Insufficient gold")
            task = {"id": self._id("task"), "owner": force, "target": target,
                    "due_day": self.day + profile["days"], "mode": profile["mode"]}
            values["gold"] -= profile["cost"]
            self.tasks.append(task)
            self.targets.add(target)
            self.revision += 1
            self._log("task_started", force=force, task_id=task["id"], due_day=task["due_day"])
            return {"task_id": task["id"], "committed_revision": self.revision}
        if action == "event_response":
            if self.phase != "WAITING_EVENT" or not self.events:
                raise RuleError("No interactive event")
            event = self.events[0]
            if event["owner"] != force or request["event_id"] != event["id"]:
                raise RuleError("Event does not belong to this player or is stale")
            if request["choice"] not in event["options"]:
                raise RuleError("Invalid event choice")
            if event["mode"] == "choice" and request["choice"] == "accept":
                self.world[force]["recruited"].append(event["target"])
            self.events.pop(0)
            self.revision += 1
            self._log("event_answered", event_id=event["id"], force=force)
            if not self.events:
                self._start_sync("PLANNING" if self.day == self.turn_end else "RUNNING")
            return {"event_id": event["id"], "recorded": True}
        if self.phase != "SYNCING" or request["barrier_id"] != self.barrier["id"]:
            raise RuleError("Stale synchronization barrier")
        if type(request["revision"]) is not int or request["revision"] != self.barrier["revision"]:
            raise RuleError("Client has not applied the required revision")
        self.acks.add(force)
        if self.acks == self.humans and self.connected == self.humans:
            self.phase = self.after_sync
            self.barrier = None
            self.acks = set()
            if self.phase == "PLANNING":
                self.turn += 1
                self.turn_end += 10
                self.ready = set()
            self._log("sync_complete")
        return {"acknowledged": True}

    def handle(self, request):
        if type(request) is not dict or type(request.get("token")) is not str or request["token"] not in self.tokens:
            return {"ok": False, "error": "Invalid player token"}
        force = self.tokens[request["token"]]
        try:
            if request.get("action") == "status":
                if set(request) != {"token", "action"}:
                    raise RuleError("Unexpected status fields")
                return {"ok": True, "state": self.snapshot(force)}
            identity = request.get("id")
            if type(identity) is not str or not 1 <= len(identity) <= 128:
                raise RuleError("Mutation requires a request id")
            key = (force, identity)
            fingerprint = json.dumps(request, sort_keys=True, separators=(",", ":"))
            if key in self.receipts:
                previous, receipt = self.receipts[key]
                if previous != fingerprint:
                    raise RuleError("Request id reused with different content")
                return {"ok": True, "replayed": True, "receipt": copy.deepcopy(receipt), "state": self.snapshot(force)}
            if len(self.receipts) >= 10000:
                raise RuleError("Demo receipt capacity reached")
            receipt = self._apply(force, request)
            self.receipts[key] = (fingerprint, copy.deepcopy(receipt))
            return {"ok": True, "replayed": False, "receipt": receipt, "state": self.snapshot(force)}
        except RuleError as error:
            return {"ok": False, "error": str(error), "state": self.snapshot(force)}

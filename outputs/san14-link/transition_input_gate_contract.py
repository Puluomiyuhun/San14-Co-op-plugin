"""Offline contract for a future game-thread input adapter, NOT a native gate.

Only trusted local adapter observations belong here. This module does not read
devices, filter messages, verify a world/journal, install hooks, or block input.
The adapter must keep polling/draining every input provider and processing engine
and window lifecycle messages while publishing neutral gameplay input. Merely
calling native 3A2700 is insufficient; see transition_input_gate_shadow.py.

All operations are serialized at a verified game-thread consumer boundary. A
release grant comes from the presentation/world controller AFTER its checks;
passing an arbitrary grant is not proof those checks occurred. The final receipt
may be acknowledged only before that cycle's gameplay consumer, with no unseen
poll/message dispatch between the observation and acknowledgement.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import re
import secrets


CHANNELS = (
    "normal_cache", "raw_keyboard", "special_repeat", "mouse",
    "controller_di", "controller_alternate", "posted_messages",
)


class GateError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise GateError(message)


def _identifier(value: str) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{32}", value) is not None


def _integer(value: int, minimum: int = 0) -> bool:
    return type(value) is int and value >= minimum


@dataclass(frozen=True)
class Binding:
    attempt: str
    attachment: str
    generation: int = 0


@dataclass(frozen=True)
class Boundary:
    binding: Binding
    thread_id: int
    cycle_id: int
    state: str = "CUserStrategyState"
    phase: int = 2
    stable_planning: bool = True
    pending_menu: int = -1
    pending_advance: bool = False
    pending_dispatch: bool = False


@dataclass(frozen=True)
class ChannelEvidence:
    name: str
    drain_cycle: int
    publish_cycle: int
    neutral: bool = True
    covered: bool = True


@dataclass(frozen=True)
class PhysicalState:
    """Physical state BEFORE neutral publication; absence/unknown isn't release.

    Axis dead zones and provider enumeration must be defined by the real adapter.
    Tuples contain non-neutral controls only. Motion/wheel activity also prevents
    release for that cycle. An unplug/focus-loss/error is unknown until re-polled,
    never an all-released observation.
    """
    keyboard_down: tuple[int, ...] = ()
    modifier_bits: int = 0
    mouse_buttons: tuple[int, ...] = ()
    mouse_motion_or_wheel: bool = False
    controller_buttons: tuple[int, ...] = ()
    controller_axes: tuple[int, ...] = ()
    unknown: bool = False

    def all_released(self) -> bool:
        return not (
            self.keyboard_down or self.modifier_bits or self.mouse_buttons
            or self.mouse_motion_or_wheel or self.controller_buttons
            or self.controller_axes or self.unknown
        )


@dataclass(frozen=True)
class Cycle:
    binding: Binding
    thread_id: int
    cycle_id: int
    channels: tuple[ChannelEvidence, ...]
    physical: PhysicalState
    pending_gameplay_messages: int = 0
    message_pump_continued: bool = True
    worker_dispatch_continued: bool = True


@dataclass(frozen=True)
class ReleaseReceipt:
    binding: Binding
    grant: str
    cycle_id: int
    nonce: str


class NeutralInputGate:
    """One attempt, including its verified post-load attachment handoff.

    NEW is closed/NOT armed: the controller may not start teardown until arm()
    succeeds. HELD and RELEASE_PENDING remain closed. OPEN is terminal; use a
    new instance/attempt next time. Rejected observations invalidate release
    evidence but do not open input. This is an in-memory adapter contract only.
    """

    native_gate_complete = False

    def __init__(self, binding: Binding, game_thread_id: int):
        self._validate_binding(binding)
        _require(_integer(game_thread_id, 1), "invalid game thread")
        self.binding = binding
        self.game_thread_id = game_thread_id
        self.state = "NEW"
        self.last_cycle: Cycle | None = None
        self._grant: str | None = None
        self._barrier = -1
        self._candidate: ReleaseReceipt | None = None
        self._verification_ids: set[str] = set()
        self._healthy = False

    @staticmethod
    def _validate_binding(binding: Binding) -> None:
        _require(type(binding) is Binding, "invalid binding")
        _require(_identifier(binding.attempt) and _identifier(binding.attachment), "invalid binding identifiers")
        _require(_integer(binding.generation), "invalid binding generation")

    def _boundary(self, boundary: Boundary, binding: Binding, cycle_id: int) -> None:
        _require(type(boundary) is Boundary, "invalid boundary")
        self._validate_binding(boundary.binding)
        _require(boundary.binding == binding, "wrong boundary attachment/attempt")
        _require(type(boundary.thread_id) is int and boundary.thread_id == self.game_thread_id, "wrong game thread")
        _require(_integer(boundary.cycle_id) and boundary.cycle_id == cycle_id, "boundary is not current cycle")
        _require(boundary.state == "CUserStrategyState" and type(boundary.phase) is int and boundary.phase == 2,
                 "not planning phase 2")
        _require(boundary.stable_planning is True, "unstable planning boundary")
        _require(type(boundary.pending_menu) is int and boundary.pending_menu == -1, "pending menu command")
        _require(boundary.pending_advance is False, "pending advance request")
        _require(boundary.pending_dispatch is False, "command already latched for dispatch")

    def _cycle(self, cycle: Cycle, binding: Binding) -> None:
        _require(type(cycle) is Cycle and cycle.binding == binding, "wrong cycle attachment/attempt")
        self._validate_binding(cycle.binding)
        _require(type(cycle.thread_id) is int and cycle.thread_id == self.game_thread_id, "wrong game thread")
        _require(_integer(cycle.cycle_id), "invalid cycle")
        _require(self.last_cycle is None or cycle.cycle_id > self.last_cycle.cycle_id, "stale cycle")
        _require(type(cycle.channels) is tuple and len(cycle.channels) == len(CHANNELS), "missing input channel")
        _require(all(type(c) is ChannelEvidence for c in cycle.channels), "invalid channel evidence")
        _require(all(type(c.name) is str for c in cycle.channels), "invalid channel name")
        _require({c.name for c in cycle.channels} == set(CHANNELS), "duplicate/unknown input channel")
        for c in cycle.channels:
            _require(c.covered is True and c.neutral is True, "uncovered or nonneutral channel: " + c.name)
            _require(_integer(c.drain_cycle) and _integer(c.publish_cycle)
                     and c.drain_cycle == cycle.cycle_id == c.publish_cycle,
                     "stale drain/publication: " + c.name)
        _require(cycle.message_pump_continued is True and cycle.worker_dispatch_continued is True,
                 "cannot block message pump or native worker dispatch")
        _require(_integer(cycle.pending_gameplay_messages), "invalid pending gameplay message count")
        p = cycle.physical
        _require(type(p) is PhysicalState, "missing physical observation")
        for values in (p.keyboard_down, p.mouse_buttons, p.controller_buttons, p.controller_axes):
            _require(type(values) is tuple and all(_integer(v) for v in values), "invalid physical controls")
            _require(len(values) == len(set(values)), "duplicate physical controls")
        _require(_integer(p.modifier_bits), "invalid modifier bits")
        _require(type(p.mouse_motion_or_wheel) is bool and type(p.unknown) is bool, "invalid physical flags")

    def arm(self, boundary: Boundary, cycle: Cycle) -> None:
        _require(self.state == "NEW", "attempt already armed")
        self._cycle(cycle, self.binding)
        self._boundary(boundary, self.binding, cycle.cycle_id)
        _require(cycle.pending_gameplay_messages == 0, "queued gameplay messages at arm")
        self.last_cycle = cycle
        self._healthy = True
        self.state = "HELD"

    def observe_cycle(self, cycle: Cycle) -> ReleaseReceipt | None:
        """After polling/draining AND neutral publication, before UI consumption.

        Physical input may remain pressed during rebuild; it never causes OPEN.
        Observation remains required throughout title/load/worker completion.
        """
        self._candidate = None
        self._healthy = False
        _require(self.state in ("HELD", "RELEASE_PENDING"), "not holding input")
        self._cycle(cycle, self.binding)
        self.last_cycle = cycle
        self._healthy = True
        if (self.state == "RELEASE_PENDING" and cycle.cycle_id > self._barrier
                and cycle.physical.all_released() and cycle.pending_gameplay_messages == 0):
            self._candidate = ReleaseReceipt(self.binding, self._grant, cycle.cycle_id, secrets.token_hex(16))
        return self._candidate

    def request_release(self, boundary: Boundary, grant: str) -> None:
        """Caller must first verify presentation/world/journal. Remains closed."""
        self._candidate = None
        was_healthy, self._healthy = self._healthy, False
        _require(self.state == "HELD", "release already requested or gate not held")
        _require(was_healthy, "latest neutral observation is invalid")
        _require(_identifier(grant), "invalid controller release grant")
        self._boundary(boundary, self.binding, self.last_cycle.cycle_id)
        self._grant = grant
        self._barrier = self.last_cycle.cycle_id
        self.state = "RELEASE_PENDING"
        self._healthy = True

    def cancel_release(self) -> None:
        """Controller revocation/failure keeps input closed; polling continues."""
        self._candidate = None
        _require(self.state in ("HELD", "RELEASE_PENDING"), "gate is not held")
        self._grant = None
        self._barrier = -1
        self.state = "HELD"

    def confirm_planning_boundary(self, boundary: Boundary) -> None:
        """Fresh local planning check without issuing a release permission."""
        try:
            _require(self.state in ("HELD", "RELEASE_PENDING") and self._healthy,
                     "no current neutral observation")
            self._boundary(boundary, self.binding, self.last_cycle.cycle_id)
        except BaseException:
            self._candidate = None
            self._healthy = False
            raise

    def acknowledge_release(self, boundary: Boundary, receipt: ReleaseReceipt, grant: str) -> None:
        candidate = self._candidate
        self._candidate = None  # even rejected/old receipts cannot retain eligibility
        self._healthy = False
        _require(self.state == "RELEASE_PENDING", "release is not pending")
        _require(type(receipt) is ReleaseReceipt and candidate is not None and receipt == candidate,
                 "stale, forged, or superseded release receipt")
        _require(grant == self._grant == receipt.grant, "release grant changed")
        self._boundary(boundary, self.binding, self.last_cycle.cycle_id)
        _require(self.last_cycle.physical.all_released() and self.last_cycle.pending_gameplay_messages == 0,
                 "physical input or posted gameplay messages remain")
        self.state = "OPEN"
        self._healthy = True

    def handoff_attachment(self, old: Binding, new: Binding, boundary: Boundary,
                           cycle: Cycle, verification_id: str) -> None:
        """Trusted controller's verified new world; NOT verification by this gate.

        The controller must bind this ID to its journal/world/force/attachment
        result. No old release grant survives. Input remains held, and release
        needs a new request and a strictly later neutral physical cycle.
        """
        self._candidate = None
        self._healthy = False
        _require(self.state in ("HELD", "RELEASE_PENDING"), "cannot handoff open/unarmed gate")
        _require(old == self.binding, "wrong previous binding")
        self._validate_binding(new)
        _require(new.attempt == old.attempt and new.attachment != old.attachment
                 and new.generation == old.generation + 1, "invalid attachment handoff")
        _require(_identifier(verification_id) and verification_id not in self._verification_ids,
                 "invalid/reused controller verification")
        self._cycle(cycle, new)
        self._boundary(boundary, new, cycle.cycle_id)
        _require(cycle.pending_gameplay_messages == 0, "messages pending on new attachment")
        self.binding = new
        self.last_cycle = cycle
        self._verification_ids.add(verification_id)
        self._grant = None
        self._barrier = -1
        self.state = "HELD"
        self._healthy = True

    def status(self) -> dict:
        return {
            "state": self.state, "binding": asdict(self.binding),
            "last_cycle": None if self.last_cycle is None else self.last_cycle.cycle_id,
            "neutral_publication_confirmed": self.state in ("HELD", "RELEASE_PENDING") and self._healthy,
            "contract_allows_input": self.state == "OPEN",
            "release_receipt_ready": self._candidate is not None,
            "latest_observation_valid": self._healthy,
            "native_gate_complete": False, "game_input_actually_blocked": False,
        }

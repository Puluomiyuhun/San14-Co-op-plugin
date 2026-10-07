"""Reusable LOCAL research bridge; every backend observation is synthetic.

Uses the real checkpoint journal/coordinator/presentation modules and input/
surface contracts. No process, hook, device, renderer or network access exists
here. Native-looking booleans passed into older contracts are fixture evidence,
never a report that SAN14 has actually been covered or gated. This controller
cannot be enabled for production by changing an argument.

External callers must route BOTH planning admission and ready through the
combined predicate, not directly through PeriodCoordinator's PLANNING phase.
The final input ack is serialized on the adapter's game-thread boundary. The
native adapter must prevent an unobserved input poll/dispatch before consumers.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import secrets
import sys
import threading

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "outputs" / "san14-link"))
from authoritative_sync import PeriodCoordinator, canonical, hexid, require
from checkpoint_journal import CheckpointJournal
from checkpoint_presentation import MapWaitGate
from transition_visual_surface import Frame, TransitionSurface, PresentationReceipt
from transition_input_gate_contract import Binding, Boundary, Cycle, NeutralInputGate, ReleaseReceipt


def frame_id(frame: Frame) -> str:
    require(type(frame) is Frame, "Immutable captured frame required")
    return sha256(canonical({"revision": frame.revision, "pixels": frame.digest})).hexdigest()[:32]


class CheckpointLocalTransition:
    """One checkpoint/attempt, with real durable intent and synthetic backend.

    Caller creates/stages the journal and calls coordinator.received first.
    Methods only return tickets/permits; none executes a native operation.
    A failure latches HELD. Reconnection does not revive the old release grant.
    This object is not persistent and does not implement restart recovery.
    """

    def __init__(self, coordinator: PeriodCoordinator, journal: CheckpointJournal, game_thread_id: int):
        require(type(coordinator) is PeriodCoordinator and type(journal) is CheckpointJournal,
                "Real coordinator and journal required")
        self.lock = threading.RLock()
        self.coordinator, self.journal = coordinator, journal
        self.presentation = MapWaitGate(coordinator, journal)
        self.surface = TransitionSurface()
        self.inputs = NeutralInputGate(
            Binding(self.presentation.nonce, journal.identity["attachments"]["B"]), game_thread_id)
        self.phase = "NEW"
        self.hold_reason = None
        self.cover = None
        self.pending_map = None
        self.reveal = None

    @property
    def binding(self) -> Binding:
        return self.inputs.binding

    def expected_loaded_binding(self, attachment: str) -> Binding:
        """Construct an expected label only; complete_load verifies it first."""
        require(hexid(attachment, 32), "Bad proposed attachment")
        return Binding(self.binding.attempt, attachment, self.binding.generation + 1)

    def _hold(self, reason: str):
        self.hold_reason = reason
        self.phase = "HELD"
        self.presentation.hold(reason)
        if self.inputs.state in ("HELD", "RELEASE_PENDING"):
            self.inputs.cancel_release()
        # Surface has no post-RELEASED recovery operation. Do not claim that a
        # previously removed cover is visible. Status requests a fresh cover.
        if self.surface.phase not in ("IDLE", "RELEASED", "FAILED"):
            self.surface.fail(self.binding.attempt, reason)

    def hold(self, reason: str):
        require(type(reason) is str and 1 <= len(reason) <= 80, "Bad hold reason")
        with self.lock, self.presentation.lock, self.coordinator.lock:
            self._hold(reason)

    def _connected(self):
        if self.coordinator.connected != {"A", "B"}:
            self._hold("PEER_DISCONNECTED")
        require(self.phase != "HELD", "Transition held: " + str(self.hold_reason))

    def begin_cover(self, old_frame: Frame, *, view: str, surface: str, window_mode: str,
                    boundary: Boundary, cycle: Cycle):
        with self.lock, self.presentation.lock, self.coordinator.lock:
            self._connected()
            require(self.phase == "NEW", "Cover already begun")
            require(hexid(view, 32) and hexid(surface, 32), "Bad view/surface identity")
            require(window_mode in ("windowed", "borderless"), "Unsupported window mode")
            fid = frame_id(old_frame)
            self.inputs.arm(boundary, cycle)
            ticket = self.surface.begin(self.binding.attempt, old_frame, native_input_gate_ack=True)
            self.cover = {"presentation": self.presentation.nonce,
                "checkpoint_id": self.journal.identity["checkpoint_id"],
                "attachment": self.binding.attachment, "frame": fid, "view": view,
                "surface": surface, "window_mode": window_mode,
                "visible": True, "input_blocked": True}
            self.phase = "COVER_PENDING"
            return ticket

    def acknowledge_cover(self, receipt: PresentationReceipt):
        with self.lock, self.presentation.lock, self.coordinator.lock:
            self._connected()
            require(self.phase == "COVER_PENDING", "No pending cover")
            try:
                self.surface.acknowledge(receipt)
                require(self.surface.may_start_native, "Cover not presented")
                require(self.inputs.status()["neutral_publication_confirmed"], "Input evidence lost")
                self.presentation.cover_presented(deepcopy(self.cover))
                self.phase = "COVERED"
            except BaseException:
                self._hold("COVER_ACK_FAILED")
                raise

    def reserve_load(self, host: dict, old_guest: dict, boundary: Boundary):
        """Durable, once-only research permit. DOES NOT submit a native load."""
        with self.lock, self.presentation.lock, self.coordinator.lock:
            self._connected()
            require(self.phase == "COVERED", "No covered load boundary")
            try:
                self.inputs.confirm_planning_boundary(boundary)
                require(self.inputs.state == "HELD" and self.surface.may_start_native,
                        "Input/surface no longer held")
                permit = self.presentation.reserve_load(host, old_guest)
                self.surface.native_started(self.binding.attempt)
                self.phase = "LOADING"
                return permit
            except BaseException:
                self._hold("LOAD_RESERVATION_UNCERTAIN")
                raise

    def complete_load(self, receipt: dict, host: dict, guest: dict,
                      boundary: Boundary, cycle: Cycle):
        """Verify durable world receipt BEFORE adopting its new attachment."""
        with self.lock, self.presentation.lock, self.coordinator.lock:
            self._connected()
            require(self.phase == "LOADING" and self.inputs.state == "HELD", "Not a closed load boundary")
            try:
                self.journal.complete(receipt)
                self.presentation.world_restored(host, guest)
                old = self.binding
                new = self.expected_loaded_binding(self.presentation.new_attachment)
                self.inputs.handoff_attachment(old, new, boundary, cycle, secrets.token_hex(16))
                self.phase = "WORLD_RESTORED"
            except BaseException:
                self._hold("WORLD_OR_ATTACHMENT_UNCONFIRMED")
                raise

    def map_frame_presented(self, frame: Frame, observation: dict):
        """Synthetic backend's new map under the retained old-picture cover."""
        with self.lock, self.presentation.lock, self.coordinator.lock:
            self._connected()
            require(self.phase == "WORLD_RESTORED" and self.inputs.state == "HELD", "No closed restored world")
            try:
                require(type(observation) is dict and observation.get("frame") == frame_id(frame)
                        and observation.get("attachment") == self.binding.attachment,
                        "New frame/attachment mismatch")
                self.presentation.map_frame_presented(observation)
                self.pending_map = (frame, deepcopy(observation))
                self.phase = "READY_TO_REVEAL"
            except BaseException:
                self._hold("NEW_MAP_UNCONFIRMED")
                raise

    def begin_reveal(self, host: dict, guest: dict):
        with self.lock, self.presentation.lock, self.coordinator.lock:
            self._connected()
            require(self.phase == "READY_TO_REVEAL" and self.inputs.state == "HELD", "No held new map")
            try:
                frame, observation = self.pending_map
                require(observation["attachment"] == self.binding.attachment
                        and observation["frame"] == frame_id(frame), "Pending frame changed")
                self.reveal = self.presentation.begin_reveal(host, guest)
                require(self.reveal["attachment"] == self.binding.attachment, "Wrong reveal attachment")
                ticket = self.surface.prepare_release(self.binding.attempt, frame,
                                                      controller_grant=self.reveal["token"])
                self.phase = "REVEAL_PENDING"
                return ticket
            except BaseException:
                self._hold("REVEAL_NOT_CONFIRMED")
                raise

    def acknowledge_reveal(self, receipt: PresentationReceipt, boundary: Boundary):
        """Only after revealed + surface commit do we request input release."""
        with self.lock, self.presentation.lock, self.coordinator.lock:
            self._connected()
            require(self.phase == "REVEAL_PENDING", "No pending reveal")
            try:
                self.inputs.confirm_planning_boundary(boundary)
                self.surface.acknowledge(receipt)
                self.presentation.revealed(self.reveal)
                self.surface.commit_release(self.binding.attempt, controller_grant=self.reveal["token"])
                require(self.presentation.status()["accept_planning_intents"], "Presentation not LIVE")
                self.inputs.request_release(boundary, self.reveal["token"])
                self.phase = "WAITING_FOR_RELEASE"
            except BaseException:
                self._hold("REVEAL_ACK_FAILED")
                raise

    def observe_cycle(self, cycle: Cycle) -> ReleaseReceipt | None:
        """Still drain while HELD; a failed transition never creates a receipt."""
        with self.lock, self.presentation.lock, self.coordinator.lock:
            if self.coordinator.connected != {"A", "B"}:
                self._hold("PEER_DISCONNECTED")
            if self.phase == "WAITING_FOR_RELEASE" and not self.presentation.status()["accept_planning_intents"]:
                self._hold("PRESENTATION_OR_ROOM_CHANGED")
            try:
                receipt = self.inputs.observe_cycle(cycle)
                return receipt if self.phase == "WAITING_FOR_RELEASE" else None
            except BaseException:
                self._hold("INPUT_CYCLE_UNCONFIRMED")
                raise

    def _fresh_world(self, host: dict, guest: dict):
        identity = self.journal.identity
        manifest = identity["manifest"]
        expected_host = {"attachment": identity["attachments"]["A"],
                         "world_sha256": manifest["world_sha256"], "node": manifest["node"]}
        expected_guest = {"attachment": self.binding.attachment, "safe_boundary": True,
                         "world_sha256": manifest["world_sha256"], "node": manifest["node"],
                         "viewer_force": identity["scope"]["bindings"]["B"]["force_id"]}
        require(canonical(host) == canonical(expected_host) and canonical(guest) == canonical(expected_guest),
                "Current world/force/attachment changed before input release")

    def acknowledge_input_release(self, receipt: ReleaseReceipt, boundary: Boundary,
                                  host: dict, guest: dict):
        with self.lock, self.presentation.lock, self.coordinator.lock:
            self._connected()
            require(self.phase == "WAITING_FOR_RELEASE", "No pending input release")
            try:
                require(self.presentation.status()["accept_planning_intents"]
                        and self.surface.phase == "RELEASED"
                        and self.binding.attachment == self.coordinator.attachments["B"],
                        "Presentation/room/attachment changed")
                self._fresh_world(host, guest)
                self.inputs.acknowledge_release(boundary, receipt, self.reveal["token"])
                self.phase = "OPEN"
            except BaseException:
                self._hold("INPUT_RELEASE_UNCONFIRMED")
                raise

    def _accept(self) -> bool:
        return (self.phase == "OPEN" and self.presentation.status()["accept_planning_intents"]
                and self.surface.phase == "RELEASED" and self.surface.available
                and self.inputs.status()["contract_allows_input"]
                and self.binding.attempt == self.presentation.nonce
                and self.binding.attachment == self.presentation.new_attachment == self.coordinator.attachments["B"])

    def require_local_planning(self, epoch: str, attachment: str):
        """Reusable admission guard; callers must not bypass it via coordinator."""
        with self.lock, self.presentation.lock, self.coordinator.lock:
            self._connected()
            require(self._accept() and epoch == self.coordinator.epoch and attachment == self.binding.attachment,
                    "Local presentation/physical input/room still held")
            return {"epoch": epoch, "attachment": attachment, "synthetic_only": True,
                    "native_gameplay_enabled": False}

    def set_local_ready(self, value: bool):
        with self.lock, self.presentation.lock, self.coordinator.lock:
            self.require_local_planning(self.coordinator.epoch, self.binding.attachment)
            self.coordinator.set_ready("B", self.coordinator.epoch, value)

    def status(self):
        with self.lock, self.presentation.lock, self.coordinator.lock:
            if self.coordinator.connected != {"A", "B"}:
                self._hold("PEER_DISCONNECTED")
            accept = self._accept()
            return {"phase": self.phase, "coordinator_phase": self.coordinator.phase,
                "presentation_phase": self.presentation.phase, "surface_phase": self.surface.phase,
                "input_phase": self.inputs.state, "accept_planning_intents": accept,
                "attempt": self.binding.attempt, "attachment": self.binding.attachment,
                "hold_reason": self.hold_reason,
                "new_recovery_cover_required": self.phase == "HELD" and self.surface.phase == "RELEASED",
                "fresh_native_gate_required": self.phase == "HELD" and self.inputs.state == "OPEN",
                "evidence_source": "SYNTHETIC_FIXTURE", "synthetic_only": True,
                "native_gameplay_enabled": False, "native_input_interception_implemented": False,
                "native_visual_cover_implemented": False, "real_game_access": False}

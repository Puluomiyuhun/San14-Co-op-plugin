"""Isolated presentation-surface contract; no process, window or native API access.

This is NOT the room/checkpoint controller or a native renderer. The caller owns
identity/world verification, durable load intent, and an independent native input
gate. A future renderer must truthfully acknowledge successful, non-test,
non-occluded presentation of each ticket. A bare Present invocation is not proof.

Frozen pixels remain a *picture* of the old map; its game objects may be gone.
"""
from dataclasses import dataclass
from hashlib import sha256


class SurfaceError(ValueError):
    pass


@dataclass(frozen=True)
class Frame:
    width: int
    height: int
    rgb: bytes
    revision: str

    def __post_init__(self):
        if type(self.width) is not int or type(self.height) is not int:
            raise SurfaceError("integer dimensions required")
        if not 1 <= self.width <= 8192 or not 1 <= self.height <= 8192:
            raise SurfaceError("frame dimensions outside isolated contract")
        if type(self.rgb) is not bytes or len(self.rgb) != self.width*self.height*3:
            raise SurfaceError("immutable packed RGB frame required")
        if not isinstance(self.revision, str) or not self.revision:
            raise SurfaceError("source revision required")

    @property
    def digest(self):
        return sha256(self.rgb).hexdigest()


@dataclass(frozen=True)
class Ticket:
    attempt: str
    serial: int
    frame: Frame
    overlay: str | None
    recovery_actions: tuple[str, ...] = ()


@dataclass(frozen=True)
class PresentationReceipt:
    ticket: Ticket
    # Backend must set PRESENTED only for a successful normal presentation.
    outcome: str
    source_sha256: str


class TransitionSurface:
    """One transition, deliberately single use and fail closed.

    begin -> successful paint ack -> native_started -> prepare_release using
    the controller's grant and verified new frame -> successful new-frame ack
    -> commit_release. Only commit_release clears this surface's input hold.
    The controller releases its independent native gate afterwards.
    """
    def __init__(self):
        self.phase = "IDLE"
        self.attempt = None
        self.frozen = None
        self.ticket = None
        self.available = True
        self._serial = 0
        self._painted = False
        self._grant = None
        self._began = False

    def _bind(self, attempt):
        if attempt != self.attempt or self.phase in ("IDLE", "RELEASED"):
            raise SurfaceError("wrong attempt or inactive surface")

    def _publish(self, frame, message, actions=()):
        self._serial += 1
        self._painted = False
        self.ticket = Ticket(self.attempt, self._serial, frame, message, actions)
        return self.ticket

    @property
    def input_held(self):
        return self.phase not in ("IDLE", "RELEASED")

    @property
    def may_start_native(self):
        return self.phase == "ARMING" and self.available and self._painted

    def begin(self, attempt, frame, *, native_input_gate_ack):
        if self._began or self.phase != "IDLE":
            raise SurfaceError("surface cannot be reused")
        if not isinstance(attempt, str) or not attempt or not isinstance(frame, Frame):
            raise SurfaceError("attempt and captured frame required")
        if native_input_gate_ack is not True:
            raise SurfaceError("native input gate must already be held")
        self._began = True
        self.attempt, self.frozen, self.phase = attempt, frame, "ARMING"
        return self._publish(frame, "正在同步，当前画面暂时冻结")

    def acknowledge(self, receipt):
        if (not isinstance(receipt, PresentationReceipt) or not isinstance(receipt.ticket, Ticket)
                or receipt.ticket != self.ticket):
            raise SurfaceError("stale or unknown presentation receipt")
        self._bind(receipt.ticket.attempt)
        self._painted = False
        if not self.available or receipt.outcome != "PRESENTED":
            raise SurfaceError("surface was not actually presented")
        if receipt.source_sha256 != self.ticket.frame.digest:
            raise SurfaceError("renderer used the wrong source frame")
        self._painted = True
        return self.may_start_native

    def native_started(self, attempt):
        self._bind(attempt)
        if not self.may_start_native:
            raise SurfaceError("cannot tear down before frozen picture is presented")
        self.phase = "WAITING"

    def progress(self, attempt, message):
        self._bind(attempt)
        if self.phase != "WAITING" or not isinstance(message, str) or not message:
            raise SurfaceError("progress only while waiting")
        return self._publish(self.frozen, message)

    def native_state_seen(self, attempt, state_name):
        """State disappearance/phase 2 alone never releases the picture/input."""
        self._bind(attempt)
        if not isinstance(state_name, str):
            raise SurfaceError("state label required")
        return self.ticket

    def prepare_release(self, attempt, verified_frame, *, controller_grant):
        self._bind(attempt)
        if self.phase != "WAITING" or not self.available:
            raise SurfaceError("cannot prepare release in this phase")
        if (not isinstance(verified_frame, Frame) or not isinstance(controller_grant, str)
                or not controller_grant):
            raise SurfaceError("verified frame and controller grant required")
        # This opaque grant is NOT a proof of world or identity on its own.
        # The caller supplies it only after its independent verification.
        self._grant, self.phase = controller_grant, "REVEAL_PENDING"
        return self._publish(verified_frame, None)

    def commit_release(self, attempt, *, controller_grant):
        self._bind(attempt)
        if (self.phase != "REVEAL_PENDING" or not self.available
                or not self._painted or controller_grant != self._grant):
            raise SurfaceError("new verified frame has not been presented for this grant")
        self.phase = "RELEASED"
        return {"surface_released": True, "release_native_input_gate_next": True}

    def fail(self, attempt, message):
        self._bind(attempt)
        if not isinstance(message, str) or not message:
            raise SurfaceError("failure message required")
        self._grant, self.phase = None, "FAILED"
        return self._publish(self.frozen, "同步未完成："+message,
                             ("查看连接状态", "查看恢复说明"))

    def surface_lost(self, attempt):
        self._bind(attempt)
        ticket = self.fail(attempt, "画面层不可用，保持暂停，等待恢复")
        self.available = False
        return ticket

    def repaint_after_loss(self, attempt):
        self._bind(attempt)
        if self.phase != "FAILED" or self.available:
            raise SurfaceError("surface is not lost")
        self.available = True
        return self._publish(self.frozen, self.ticket.overlay, self.ticket.recovery_actions)

    def route_input(self, category):
        """Routing contract only; not an OS/game input interceptor."""
        if category not in ("gameplay", "recovery"):
            raise SurfaceError("unknown input category")
        if not self.input_held:
            return "FORWARD"
        if category == "recovery" and self.phase == "FAILED":
            return "HANDLE_RECOVERY_ONLY"
        return "CONSUME"

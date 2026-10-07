"""MapWaitGate bridge requiring independent, caller-trusted native/display proof.

No default provider and no native implementation. A WGC hash, visible HWND, or
helper token alone cannot create legal MapWaitGate or TransitionSurface proof.
The root owns the trust boundary when injecting a provider. Fixture providers
must be explicitly enabled, never silently treated as native implementations.
"""
from dataclasses import dataclass
import secrets
import time

from checkpoint_visual_client import (VisualClient, VisualError, CoverReceipt,
                                     PreparedReceipt, RevealReceipt, TargetBinding,
                                     require, hexid)


@dataclass(frozen=True)
class ProofRequest:
    challenge: str
    purpose: str
    session: str
    presentation: str
    checkpoint_id: str
    epoch: str
    target: TargetBinding
    attachment: str
    view: str
    viewer_force: int
    world_sha256: str | None
    surface: str
    frame: str
    pixel_sha256: str
    frame_time: int
    requested_monotonic_ns: int


@dataclass(frozen=True)
class NativeVisualEvidence:
    """A trusted adapter's assertions; this dataclass does not acquire evidence.

    The provider must verify target/room/boundary and prove native planning-map
    and input-barrier continuity across frame_time, as well as separately usable
    presentation. Attaching a label to helper output is not an implementation.
    """
    request: ProofRequest
    provenance: str
    input_blocked: bool
    display_usable: bool
    native_planning_map: bool
    native_attachment: str
    native_view: str
    native_force: int
    native_world_sha256: str
    connected: tuple[str, ...]
    epoch: str
    input_held_since: int
    map_stable_since: int
    observed_qpc100ns: int
    observed_monotonic_ns: int


class GateVisualBridge:
    def __init__(self, client: VisualClient, *, evidence_provider=None, allow_fixture_evidence=False):
        require(type(client) is VisualClient, 'Validated visual client required')
        require(evidence_provider is None or callable(evidence_provider), 'Evidence provider must be callable')
        require(type(allow_fixture_evidence) is bool, 'Explicit fixture mode required')
        self.client = client
        self.provider = evidence_provider
        self.allow_fixture_evidence = allow_fixture_evidence

    def _gate_state(self, gate, phase):
        from checkpoint_presentation import MapWaitGate
        require(type(gate) is MapWaitGate, 'Real MapWaitGate required')
        c = gate.coordinator
        with gate.lock, c.lock:
            require(gate.phase == phase and c.connected == {'A','B'}, 'Gate phase/room connection changed')
            require(self.client.binding is not None and
                    self.client.binding.attachment == gate.identity['attachments']['B'],
                    'Visual target is not this checkpoint guest')
            if phase == 'REVEALING':
                require(c.phase == 'PLANNING' and c.epoch == gate.release_epoch and
                        c.attachments['B'] == gate.new_attachment, 'Release epoch/attachment changed')
            else:
                gate._boundary()
                require(c.epoch == gate.identity['manifest']['epoch'], 'Checkpoint epoch changed')
            return (gate.nonce, gate.identity['checkpoint_id'], c.epoch,
                    gate.identity['scope']['bindings']['B']['force_id'],
                    gate.identity['manifest']['world_sha256'], gate.new_attachment)

    def _proof(self, gate, receipt, *, phase, purpose):
        require(self.provider is not None, 'Independent native/input/display evidence provider missing')
        require(type(receipt) in (CoverReceipt,PreparedReceipt), 'Expected cover/prepared receipt')
        allowed = ('COVERED',) if type(receipt) is CoverReceipt else ('PREPARED',)
        self.client.assert_current(receipt, allowed)
        state = self._gate_state(gate, phase)
        if type(receipt) is PreparedReceipt:
            require(receipt.attachment == state[5], 'Prepared frame is not restored attachment')
        request = ProofRequest(secrets.token_hex(16), purpose, self.client.session,
            state[0],state[1],state[2],self.client.binding,receipt.attachment,receipt.view,
            state[3],None if type(receipt) is CoverReceipt else state[4],
            receipt.surface,receipt.frame,receipt.sha256,receipt.capture_time,time.monotonic_ns())
        evidence = self.provider(request)
        require(type(evidence) is NativeVisualEvidence and evidence.request == request,
                'Missing/stale/foreign independent evidence')
        require(evidence.provenance == 'ROOT_TRUSTED_NATIVE_ADAPTER' or
                (self.allow_fixture_evidence and evidence.provenance == 'FIXTURE_ONLY'),
                'Fixture/untrusted provider cannot authorize native presentation')
        require(evidence.input_blocked is True and evidence.display_usable is True and
                evidence.native_planning_map is True, 'Input, native map or usable display unproved')
        require(evidence.native_attachment == request.attachment and evidence.native_view == request.view and
                type(evidence.native_force) is int and evidence.native_force == request.viewer_force and
                type(evidence.connected) is tuple and set(evidence.connected) == {'A','B'} and
                len(evidence.connected) == 2 and hexid(evidence.epoch) and evidence.epoch == request.epoch,
                'Independent native identity/room mismatch')
        require(hexid(evidence.native_world_sha256,64) and
                (request.world_sha256 is None or evidence.native_world_sha256 == request.world_sha256),
                'Independent world digest mismatch')
        require(all(type(v) is int and v > 0 for v in (evidence.input_held_since,
                evidence.map_stable_since,evidence.observed_qpc100ns,evidence.observed_monotonic_ns)) and
                evidence.input_held_since <= request.frame_time and
                evidence.map_stable_since <= request.frame_time <= evidence.observed_qpc100ns and
                evidence.observed_monotonic_ns >= request.requested_monotonic_ns,
                'Native evidence does not cover captured frame interval')
        # Provider may have waited. Recheck both independent state machines.
        self.client.assert_current(receipt, allowed)
        require(self._gate_state(gate,phase) == state, 'Boundary changed during evidence acquisition')
        return request

    def accept_cover(self, gate, receipt: CoverReceipt):
        proof = self._proof(gate,receipt,phase='WAITING_FOR_COVER',purpose='OLD_MAP_COVER')
        report = {'presentation':proof.presentation,'checkpoint_id':proof.checkpoint_id,
            'attachment':receipt.attachment,'frame':receipt.frame,'view':receipt.view,
            'surface':receipt.surface,'window_mode':proof.target.window_mode,
            'visible':True,'input_blocked':True}
        with gate.lock,gate.coordinator.lock:
            self.client.assert_current(receipt,('COVERED',))
            self._gate_state(gate,'WAITING_FOR_COVER')
            gate.cover_presented(report)
        return report

    def accept_prepared(self, gate, receipt: PreparedReceipt):
        proof = self._proof(gate,receipt,phase='WAITING_FOR_MAP_FRAME',purpose='RESTORED_NATIVE_MAP')
        report = {'presentation':proof.presentation,'checkpoint_id':proof.checkpoint_id,
            'attachment':receipt.attachment,'frame':receipt.frame,'view':receipt.view,
            'surface':receipt.surface,'viewer_force':proof.viewer_force,'kind':'NATIVE_PLANNING_MAP',
            'window_mode':proof.target.window_mode,'cover_visible':True,'input_blocked':True}
        with gate.lock,gate.coordinator.lock:
            self.client.assert_current(receipt,('PREPARED',))
            self._gate_state(gate,'WAITING_FOR_MAP_FRAME')
            gate.map_frame_presented(report)
        return report

    def reveal(self, gate, grant):
        """Caller already called gate.begin_reveal with current host/guest proof.

        A disconnect during helper I/O prevents gate.revealed and holds the gate.
        The pixels might already have been uncovered; the external native input
        barrier must remain closed. This module does not re-cover/reload/retry.
        """
        require(type(grant) is dict and set(grant) == {'presentation','checkpoint_id','token','attachment'},
                'Exact MapWaitGate reveal grant required')
        prepared = self.client.prepared_receipt
        self._proof(gate,prepared,phase='REVEALING',purpose='BEFORE_REVEAL')
        with gate.lock,gate.coordinator.lock:
            self._gate_state(gate,'REVEALING')
            require(grant == {'presentation':gate.nonce,'checkpoint_id':gate.identity['checkpoint_id'],
                    'token':gate.reveal_token,'attachment':gate.new_attachment} and hexid(grant['token']),
                    'Foreign or stale gate reveal grant')
        try:
            receipt = self.client.reveal(prepared,controller_grant=grant['token'])
            with gate.lock,gate.coordinator.lock:
                self.client.assert_current(receipt,('REVEALED',))
                self._gate_state(gate,'REVEALING')
                require(receipt.attachment == grant['attachment'] and
                        receipt.controller_grant == grant['token'], 'Reveal acknowledgement mismatch')
                gate.revealed(dict(grant))
            return receipt
        except BaseException:
            gate.hold('VISUAL_RELEASE_NOT_CONFIRMED')
            raise

    @staticmethod
    def transition_surface_receipt(*args, **kwargs):
        """The helper does not transmit immutable RGB or prove non-occlusion.

        Therefore it cannot implement TransitionSurface.Frame/PresentationReceipt
        as-is. Do not substitute a hash-only dummy Frame or label WGC PRESENTED.
        """
        raise VisualError('TransitionSurface needs separately supplied real RGB and trusted presentation evidence')

"""One-command offline integration diagnostic. NEVER attaches to SAN14.

Real: workspace checkpoint bytes, journal, staging, owned child, named pipe,
Session hooks/receipts. Synthetic: game functions, initial world/input/visual
evidence. Missing final world evidence MUST keep the real controller blocked.
This is not a playable mod, nor a performance benchmark of native game loading.
"""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'outputs' / 'san14-link'
sys.path.insert(0, str(OUT))

from authoritative_sync import (scope_from_room, PeriodCoordinator, CheckpointPackage,
                                CheckpointReceiver, canonical, digest)
from checkpoint_journal import CheckpointJournal
from checkpoint_presentation import MapWaitGate
from checkpoint_visual_client_test import FakeTransport, BINDING, fixture_evidence
from test_authoritative_sync import bound_room
from checkpoint_visual_client import VisualClient
from checkpoint_visual_client_bridge import GateVisualBridge
from checkpoint_guest_transition import GuestTransition, InputHold, WorldObservation
from checkpoint_session_native_port import (SessionNativePort, SessionProfile,
    HeldEvidence, WorldEvidence, RetainedEvidence, EvidencePending, FIXTURE)

ARCHIVE = HERE / 'checkpoint_push_archives' / '20261006-204306-581930' / 'mppush01.s14'
ARCHIVE_SHA = '88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
NODE = dict(year=203, month=8, day=11, phase='PLANNING_BOUNDARY')


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def approved_fixture_hash():
    approval = json.loads((OUT/'离线原型组件清单.json').read_text(encoding='utf-8'))
    require(approval['schema'] == 'san14.offline-prototype-components.v1' and
            approval['provenance'] == FIXTURE and approval['playable_mod'] is False,
            'Unsupported offline approval manifest')
    for name, expected in approval['runtime_sha256'].items():
        require(Path(name).name == name and file_sha(HERE/name) == expected,
                'Offline component changed after approval: '+name)
    for name, expected in approval['output_sha256'].items():
        require(Path(name).name == name and file_sha(OUT/name) == expected,
                'Offline shared module changed after approval: '+name)
    return approval['runtime_sha256']['checkpoint_session_ipc_fixture.exe']


class ArchiveFixture:
    """The copied archive is real; the model's semantic world is NOT game data."""
    def __init__(self, folder):
        raw = ARCHIVE.read_bytes()
        require(len(raw) == 274880 and hashlib.sha256(raw).hexdigest() == ARCHIVE_SHA,
                'Workspace archive is not the frozen supported copy')
        scope = scope_from_room(bound_room())
        model_hash = digest({'fixture_only': True, 'semantic_world_not_measured': True,
                             'copied_archive_sha256': ARCHIVE_SHA})
        self.c = PeriodCoordinator(scope, 'offline-archive-fixture.v1', model_hash,
                                   {'A': 'a'*32, 'B': 'b'*32}, {**NODE, 'day': 1})
        for player in ('A', 'B'):
            self.c.set_ready(player, self.c.epoch, True)
        self.c.begin_simulation(self.c.seal_inputs())
        cut = {k: self.c.seal[k] for k in ('sequence', 'prefix_sha256')}
        package = CheckpointPackage(scope, self.c.epoch, 1, cut, NODE,
            self.c.state_contract, model_hash,
            {'world.s14': raw, 'adapter.json': canonical({'fixture_only': True,
                'viewer_force': 2, 'native_gameplay_enabled': False})}, source_player='A')
        self.c.offer_checkpoint('A', package.manifest)
        receiver = CheckpointReceiver(package.manifest, package.checkpoint_id,
                                     scope, self.c.epoch, 1, cut)
        chunks = list(package.chunks())
        for chunk in reversed(chunks):
            receiver.accept(chunk)
        self.chunk_count = len(chunks)
        self.j = CheckpointJournal(folder/'checkpoint.sqlite', scope, package.manifest,
            package.checkpoint_id, self.c.epoch, 1, cut, self.c.attachments, create=True)
        self.j.stage(receiver)
        self.c.received('B', self.c.epoch, receiver)
        self.g = MapWaitGate(self.c, self.j)
        self.host = dict(attachment='a'*32, world_sha256=model_hash, node=deepcopy(NODE))
        self.old = dict(attachment='b'*32, viewer_force=2, safe_boundary=True)


class InitialOnlyFixtureEvidence:
    """Deliberate test double. It cannot certify a restored world or release."""
    provenance = FIXTURE
    def __init__(self, fixture):
        self.fixture = fixture
        self.calls = []

    def hold_input(self, request):
        self.calls.append('synthetic_initial_hold')
        return HeldEvidence(request, InputHold(request.binding.context, '2'*32,
            request.binding.target.attachment, True), True, time.monotonic_ns())

    def observe(self, request):
        if request.purpose == 'RESTORED_WORLD':
            self.calls.append('missing_real_world_proof')
            raise EvidencePending('No complete game world/input/planning provider in offline prototype')
        self.calls.append('synthetic_initial_world')
        observation = WorldObservation(request.binding.lease, deepcopy(self.fixture.host),
            deepcopy(self.fixture.old), True, True, request.binding.context.state_contract, 0)
        return WorldEvidence(request, observation, True, '3'*32, True, True, time.monotonic_ns())

    def release_input(self, request):
        self.calls.append('UNEXPECTED_RELEASE')
        raise RuntimeError('Offline prototype cannot authorize input release')

    def retain(self, request):
        self.calls.append('synthetic_hold_retained')
        return RetainedEvidence(request, True, True, time.monotonic_ns())


def run():
    # Import the explicitly offline launcher only. No live-game module is loaded.
    from checkpoint_test_bootstrap import WorkspaceFixtureBootstrap
    folder = HERE/'checkpoint_offline_prototype_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    result = dict(schema='san14.offline-prototype-diagnostic.v1', provenance=FIXTURE,
        result='FAILED', game_accessed=False, playable_mod=False,
        actual_components=['checkpoint_chunk_validation', 'durable_journal',
            'workspace_file_staging', 'owned_child_process', 'bound_named_pipe',
            'native_session_dispatch_and_receipts'],
        synthetic_components=['native_game_function_bodies', 'initial_world_and_input_evidence',
            'visual_transport_and_window_handle'],
        missing=['real_game_input_hold_and_release', 'full_world_native_validation',
            'real_game_planning_and_frame_attribution', 'two_machine_playable_integration'],
        checks={}, elapsed_ms={}, source_sha256={})
    checks = result['checks']
    flow = port = bootstrap = client = fixture = None
    try:
        approved_sha = approved_fixture_hash()
        fixture = ArchiveFixture(folder)
        profile = SessionProfile(FIXTURE, 'san14.cc63-native-session.v1',
            fixture.g.identity['scope']['profile']['game_sha256'],
            approved_sha,
            file_sha(HERE/'checkpoint_guest_native_session.h'), fixture.c.state_contract,
            'svdexccSC03.s14', 274880, ARCHIVE_SHA, digest(NODE), 2)
        bootstrap = WorkspaceFixtureBootstrap(profile=profile, manifest=fixture.g.identity['manifest'],
                                               approved_fixture_sha256=profile.session_binary_sha256)
        started = time.monotonic_ns()
        prepared = bootstrap.prepare_fixture()
        result['elapsed_ms']['prepare_owned_child'] = (time.monotonic_ns()-started)/1e6
        # The handle is only a test token passed to FakeTransport, never an OS HWND.
        require(prepared['has_window'] is False and prepared['provenance'] == FIXTURE,
                'Unexpected prepared fixture type')
        target = replace(BINDING, pid=prepared['pid'], birth=prepared['birth'])
        native = InitialOnlyFixtureEvidence(fixture)
        port = SessionNativePort(fixture.g, approved_profile=profile,
            approved_profile_sha256=profile.sha256, native_provider=native,
            bootstrap_provider=bootstrap, allow_fixture_providers=True)
        visual = FakeTransport()
        client = VisualClient(visual, session='1'*32, timeout=2)
        bridge = GateVisualBridge(client, evidence_provider=fixture_evidence, allow_fixture_evidence=True)
        flow = GuestTransition(fixture.g, bridge, port, allow_fixture_native=True)
        print('1/4  工作区存档已分块校验；自有测试进程已启动。', flush=True)
        started = time.monotonic_ns()
        require(flow.start(target)['phase'] == 'LOADING', 'Controller did not enter LOADING')
        result['elapsed_ms']['stage_bind_and_arm'] = (time.monotonic_ns()-started)/1e6
        checks['durable_intent_before_native_arm'] = fixture.j.status()['status'] == 'INTENT'
        ep = bootstrap.channel.endpoint
        checks['exact_process_attempt_intent_binding'] = (
            ep.server_pid == prepared['pid'] and ep.server_birth == prepared['birth'] and
            ep.attempt.hex() == flow.context.attempt and ep.intent.hex() == flow.permit['intent'])
        print('2/4  存档已落盘；通过真实管道提交一次加载请求。', flush=True)
        deadline = time.monotonic()+15
        identity_started = time.monotonic_ns()
        while time.monotonic() < deadline:
            status = flow.poll()
            if port.last_session and port.last_session.fields['identity_ready']:
                break
            time.sleep(.02)
        require(port.last_session and port.last_session.fields['identity_ready'] == 1,
                'Native fixture identity receipt timed out')
        result['elapsed_ms']['fixture_receipts_only_not_game_load'] = (time.monotonic_ns()-identity_started)/1e6
        native_status = dict(port.last_session.fields)
        checks['native_bytes_lifecycle_identity_receipts'] = all(native_status[k] == 1
            for k in ('bytes_ready', 'lifecycle_ready', 'identity_ready'))
        checks['identity_not_promoted_to_complete'] = (
            status['phase'] == 'LOADING' and not status['accept_planning_intents'] and
            fixture.j.status()['status'] == 'INTENT' and not port.completed)
        checks['no_visual_reveal_or_input_release'] = (
            'reveal' not in [r['op'] for r in visual.sent] and 'UNEXPECTED_RELEASE' not in native.calls)
        result['native_identity_snapshot'] = native_status
        result['identity_is_not_load_complete'] = True
        print('3/4  已收到字节、加载生命周期、刘备身份收据；仍等待完整世界验证。', flush=True)
        with flow.lock:
            flow._hold('OFFLINE_PROTOTYPE_MISSING_REAL_WORLD_INPUT_PROVIDERS')
        flow.poll()
        checks['stop_retains_observation_without_second_arm'] = (
            flow.phase == 'HELD' and port.last_session.fields['stop_requested'] == 1 and
            port.last_session.fields['hooks_restored'] == 0 and
            bootstrap.channel.status()['arm_consumed'])
        try:
            flow.start(target)
        except Exception:
            checks['duplicate_transition_rejected'] = True
        else:
            checks['duplicate_transition_rejected'] = False
        checks['hold_has_no_cleanup_errors'] = not flow.cleanup_errors and not port.status()['errors']
        checks['no_visual_reveal_or_input_release'] = (
            'reveal' not in [r['op'] for r in visual.sent] and 'UNEXPECTED_RELEASE' not in native.calls)
        require(all(checks.values()), 'One or more integration checks failed')
        result.update(result='PASS_EXPECTED_HOLD', controller=flow.status(),
                      journal_status=fixture.j.status()['status'], chunk_count=fixture.chunk_count,
                      native_provider_calls=list(native.calls))
        print('4/4  正确停在等待状态，没有开放操作或重复加载。', flush=True)
    except Exception as exc:
        # Do not print child stdout/endpoint objects: they contain the pipe secret.
        result['error_type'] = type(exc).__name__
        if flow and flow.phase not in ('NEW', 'HELD'):
            with flow.lock:
                flow._hold('OFFLINE_PROTOTYPE_DIAGNOSTIC_FAILED')
        if flow:
            result['controller'] = flow.status()
        if fixture:
            result['journal_status'] = fixture.j.status()['status']
        print('诊断失败：'+type(exc).__name__+'。请保留诊断报告。', flush=True)
    finally:
        if client:
            try:
                client.terminate_helper(accept_cover_loss=True)
            except Exception as exc:
                result.setdefault('cleanup_errors', []).append(type(exc).__name__)
        if bootstrap:
            try:
                cleanup = bootstrap.close()
                result['bootstrap_cleanup'] = cleanup
                if cleanup['close_errors'] or not cleanup['closed'] or (
                        cleanup['prepared'] is not None and cleanup['exit_code'] is None):
                    result.setdefault('cleanup_errors', []).append('OwnedFixtureCleanupUnconfirmed')
            except Exception as exc:
                result.setdefault('cleanup_errors', []).append(type(exc).__name__)
        for name in ('checkpoint_offline_prototype.py','checkpoint_test_bootstrap.py',
            'checkpoint_session_native_port.py','checkpoint_guest_transition.py',
            'checkpoint_session_channel.py','checkpoint_guest_native_session.cpp',
            'checkpoint_guest_native_session.h','checkpoint_session_ipc_fixture.cpp',
            'checkpoint_session_ipc_fixture.exe'):
            if (HERE/name).is_file():
                result['source_sha256'][name] = file_sha(HERE/name)
        result['imported_dependency_sha256'] = {}
        for name in ('authoritative_sync','checkpoint_journal','checkpoint_presentation',
                     'checkpoint_visual_client','checkpoint_visual_client_bridge',
                     'checkpoint_visual_client_test','test_authoritative_sync','room_session'):
            module = sys.modules[name]
            path = Path(module.__file__).resolve()
            result['imported_dependency_sha256'][name] = dict(path=str(path), sha256=file_sha(path))
        if result.get('cleanup_errors'):
            result['result'] = 'FAILED_CLEANUP'
        raw = json.dumps(result, ensure_ascii=False, indent=2)
        (folder/'result.json').write_text(raw, encoding='utf-8')
        (OUT/'离线原型最近诊断.json').write_text(raw, encoding='utf-8')
    print('结果：'+result['result']+'。这验证装配链路，不代表游戏可联机。', flush=True)
    print('报告：'+str(OUT/'离线原型最近诊断.json'), flush=True)
    return 0 if result['result'] == 'PASS_EXPECTED_HOLD' else 1


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    print('三国志14联机：离线装配诊断（不访问游戏、不修改游戏存档）', flush=True)
    raise SystemExit(run())

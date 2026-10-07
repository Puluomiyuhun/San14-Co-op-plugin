"""Loopback TLS room -> verified archive -> owned C++ Session/planning fixture.

No game access. Initial boundary/world observations are fixture values; original
game function bodies in the child are doubles. Never completes a world receipt.
"""
from copy import deepcopy
from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
from pathlib import Path
import secrets
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1]/'outputs'/'san14-link'
sys.path.insert(0, str(OUT))
from checkpoint_room_progress import ProgressRoom
from checkpoint_room_client import RoomConnection
from checkpoint_host_export_reader import load_reviewed_host_export
from room_transport import Client, Server, make_certificate
from authoritative_sync import CheckpointPackage, CheckpointReceiver, PeriodCoordinator, scope_from_room, SyncError
from checkpoint_transfer import receive_checkpoint
from checkpoint_journal import CheckpointJournal, LoadHeld
from checkpoint_admitted_runtime_client import RuntimeFixture, RuntimeFixtureError
from checkpoint_admitted_receipt import classify, ReceiptRejected

APPROVED_EXE = '2ff9fb6080617a2d960609b2853423808c747e853695476a33d59f610fd63bc5'
APPROVED_HANDOFF = '738d7221177d7848a3dcd5916702db300e2ed75a0ad7c47694d24f023a21a7f3'
ARCHIVE = HERE/'checkpoint_push_archives/20261006-204306-581930/mppush01.s14'
ARCHIVE_SHA = '88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
CASES = ('success', 'corrupt-transfer', 'control-disconnect', 'planning-not-ready',
         'disconnect-after-download', 'disconnect-after-bind', 'progress-reply-lost',
         'input-pending-at-entry', 'input-pending-during-original')


class ControlBoundaryLost(RuntimeError):
    pass


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def denied(callback, expected):
    try:
        callback()
    except expected:
        return True
    raise RuntimeError('A one-shot operation was accepted twice')


def check_sources():
    """Pin to independently tested handoff, not to the currently found binary."""
    raw = (HERE/'checkpoint_admitted_runtime_handoff.json').read_bytes()
    require(hashlib.sha256(raw).hexdigest()==APPROVED_HANDOFF, 'Tested runtime handoff changed')
    h = json.loads(raw)
    require(h['fixture_binary_sha256'] == APPROVED_EXE, 'Runtime handoff does not match integrated approval')
    require(hashlib.sha256((HERE/'checkpoint_admitted_runtime_fixture.exe').read_bytes()).hexdigest() == APPROVED_EXE,
            'Runtime executable changed')
    for name, sha in h['source_sha256'].items():
        require(Path(name).name == name and hashlib.sha256((HERE/name).read_bytes()).hexdigest() == sha,
                'Runtime dependency changed: '+name)
    require(hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == ARCHIVE_SHA, 'Workspace archive changed')
    require(hashlib.sha256((HERE/'checkpoint_host_export_reader.py').read_bytes()).hexdigest()==
        '3713127f37aff8b252212e471cd0885ce40f5677d2bbfe326e782f741ce9717d', 'Reviewed host export reader changed')


class TrackingServer(Server):
    """Wait for owned handlers too, not merely the accepting thread."""
    def __init__(self, *args):
        self.active_handlers = 0
        self.handlers_changed = threading.Condition()
        super().__init__(*args)

    def process_request(self, request, address):
        with self.handlers_changed:
            self.active_handlers += 1
        try:
            super().process_request(request, address)
        except BaseException:
            with self.handlers_changed:
                self.active_handlers -= 1
                self.handlers_changed.notify_all()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            with self.handlers_changed:
                self.active_handlers -= 1
                self.handlers_changed.notify_all()

    def wait_handlers(self):
        with self.handlers_changed:
            return self.handlers_changed.wait_for(lambda: self.active_handlers == 0, timeout=5)


class FaultChannel:
    """Network-only fault injection; never changes the trusted source package."""
    def __init__(self, service, corrupt):
        self.service = service
        self.corrupt = corrupt

    def authenticate(self, *args): return self.service.authenticate(*args)
    def disconnect(self, *args): return self.service.disconnect(*args)

    def handle(self, *args):
        reply = self.service.handle(*args)
        if self.corrupt and reply.get('ok'):
            reply = deepcopy(reply)
            raw = reply['chunk']['data']
            reply['chunk']['data'] = ('A' if raw[0] != 'A' else 'B')+raw[1:]
            self.corrupt = False
        return reply


class DiagnosticRoom(ProgressRoom):
    """Own fixture can drop exactly one advisory reply; it never retries it."""
    def __init__(self,manifest,drop_progress_reply=False):
        super().__init__(manifest)
        self.drop_progress_reply=drop_progress_reply

    def handle(self,player,connection_id,request):
        reply=super().handle(player,connection_id,request)
        if self.drop_progress_reply and request.get('action')=='checkpoint_progress' and \
                request.get('stage')=='LOAD_REQUESTED' and reply.get('ok'):
            self.drop_progress_reply=False
            raise EOFError('Own fixture drops advisory reply after recording progress')
        return reply


def run(case='success', *, folder=None):
    require(case in CASES, 'Unknown fixture case')
    check_sources()
    folder = folder or HERE/'checkpoint_admitted_connected_prototype_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    report = dict(schema='san14.admitted-connected-prototype.v1', case=case, provenance='FIXTURE_ONLY',
        result='RUNNING', game_access=False, native_gameplay_enabled=False, full_world_verified=False,
        actual_two_games=False, original_game_functions='TEST_DOUBLES',
        initial_boundary_observations='SYNTHETIC_FIXTURE_ONLY', listeners_loopback_only=True,
        archive_sha256=ARCHIVE_SHA, runtime_approved_sha256=APPROVED_EXE, stages=[])
    servers, clients = [], []
    runtime = service = journal = room = None
    started = time.perf_counter()
    progress_sequence=0
    report['host_progress_history']=[]

    def start_server(owner):
        server = TrackingServer(('127.0.0.1', 0), owner, cert, key)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval':.05}, daemon=True)
        servers.append((server, thread));thread.start()
        return server.server_address[1]

    def connect(port, method, credential):
        connection_type=Client if method=='checkpoint_download' else RoomConnection
        client = connection_type('127.0.0.1', port, fingerprint,
            dict(method=method, credential=credential, profile=room.manifest['profile']))
        clients.append(client)
        return client

    def post_progress(stage,amount,reason='NONE'):
        nonlocal progress_sequence
        packet=dict(action='checkpoint_progress',checkpoint_id=package.checkpoint_id,epoch=c.epoch,
            sequence=progress_sequence+1,stage=stage,received_bytes=amount,intent=c.load_intent,reason=reason)
        reply=b.request(packet)
        require(reply['ok'],'Guest progress rejected')
        progress_sequence+=1
        host=a.request({'action':'status'})['state']['guest_progress']
        require(host==reply['guest_progress'] and host['grants_permission'] is False and
                host['full_world_verified'] is False,'Host did not observe bounded guest progress')
        report['host_progress_history'].append(host)

    def disconnect_guest():
        b.close()
        until = time.monotonic()+3
        while True:
            with room.lock: disconnected = room.players['B']['connection'] is None
            if disconnected:return
            require(time.monotonic()<until, 'Guest disconnect was not observed')
            threading.Event().wait(.005)

    @contextmanager
    def control_boundary():
        # Only the connection state observed by this owner is atomic with ARM.
        # This is NOT a continuous native input/disconnect barrier.
        with room.lock, c.lock:
            current = {p:row['connection'] for p,row in room.players.items()}
            if current != original_connections:
                for p in ('A','B'):
                    if current[p] != original_connections[p]:c.connection(p,False)
                raise ControlBoundaryLost('Original room connection lost before native dispatch')
            if scope_from_room(room) != scope or c.connected != {'A','B'}:
                raise ControlBoundaryLost('Room scope or coordinator connection changed')
            yield

    try:
        host_export=load_reviewed_host_export()
        report['host_export']=host_export.receipt
        room = DiagnosticRoom(json.loads((OUT/'房间势力目录.json').read_text(encoding='utf-8')),
                              drop_progress_reply=case=='progress-reply-lost')
        cert, key, fingerprint = make_certificate(folder/'tls')
        port = start_server(room)
        a = connect(port, 'host', room.host_token)
        b = connect(port, 'join', room.invite)
        for client, force in ((a,12), (b,2)):
            require(client.request(dict(action='select_force', force_id=force,
                request_id=secrets.token_hex(16), expected_revision=room.revision))['ok'], 'Faction selection failed')
        for client in (a,b):
            require(client.request(dict(action='confirm_force', request_id=secrets.token_hex(16),
                expected_revision=room.revision))['ok'], 'Faction confirmation failed')
        report['stages'].append('TWO_CONTROL_CONNECTIONS_AND_FACTIONS_CONFIRMED')
        scope = scope_from_room(room)
        original_connections = {p:row['connection'] for p,row in room.players.items()}
        attachments = {p:secrets.token_hex(16) for p in ('A','B')}
        node = dict(year=203, month=8, day=1, phase='PLANNING_BOUNDARY')
        # Model only: this does not execute a real battle or certify a full-world hash.
        world_sha = hashlib.sha256(b'san14.connected-prototype.fixture-world.v1').hexdigest()
        c = PeriodCoordinator(scope, 'fixture-world-not-production.v1', world_sha, attachments, node)
        room.bind_coordinator(c)
        for client in (a,b):
            require(client.request(dict(action='period_ready',epoch=c.epoch,ready=True))['ok'], 'Network ready failed')
        c.begin_simulation(c.seal_inputs())
        cut = {k:c.seal[k] for k in ('sequence','prefix_sha256')}
        package = CheckpointPackage(scope, c.epoch, c.period, cut, {**node,'day':11}, c.state_contract,
            world_sha, host_export.parts_for_archive_replay({**node,'day':11}), source_player='A')
        c.offer_checkpoint('A', package.manifest)
        service = room.install_offered_checkpoint(c, package)
        total_bytes=sum(part['size'] for part in package.manifest['parts'].values())
        post_progress('RECEIVING',0)
        artifact_port = start_server(FaultChannel(room.download_endpoint, case == 'corrupt-transfer'))
        offer = b.request(dict(action='checkpoint_download_offer', checkpoint_id=package.checkpoint_id))
        require(offer['ok'] and offer['manifest'] == package.manifest, 'Pinned checkpoint offer differs')
        download = connect(artifact_port, 'checkpoint_download', offer.pop('download_token'))
        receiver = CheckpointReceiver(package.manifest, package.checkpoint_id, scope, c.epoch, c.period, cut)
        journal = CheckpointJournal(folder/'guest.sqlite', scope, package.manifest, package.checkpoint_id,
            c.epoch, c.period, cut, attachments, create=True)
        if case == 'control-disconnect':
            disconnect_guest()
        transfer_start = time.perf_counter()
        if case in ('corrupt-transfer','control-disconnect'):
            denied(lambda: receive_checkpoint(download, receiver, action='checkpoint_chunk'), (SyncError,))
            if case=='corrupt-transfer':post_progress('HELD',0,'TRANSFER_FAILED')
            require(journal.status()['status'] == 'EMPTY' and c.load_intent is None, 'Bad download reached native permission')
            report.update(result='PASS_TRANSFER_REJECTED_BEFORE_NATIVE', runtime_started=False,
                          native_arm_count=0, download_rejected=True)
            report['host_control_still_connected'] = a.request({'action':'status'})['ok']
            if case == 'corrupt-transfer':
                report['guest_control_still_connected'] = b.request({'action':'status'})['ok']
            require(report['host_control_still_connected'] and report.get('guest_control_still_connected',True),
                    'Artifact failure disconnected a control channel')
            report['stages'].append('INVALID_TRANSFER_REJECTED_NO_LOAD')
        else:
            transfer = receive_checkpoint(download, receiver, action='checkpoint_chunk', window=4)
            parts = transfer.pop('parts')
            received_export=json.loads(parts['adapter.json'])
            require(received_export==host_export.receipt and received_export['current_A_world_verified'] is False,
                    'Historical provenance changed during transfer')
            report['host_export_provenance_transferred']=True
            report['transfer'] = {**transfer,'loopback_elapsed_ms':round((time.perf_counter()-transfer_start)*1000,3)}
            report['control_channels_preserved_after_download'] = all(
                client.request({'action':'status'})['ok'] for client in (a,b))
            require(report['control_channels_preserved_after_download'], 'Download closed room control')
            report['stages'].append('ACTUAL_TLS_BYTES_VERIFIED_CONTROL_CONNECTIONS_PRESERVED')
            journal.stage(receiver);c.received('B',c.epoch,receiver)
            post_progress('STAGED',total_bytes)
            if case=='disconnect-after-download':disconnect_guest()
            with control_boundary():pass
            runtime_case = {'planning-not-ready':'report-state', 'input-pending-at-entry':'entry-pending',
                            'input-pending-during-original':'late-pending'}.get(case,'success-new')
            runtime = RuntimeFixture(approved_exe_sha256=APPROVED_EXE, case=runtime_case)
            identity = runtime.prepare()
            host_fixture = dict(attachment=attachments['A'], world_sha256=world_sha, node=package.manifest['node'])
            guest_fixture = dict(attachment=attachments['B'],viewer_force=2,safe_boundary=True)
            with control_boundary():
                intent = c.begin_guest_load('B',c.epoch)
                permit = journal.reserve_load(intent,host_fixture,guest_fixture)
            require(permit['native_load_permitted_once'], 'No durable one-shot permission')
            bound = runtime.bind(secrets.token_hex(16),permit['intent'],world_bytes=parts['world.s14'])
            require(bound['consumed_world_source']=='verified_workspace_stage', 'Received bytes were not bound')
            report['stages'].append('DURABLE_INTENT_AND_RECEIVED_BYTES_BOUND_TO_OWN_CHILD')
            post_progress('LOAD_REQUESTED',total_bytes)
            if case=='disconnect-after-bind':disconnect_guest()
            with control_boundary():runtime.arm_once()
            receipt = runtime.wait_result()
            report['runtime_receipt']=receipt
            try:
                verdict = classify(receipt,binding=runtime.binding,fixture_case=runtime_case,
                                   archive_sha256=ARCHIVE_SHA,archive_size=len(parts['world.s14']))
            except ReceiptRejected as exc:
                report['receipt_rejected']=str(exc)
                post_progress('HELD',total_bytes,'LOAD_UNCERTAIN')
                raise
            report['runtime_classification']=verdict
            if verdict['outcome']=='ADMISSION_REJECTED':
                post_progress('HELD',total_bytes,'LOAD_UNCERTAIN')
            else:
                post_progress('IDENTITY_RESTORED',total_bytes)
                if verdict['outcome']=='WAITING_WORLD':
                    post_progress('WAITING_WORLD',total_bytes,'WORLD_PROVIDER_MISSING')
                else:post_progress('HELD',total_bytes,'WAITING_PLANNING')
            require(denied(runtime.arm_once,(RuntimeFixtureError,)) and
                denied(lambda:journal.reserve_load(intent,host_fixture,guest_fixture),(LoadHeld,)),
                'Duplicate load was not blocked')
            reopened = CheckpointJournal(folder/'guest.sqlite',scope,package.manifest,package.checkpoint_id,
                c.epoch,c.period,cut,attachments)
            denied(lambda:reopened.reserve_load(intent,host_fixture,guest_fixture),(LoadHeld,))
            require(journal.status()['status']=='INTENT' and c.phase=='RECONCILING',
                    'Partial receipt incorrectly enabled next period')
            report.update(runtime_receipt=receipt, runtime_started=True, native_arm_count=1,
                duplicate_arm_rejected=True, duplicate_journal_intent_rejected=True,
                reopened_journal_replay_rejected=True,
                result={'WAITING_WORLD':'PASS_EXPECTED_WAIT_FOR_GAME_PROVIDERS',
                        'WAITING_PLANNING':'PASS_PLANNING_NOT_READY_HELD',
                        'ADMISSION_REJECTED':'PASS_PLAYER_INPUT_BLOCKED_LOAD'}[verdict['outcome']])
            report['stages'].append({'WAITING_WORLD':'SESSION_IDENTITY_AND_PLANNING_OBSERVED',
                'WAITING_PLANNING':'REPORT_SCREEN_STILL_HELD',
                'ADMISSION_REJECTED':'PLAYER_INPUT_RETAINED_NO_LOAD_QUEUE'}[verdict['outcome']])
            report['control_channels_preserved_after_native'] = all(client.request({'action':'status'})['ok'] for client in (a,b))
            require(report['control_channels_preserved_after_native'], 'Runtime altered room controls')
        report['journal'] = journal.status()
        report['coordinator'] = c.status()
    except ControlBoundaryLost as exc:
        expected = case in ('disconnect-after-download','disconnect-after-bind')
        state = runtime.status() if runtime else None
        no_arm = state is None or not state['arm_consumed']
        report.update(result='PASS_DISCONNECT_BEFORE_ARM_HELD' if expected and no_arm else 'FAIL',
            connection_error=str(exc),runtime_started=runtime is not None,native_arm_count=0 if no_arm else 1,
            observed_disconnect_blocks_arm=no_arm,journal=journal.status(),coordinator=c.status())
        report['stages'].append('OBSERVED_DISCONNECT_BEFORE_ARM_HELD')
    except BaseException as exc:
        report.update(result='FAIL', error_type=type(exc).__name__, error=str(exc))
        if case=='progress-reply-lost' and isinstance(exc,(EOFError,OSError)) and runtime is not None:
            state=runtime.status()
            if state['phase']=='BOUND' and not state['arm_consumed'] and journal.status()['status']=='INTENT':
                try:
                    host=a.request({'action':'status'})['state']
                    require(host['guest_progress']['stage']=='LOAD_REQUESTED' and
                            host['guest_progress']['grants_permission'] is False and
                            c.connected=={'A'},'Lost advisory reply did not leave the room held')
                    report.update(result='PASS_PROGRESS_REPLY_LOST_NO_ARM',native_arm_count=0,
                        runtime_started=True,diagnostic_reply_lost=True,host_observed_after_lost_reply=host['guest_progress'],
                        guest_connection_fault=b.status()['fault'],journal=journal.status(),coordinator=c.status())
                except Exception as verify_error:
                    report['verification_error']=str(verify_error)
    finally:
        cleanup_errors = []
        if runtime:
            try:
                report['runtime_cleanup'] = runtime.close()
                if report['runtime_cleanup']['errors'] or report['runtime_cleanup']['exit_code'] != 0:
                    cleanup_errors.append('OWN_RUNTIME_CLEANUP_FAILED')
            except Exception as exc:cleanup_errors.append(type(exc).__name__)
        if room:
            try:room.close_checkpoints()
            except Exception as exc:cleanup_errors.append(type(exc).__name__)
        for client in reversed(clients):
            try:client.close()
            except Exception as exc:cleanup_errors.append(type(exc).__name__)
        for server, thread in reversed(servers):
            try:
                server.shutdown();thread.join(timeout=5)
                if thread.is_alive() or not server.wait_handlers():cleanup_errors.append('LISTENER_OR_HANDLER_ALIVE')
                server.server_close()
            except Exception as exc:cleanup_errors.append(type(exc).__name__)
        report['cleanup_errors'] = cleanup_errors
        report['owned_resources_closed'] = not cleanup_errors
        report['total_elapsed_ms'] = round((time.perf_counter()-started)*1000,3)
        if cleanup_errors:report['result']='FAIL'
        save(folder/'result.json',report)
    return report, folder/'result.json'


def main():
    # Deliberately no game path, PID, remote address or arbitrary archive option.
    if len(sys.argv)!=1:
        print('This fixed offline diagnostic accepts no arguments.');return 2
    report, path = run()
    save(OUT/'输入检查接入诊断结果.json',report)
    print(report['result'])
    print('输入检查接入离线诊断：'+('通过' if report['result'].startswith('PASS_') else '未通过，请查看报告中的错误。'))
    print('不连接游戏；原游戏函数使用测试替身；尚不允许进入下一旬。')
    print('报告：'+str(OUT/'输入检查接入诊断结果.json'))
    return 0 if report['result'].startswith('PASS_') else 1


if __name__=='__main__':
    raise SystemExit(main())

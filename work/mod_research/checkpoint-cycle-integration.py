"""Synthetic multi-period lifecycle over local pinned TLS; zero game access.

Reuses research TestRoom artifact endpoints. Each transfer consumes one B
connection; B explicitly disconnects/resumes around it. This is NOT production
dual-channel transport, native game loading, or whole-room restart recovery.
"""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import json
import secrets
import sys
import tempfile
import threading
import time

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'outputs' / 'san14-link'
sys.path[:0] = [str(OUT), str(HERE), str(HERE / 'python_deps')]
from authoritative_sync import (CheckpointPackage, CheckpointReceiver, PeriodCoordinator,
    SyncError, canonical, digest, next_node, scope_from_room)
from checkpoint_journal import CheckpointJournal, LoadHeld
from checkpoint_transfer import receive_checkpoint
from room_transport import Server, Client, make_certificate
from test_checkpoint_tls import TestRoom


INITIAL_NODE = {'year': 203, 'month': 8, 'day': 11, 'phase': 'PLANNING_BOUNDARY'}


def initial_world():
    return {'schema': 'synthetic-world-not-san14.v1', 'node': deepcopy(INITIAL_NODE),
            'armies': {'1': {'force': 12, 'troops': 1300}, '2': {'force': 11, 'troops': 900}},
            'persons': {'10': {'force': 12, 'status': 'free'}, '11': {'force': 2, 'status': 'free'}},
            'cities': {'13': {'force': 2, 'gold': 5000}, '19': {'force': 12, 'gold': 6000}},
            'tiles': {str(i): {'owner': 12 if i % 2 else 2, 'fire': False} for i in range(800)},
            'tasks': [{'id': 1, 'kind': 'recruit', 'remaining_days': 5}], 'completed_periods': 0}


def host_step(world, period):
    world = deepcopy(world)
    world['node'] = next_node(world['node'])
    world['completed_periods'] = period
    victim = sorted(world['armies'])[0]
    del world['armies'][victim]
    world['armies'][str(2 + period)] = {'force': 2, 'troops': 1700 - 200 * period}
    del world['persons'][sorted(world['persons'])[0]]
    world['persons'][str(11 + period)] = {'force': 2, 'status': 'captured' if period == 1 else 'free'}
    world['tiles'][str(period)] = {'owner': 2, 'fire': period % 2 == 1}
    world['tasks'] = [{'id': 1 + period, 'kind': 'move', 'remaining_days': 7 - period}]
    world['cities']['13']['gold'] += 111 * period
    return world


def speculative_step(world, period):
    world = deepcopy(world)
    world['node'] = next_node(world['node'])
    world['completed_periods'] = period
    world['armies']['999'] = {'force': 12, 'troops': 42}
    world['persons']['999'] = {'force': 11, 'status': 'dead'}
    world['tiles'][str(period)] = {'owner': 11, 'fire': False}
    world['tasks'] = [{'id': 999, 'kind': 'wrong-local-outcome', 'remaining_days': 99}]
    world['cities']['13']['gold'] = 7
    return world


def main():
    run = HERE / 'checkpoint-cycle-runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True, exist_ok=False)
    assert run.resolve().is_relative_to(HERE.resolve())
    room_manifest = json.loads((OUT / '房间势力目录.json').read_text(encoding='utf-8'))
    room = TestRoom(room_manifest)
    checks = []; periods = []; transfer_handoffs = []; journals = []; attempt_counts = {}
    a = b = transfer = None; successful_replacements = 0
    with tempfile.TemporaryDirectory(prefix='tls-', dir=run) as tls_folder:
        cert, key, pin = make_certificate(tls_folder)
        with Server(('127.0.0.1', 0), room, cert, key) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            def connect(method, credential):
                return Client('127.0.0.1', server.server_address[1], pin,
                              {'method': method, 'credential': credential,
                               'profile': room_manifest['profile']})
            def wait_guest_disconnected():
                deadline = time.monotonic() + 3
                while a.request({'action': 'status'})['state']['players']['B']['connected']:
                    assert time.monotonic() < deadline, 'Test B did not disconnect'
                    time.sleep(.01)
            def reject(label, callback):
                try:
                    callback()
                except SyncError:
                    checks.append(label)
                else:
                    raise AssertionError('Expected rejection: ' + label)
            try:
                a = connect('host', room.host_token)
                b = connect('join', room.invite)
                for client, force in ((a, 12), (b, 2)):
                    state = client.request({'action': 'status'})['state']
                    assert client.request({'action': 'select_force', 'request_id': secrets.token_hex(16),
                        'expected_revision': state['revision'], 'force_id': force})['ok']
                for client in (a, b):
                    state = client.request({'action': 'status'})['state']
                    assert client.request({'action': 'confirm_force', 'request_id': secrets.token_hex(16),
                        'expected_revision': state['revision']})['ok']
                scope = scope_from_room(room)
                host = {'world': initial_world(), 'viewer_force': 12, 'attachment': 'a' * 32}
                guest = {'world': initial_world(), 'viewer_force': 2, 'attachment': 'b' * 32}
                c = PeriodCoordinator(scope, 'synthetic-all-records.v1', digest(host['world']),
                                      {'A': host['attachment'], 'B': guest['attachment']}, INITIAL_NODE)
                checks.append('native room remains WAITING_NATIVE_ADAPTER while fixture coordinator is separate')
                def host_observation():
                    return {'attachment': host['attachment'], 'world_sha256': digest(host['world']),
                            'node': deepcopy(host['world']['node'])}
                def guest_observation():
                    return {'attachment': guest['attachment'], 'viewer_force': guest['viewer_force'],
                            'world_sha256': digest(guest['world']), 'node': deepcopy(guest['world']['node']),
                            'safe_boundary': True}

                for period in (1, 2, 3):
                    assert c.period == period and c.phase == 'PLANNING'
                    assert host['world'] == guest['world']
                    # Synthetic planning command prefix crosses periods monotonically.
                    host['world']['planning_order'] = {'period': period, 'actor': 'B', 'target': 13}
                    guest['world'] = deepcopy(host['world'])
                    previous = deepcopy(c.reports['A'])
                    sequence = previous['sequence'] + 1
                    prefix = digest({'previous': previous['prefix_sha256'], 'sequence': sequence,
                                     'command': host['world']['planning_order']})
                    for player, replica in (('A', host), ('B', guest)):
                        c.applied_prefix(player, c.epoch, sequence, prefix,
                                         digest(replica['world']), replica['attachment'])
                        c.set_ready(player, c.epoch, True)
                    c.begin_simulation(c.seal_inputs())
                    old_attachments = deepcopy(c.attachments)
                    host['world'] = host_step(host['world'], period)
                    guest['world'] = speculative_step(guest['world'], period)
                    assert digest(host['world']) != digest(guest['world'])
                    divergent_guest_sha256 = digest(guest['world'])
                    cut = {'sequence': sequence, 'prefix_sha256': prefix}
                    package = CheckpointPackage(scope, c.epoch, period, cut, host['world']['node'],
                        c.state_contract, digest(host['world']),
                        {'world.s14': canonical(host['world']),
                         'adapter.json': canonical({'schema': 'synthetic-sidecar.v1',
                            'scope_sha256': digest(scope), 'epoch': c.epoch, 'cut': cut,
                            'guest_force': scope['bindings']['B']['force_id'], 'events': []})}, source_player='A')
                    c.offer_checkpoint('A', package.manifest)
                    with room.lock:
                        room.package = package

                    if journals:
                        old = journals[-1]
                        before = deepcopy(c.status())
                        reject('old journal cannot certify the currently different world in period ' + str(period),
                            lambda: old.apply_to_coordinator(c, host_observation(), guest_observation()))
                        assert c.status() == before
                        # Coordinator acknowledges an identical historical receipt only.
                        # That acknowledgment MUST NOT release this newer boundary.
                        assert c.loaded(**old.coordinator_arguments())['duplicate']
                        assert c.status() == before and c.phase == 'RECONCILING'
                        checks.append('historical loaded duplicate leaves period ' + str(period) + ' held')

                    # The existing Room supports one connection per seat. Deliberately
                    # replace B control with a one-transfer research connection.
                    token = b.resume_token; b.close(); b = None
                    c.connection('B', False); wait_guest_disconnected()
                    transfer = connect('resume', token); c.connection('B', True)
                    assert transfer.state['binding_epoch'] == scope['binding_epoch']
                    response = transfer.request({'action': 'test_checkpoint_manifest'})
                    assert response['ok'] and response['checkpoint_id'] == package.checkpoint_id
                    receiver = CheckpointReceiver(response['manifest'], response['checkpoint_id'],
                        scope, c.epoch, period, cut)
                    transfer_result = receive_checkpoint(transfer, receiver,
                        action='test_checkpoint_chunk', window=4)
                    assert transfer.stream is None and transfer.socket is None
                    c.connection('B', False); wait_guest_disconnected()
                    reject('cannot confirm transfer while B is disconnected, period ' + str(period),
                           lambda: c.received('B', c.epoch, receiver))
                    b = connect('resume', token); c.connection('B', True)
                    assert b.state['binding_epoch'] == scope['binding_epoch']
                    transfer_handoffs.append({'period': period, 'dedicated_transfer_consumed': True,
                        'resumed_before_continue': True, 'simultaneous_B_channels': False})
                    assert transfer_result['integrity_verified'] and not transfer_result['native_loaded']

                    path = run / (package.checkpoint_id + '.sqlite')
                    def open_journal(create=False):
                        return CheckpointJournal(path, scope, package.manifest, package.checkpoint_id,
                            package.manifest['epoch'], period, cut, old_attachments, create=create)
                    j = open_journal(True); j.stage(receiver); j = open_journal()
                    assert j.verified_parts() == transfer_result['parts']
                    c.received('B', c.epoch, receiver)
                    intent = c.begin_guest_load('B', c.epoch)
                    before_guest = {'attachment': guest['attachment'],
                                    'viewer_force': guest['viewer_force'], 'safe_boundary': True}
                    offered_epoch = c.epoch
                    captured_receipt = None
                    def fixture_load(permit, parts):
                        nonlocal successful_replacements, captured_receipt
                        assert open_journal().status()['native_outcome_unknown']
                        assert permit['intent'] == intent
                        attempt_counts[package.checkpoint_id] = attempt_counts.get(package.checkpoint_id, 0) + 1
                        if period == 3:
                            raise RuntimeError('synthetic crash/unknown outcome after durable load INTENT')
                        world = json.loads(parts['world.s14'])
                        sidecar = json.loads(parts['adapter.json'])
                        assert sidecar['scope_sha256'] == digest(scope)
                        assert sidecar['epoch'] == offered_epoch and sidecar['cut'] == cut
                        guest['world'] = world  # Full replacement, including added/deleted records.
                        guest['viewer_force'] = sidecar['guest_force']
                        guest['attachment'] = secrets.token_hex(16)
                        successful_replacements += 1
                        captured_receipt = {'player': 'B', 'epoch': offered_epoch,
                            'checkpoint_id': package.checkpoint_id, 'intent': intent,
                            'world_sha256': digest(guest['world']), 'viewer_force': guest['viewer_force'],
                            'attachment': guest['attachment'], 'host_observation': host_observation()}
                        return captured_receipt

                    if period < 3:
                        completion = j.invoke_once(intent, host_observation(), before_guest, fixture_load)
                        assert not completion['duplicate'] and completion['status'] == 'COMPLETED'
                        j = open_journal()
                        assert j.complete(captured_receipt)['duplicate']
                        assert canonical(guest['world']) == canonical(host['world'])
                        assert guest['viewer_force'] == 2 and host['viewer_force'] == 12
                        assert '999' not in guest['world']['armies'] and '999' not in guest['world']['persons']
                        applied = j.apply_to_coordinator(c, host_observation(), guest_observation())
                        assert not applied['duplicate'] and c.phase == 'PLANNING' and c.period == period + 1
                        assert c.reports['A'] == c.reports['B']
                        assert c.reports['A']['sequence'] == sequence and c.ready == set()
                        assert j.apply_to_coordinator(c, host_observation(), guest_observation())['duplicate']
                        checks.append('period ' + str(period) + ': full fixture replacement preserves B identity and next-period prefix')
                        assert attempt_counts[package.checkpoint_id] == 1
                        journals.append(j)
                    else:
                        try:
                            j.invoke_once(intent, host_observation(), before_guest, fixture_load)
                        except RuntimeError as error:
                            assert 'synthetic crash' in str(error)
                        else:
                            raise AssertionError('Third period did not fail as intended')
                        j = open_journal()
                        reject('third-period unresolved durable intent cannot invoke another fixture load',
                            lambda: j.invoke_once(intent, host_observation(), before_guest, fixture_load))
                        reject('third-period unknown result cannot emit a coordinator receipt', j.coordinator_arguments)
                        reject('third-period unknown result prevents B ready', lambda: c.set_ready('B', c.epoch, True))
                        reject('third-period unknown result prevents A ready', lambda: c.set_ready('A', c.epoch, True))
                        reject('third-period cannot allocate a second in-memory load intent',
                            lambda: c.begin_guest_load('B', c.epoch))
                        stale = journals[-1].coordinator_arguments()
                        stale['attachment'] = stale.pop('new_attachment')
                        reject('previous-period receipt cannot complete third-period durable intent', lambda: j.complete(stale))
                        assert attempt_counts[package.checkpoint_id] == 1
                        assert c.period == 3 and c.phase == 'RECONCILING'
                        assert j.status()['native_outcome_unknown'] and not c.ready

                    periods.append({'period': period, 'checkpoint_id': package.checkpoint_id,
                        'node': package.manifest['node'], 'cut': cut,
                        'host_world_sha256': digest(host['world']),
                        'guest_world_sha256_before_replacement': divergent_guest_sha256,
                        'guest_world_sha256': digest(guest['world']),
                        'guest_force': guest['viewer_force'],
                        'fixture_load_attempts': attempt_counts[package.checkpoint_id],
                        'journal_status': j.status()['status'],
                        'coordinator_phase_after': c.phase, 'coordinator_period_after': c.period,
                        'transport_chunks': transfer_result['chunks'],
                        'transport_bytes': transfer_result['received_bytes'],
                        'journal_file': str(path.relative_to(HERE))})

                state = b.request({'action': 'status'})['state']
                assert state['phase'] == 'WAITING_NATIVE_ADAPTER' and not state['native_gameplay_enabled']
                assert not c.status()['native_gameplay_enabled']
                assert successful_replacements == 2 and len(c.trace) == 2
                assert not c.status()['host_restart_recovery_implemented']
                checks.append('production Room never enables native gameplay or actual game loading')
                report = {'schema': 'san14.synthetic-checkpoint-cycle-integration.v1', 'result': 'PASS',
                    'transport': '127.0.0.1 pinned TLS against research TestRoom only',
                    'completed_fixture_periods': 2, 'third_period': 'DURABLE_INTENT_UNKNOWN_HELD',
                    'periods': periods, 'checks': checks, 'check_count': len(checks),
                    'connection_handoffs': transfer_handoffs,
                    'successful_fixture_replacements': successful_replacements,
                    'listener_stopped': False, 'game_processes_opened': 0,
                    'game_memory_writes': 0, 'game_files_read_or_written': 0,
                    'native_loads': 0, 'native_gameplay_enabled': False,
                    'native_full_world_coverage_verified': False,
                    'production_dual_channel_transport_implemented': False,
                    'host_restart_recovery_implemented': False,
                    'limits': ['All worlds, sidecars, safe-boundary observations and load callbacks are fixtures.',
                               'The real SAN14 process and user save slots were not accessed.',
                               'B disconnect/resume during transfer is test orchestration, not a completed production channel design.',
                               'Host/room restart and installation of saved bytes into the game remain unimplemented.']}
            finally:
                if a: a.close()
                if b: b.close()
                if transfer: transfer.close()
                server.shutdown(); thread.join(timeout=5)
                assert not thread.is_alive()
        report['listener_stopped'] = True
    (HERE / 'checkpoint-cycle-integration-results.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()

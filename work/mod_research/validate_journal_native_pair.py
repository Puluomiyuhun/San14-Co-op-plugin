"""Exercise the durable gate around isolated native reward calls.

Reuses a recorded input; never opens SAN14, reads live memory or injects a DLL.
Each fixture child executes copied native code, then exits. The Python adapter
retains its output sample. This is not two persistent native game clients.
"""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import secrets
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parents[1] / 'outputs' / 'san14-link'
sys.path.insert(0, str(OUT))
from execution_journal import (ExecutionJournal, ExecutionHeld, JournalError,
                               compare_applied_prefixes, make_intent, scope_from_room)
from authority_reward import validate_reward
from test_execution_journal import bound_room


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def normalized_initial(raw):
    """Exactly the existing normal-mode fixture dump coverage, not a full world."""
    assert struct.unpack_from('<I', raw)[0] == 0x1414FACE
    world = bytearray(raw[4:4+0x1700])
    world[:8] = b'\0' * 8
    world[0x3A] = 0
    out = bytearray(world)
    at = 4 + 0x1700
    count = struct.unpack_from('<I', raw, at)[0]
    at += 4
    assert count == 9
    for _ in range(count):
        at += 4
        out.extend(raw[at+8:at+0x200])
        at += 0x200
    for stride in (0x1D0, 0x28, 0x168, 0x20):
        for _ in range(52):
            out.extend(raw[at+8:at+stride])
            at += stride
    # Rank and linked-list input are used by the fixture but not in its output
    # sample. This limitation remains part of the coverage contract.
    at += 13 * 0xB8
    districts = struct.unpack_from('<I', raw, at)[0]
    assert at + 4 + 4 * districts == len(raw)
    return bytes(out)


class FixtureAdapter:
    def __init__(self, viewer, name, initial, folder, input_path):
        self.viewer, self.name, self.folder, self.input_path = viewer, name, folder, input_path
        self.sample = initial
        self.calls = 0
        self.results = []

    def observe(self):
        return sha(self.sample)

    def invoke(self):
        self.calls += 1
        output = self.folder / f'{self.name}-{self.calls}.bin'
        process = subprocess.run([str(ROOT/'identity_pair_fixture.exe'), str(self.input_path),
                                  str(self.viewer), 'normal', 'B', str(output)],
                                 capture_output=True, text=True, timeout=20,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
        assert process.returncode == 0, (process.returncode, process.stdout, process.stderr)
        result = json.loads(process.stdout)
        assert result['result'] == 'PASS' and result['native_reward_calls'] == 1
        assert result['local_identity_preserved'] and result['viewer'] == self.viewer
        assert result['gold_A'] == 83308 and result['actions_A'] == 18
        assert result['gold_B'] == 20504 and result['actions_B'] == 9
        assert result['loyalty_B'] == [97, 95, 100]
        self.sample = output.read_bytes()
        self.results.append(result)
        save(output.with_suffix('.json'), result)
        return result


def main():
    prior = read(ROOT/'identity-pair-results.json')
    source = Path(prior['directory'])
    input_path = source/'input.bin'
    raw = input_path.read_bytes()
    assert sha(raw) == prior['input']['sha256']
    initial = normalized_initial(raw)
    inputs = read(source/'authority-inputs.json')['2']
    preflight = validate_reward(inputs['command'], inputs['context'], 2)
    assert preflight['result'] == 'PRECHECK_PASS'
    room = bound_room()
    scope = scope_from_room(room, secrets.token_hex(16),
                            'identity-pair.normalized-sample.normal-mode.v1', sha(initial))
    binding = room.binding_for_command('B', {'room_id': room.room_id, 'binding_epoch': room.binding_epoch,
                                             'command': inputs['command']})
    assert binding['authorized_force_id'] == 2 and not binding['applied_to_game']
    intent = make_intent(scope, 1, 'B', secrets.token_hex(16), inputs['command'], sha(initial))
    folder = ROOT/'journal-native-pair-traces'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    save(folder/'scope.json', scope)
    save(folder/'intent.json', intent)
    adapters = {p: FixtureAdapter(v, p, initial, folder, input_path) for p, v in [('A', 12), ('B', 2)]}
    attachments = {p: secrets.token_hex(16) for p in adapters}
    journals = {p: ExecutionJournal(folder/f'{p}.sqlite', scope, p, attachments[p], create=True) for p in adapters}
    receipts = {}
    receipts['A'] = journals['A'].execute(intent, adapters['A'].observe, adapters['A'].invoke)
    try:
        compare_applied_prefixes(scope, 1, {p: j.report(adapters[p].observe) for p, j in journals.items()})
    except JournalError:
        slow_replica_held = True
    else:
        raise AssertionError('Unapplied B passed the prefix check')
    receipts['B'] = journals['B'].execute(intent, adapters['B'].observe, adapters['B'].invoke)
    assert adapters['A'].sample == adapters['B'].sample
    duplicate_receipts = []
    for p in adapters:
        reopened = ExecutionJournal(folder/f'{p}.sqlite', scope, p, attachments[p])
        for _ in range(3):
            receipt = reopened.execute(intent, adapters[p].observe, adapters[p].invoke)
            assert receipt['duplicate'] and not receipt['native_invoked']
            duplicate_receipts.append(receipt)
        assert adapters[p].calls == 1
    reports = {p: j.report(adapters[p].observe) for p, j in journals.items()}
    match = compare_applied_prefixes(scope, 1, reports)
    # Isolated failure after the real copied native body has returned. Known
    # fixture output does not authorize guessing that a game commit persisted.
    uncertain = FixtureAdapter(2, 'uncertain', initial, folder, input_path)
    attachment = secrets.token_hex(16)
    journal = ExecutionJournal(folder/'uncertain.sqlite', scope, 'B', attachment, create=True)
    def lose_result():
        uncertain.invoke()
        raise OSError('Injected loss between native effect and durable receipt')
    try:
        journal.execute(intent, uncertain.observe, lose_result)
    except ExecutionHeld:
        pass
    else:
        raise AssertionError('Lost result did not hold execution')
    reopened = ExecutionJournal(folder/'uncertain.sqlite', scope, 'B', attachment)
    try:
        reopened.execute(intent, uncertain.observe, uncertain.invoke)
    except ExecutionHeld:
        uncertain_retry_blocked = True
    else:
        raise AssertionError('Uncertain native call retried')
    assert uncertain.calls == 1
    # Rollback changes native state even if the room and command IDs are the same.
    adapters['B'].sample = initial
    try:
        journals['B'].execute(intent, adapters['B'].observe, adapters['B'].invoke)
    except ExecutionHeld:
        rollback_detected = True
    else:
        raise AssertionError('Old receipt trusted after rollback')
    report = {'schema': 'san14.durable-native-fixture-gate.v1', 'result': 'PASS',
              'created': datetime.now().astimezone().isoformat(), 'directory': str(folder),
              'recorded_input': {'path': str(input_path), 'sha256': sha(raw), 'sample_bytes': len(initial)},
              'room_phase': room.view('A')['phase'], 'binding': binding,
              'fixture_processes': 3, 'fixture_native_reward_calls': 3,
              'successful_pair_calls': {p: a.calls for p, a in adapters.items()},
              'duplicate_attempts_suppressed': len(duplicate_receipts),
              'slow_replica_held': slow_replica_held, 'uncertain_retry_blocked': uncertain_retry_blocked,
              'rollback_detected': rollback_detected, 'paired_prefix_check': match,
              'receipts': receipts, 'prefix_reports': reports, 'uncertain_journal': reopened.status(),
              'game_processes_opened': 0, 'game_memory_writes': 0, 'actual_game_command_calls': 0,
              'native_gameplay_enabled': False, 'full_world_synchronization_proven': False,
              'scope': 'Room binding -> saved reward preflight -> durable per-replica gate -> isolated native reward fixture -> bounded sample prefix comparison. No actual menus, two-game synchronization, network report authentication, readiness transition or game recovery.',
              'fixture_limitations': 'Existing normal-mode fixture: copied native bodies; explicit policy query stub returns 0; command containers reconstructed; local player and reconstructed vtables normalized; output does not cover all state or rank/list inputs. Fixture children exit; reopening the Python journal uses retained sample output, not reconnection to a running game.',
              'source_sha256': {str(p): sha(p.read_bytes()) for p in [OUT/'execution_journal.py',
                  ROOT/'test_execution_journal.py', Path(__file__), ROOT/'identity_pair_fixture.exe',
                  ROOT/'identity_pair_fixture.cpp', ROOT/'identity_pair_fixture_code.h']}}
    save(folder/'result.json', report)
    save(ROOT/'journal-native-pair-results.json', report)
    print(json.dumps({k: v for k, v in report.items() if k not in ('receipts', 'prefix_reports', 'source_sha256')},
                     ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()

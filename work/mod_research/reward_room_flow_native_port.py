"""Test-only IPC port for a separately owned, source-pinned native fixture.

Starts only the fixture produced by a_reward_save_owner_test.py. Its business
effect is a substitute, while Owner/bridge/owned replay/container paths are real
compiled implementations. Never discovers, launches or attaches to SAN14.
"""
import hashlib
import json
from pathlib import Path
import queue
import secrets
import subprocess
import threading

from reward_room_flow_fixture import context_from_state
import execution_journal as journal


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class NativePort:
    def __init__(self, exe, viewer, folder):
        self.exe = Path(exe).resolve()
        self.viewer = viewer
        self.calls = 0
        if viewer not in (12, 2) or self.exe.name != 'fixture.exe':
            raise ValueError('Only the two explicit owned fixture viewpoints are supported')
        self.provenance = json.loads((self.exe.parent / 'result.json').read_text(encoding='utf-8'))
        identity = self.provenance
        if identity.get('schema') != 'san14.a-reward-save-owner-owned.v1' or identity.get('result') != 'PASS':
            raise ValueError('Missing successful owned native fixture provenance')
        for name, key in [('fixture.exe', 'fixture_sha256'), ('reward.dll', 'reward_dll_sha256'),
                          ('checkpoint_planning_hold.dll', 'planning_dll_sha256')]:
            if sha(self.exe.parent / name) != identity[key]:
                raise ValueError('Owned native artifact changed: ' + name)
        source_dir = Path(__file__).parent
        for name, expected in identity['sources'].items():
            if sha(source_dir / name) != expected:
                raise ValueError('Owned native source changed: ' + name)
        self.attachment_id = secrets.token_hex(16)
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=False)
        self.output = queue.Queue()
        self.transcript = (folder / 'ipc.jsonl').open('w', encoding='utf-8')
        self.stderr = (folder / 'stderr.log').open('w', encoding='utf-8')
        self.process = subprocess.Popen([str(self.exe), 'worker' if viewer == 12 else 'worker-b',
                                         str(folder.resolve()), identity['fixture_sha256']],
                cwd=self.exe.parent, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=self.stderr, text=True, encoding='utf-8')
        def reader():
            for line in self.process.stdout:
                self.output.put(line)
        self.reader = threading.Thread(target=reader, daemon=True)
        self.reader.start()
        self.sample()

    def _call(self, packet):
        if self.process.poll() is not None:
            raise RuntimeError('Owned native attachment exited')
        self.transcript.write(json.dumps({'direction': 'request', 'packet': packet}) + '\n')
        self.transcript.flush()
        self.process.stdin.write(json.dumps(packet, separators=(',', ':')) + '\n')
        self.process.stdin.flush()
        response = json.loads(self.output.get(timeout=10))
        self.transcript.write(json.dumps({'direction': 'response', 'packet': response}) + '\n')
        self.transcript.flush()
        if response.get('ok') is not True:
            raise RuntimeError('Owned native operation rejected: ' + str(response))
        return response

    def sample(self):
        response = self._call({'op': 'sample'})
        value = response['sample']
        if response['source'] != 'owned-native-fixture' or value['viewer_force_id'] != self.viewer:
            raise ValueError('Wrong native fixture/viewer')
        return {'date': {**value['date'], 'period': '中旬'}, 'forces': {
                str(row['force_id']): {'district': row['district_id'], 'city': row['city_id'],
                'ruler': row['ruler_id'], 'gold': row['gold'], 'ap': row['action_points'],
                'officers': {str(officer['id']): officer['loyalty'] for officer in row['officers']}}
                for row in value['forces']}}

    def observe(self):
        return journal.digest(self.sample())

    def context(self, force):
        return context_from_state(self.sample(), self.viewer, force)

    def execute(self, command):
        # This adapter is deliberately fixture-only. The native sampler checks
        # resources/context again on its actual owned User callback.
        response = self._call({'op': 'reward', 'force_id': command['force_id'],
                'district_id': command['district_id'], 'officer_ids': command['officer_ids']})
        if response.get('uncertain') is not False or response.get('error') != 0 or response.get('exception') != 0:
            raise RuntimeError('Owned native result uncertain')
        if response['native_calls'] != self.calls + 1 or response['capture_calls'] != 2:
            raise RuntimeError('Native call/revalidation count changed')
        self.calls = response['native_calls']
        return {k: response[k] for k in ('source', 'sequence', 'native_returned', 'args_released',
                                       'owned_slot_cleared', 'capture_calls', 'native_calls')}

    def close(self):
        if self.process.poll() is None:
            try:
                self._call({'op': 'close'})
                self.process.wait(timeout=5)
            except Exception:
                self.process.kill()  # owned fixture process, never a game/debugger
                self.process.wait(timeout=5)
        self.process.stdin.close()
        self.process.stdout.close()
        self.transcript.close()
        self.stderr.close()

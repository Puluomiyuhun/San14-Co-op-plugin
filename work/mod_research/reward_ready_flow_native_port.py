"""Test-only successor port for source-pinned a_reward_ready_worker processes."""
import json
from pathlib import Path
import queue
import secrets
import subprocess
import threading

from reward_room_flow_native_port import NativePort, sha
from reward_ready_flow import FENCE_SCHEMA, COVERAGE, validate_fence


class ReadyNativePort(NativePort):
    def __init__(self, exe, viewer, folder):
        self.exe = Path(exe).resolve()
        self._io_lock = threading.RLock()
        self.viewer, self.calls = viewer, 0
        self.fence_setters = self.fence_observations = 0
        if viewer not in (12, 2) or self.exe.name != 'fixture.exe':
            raise ValueError('Only the two explicit owned fixture viewpoints are supported')
        self.provenance = json.loads((self.exe.parent / 'result.json').read_text(encoding='utf-8'))
        identity = self.provenance
        if identity.get('schema') != 'san14.a-reward-ready-worker-owned.v1' or identity.get('result') != 'PASS':
            raise ValueError('Missing successful observed-fence fixture provenance')
        for name, key in [('fixture.exe', 'fixture_sha256'), ('reward.dll', 'reward_dll_sha256'),
                          ('checkpoint_planning_hold.dll', 'planning_dll_sha256')]:
            if sha(self.exe.parent / name) != identity[key]:
                raise ValueError('Owned fixture artifact changed: ' + name)
        for name, expected in identity['sources'].items():
            if sha(Path(__file__).parent / name) != expected:
                raise ValueError('Owned fixture source changed: ' + name)
        self.attachment_id = secrets.token_hex(16)
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=False)
        self.output = queue.Queue()
        self.transcript = (folder / 'ipc.jsonl').open('w', encoding='utf-8')
        self.stderr = (folder / 'stderr.log').open('w', encoding='utf-8')
        self.process = subprocess.Popen([str(self.exe), 'worker' if viewer == 12 else 'worker-b',
                str(folder.resolve()), identity['fixture_sha256']], cwd=self.exe.parent,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr, text=True, encoding='utf-8')
        def reader():
            for line in self.process.stdout:
                self.output.put(line)
        self.reader = threading.Thread(target=reader, daemon=True)
        self.reader.start()
        self.sample()

    def _call(self, packet):
        with self._io_lock:
            return super()._call(packet)

    def request_fence(self, revision):
        result = self._call({'op': 'ready_fence', 'value': True, 'revision': revision})
        if (result.get('source') != 'owned-native-fixture' or result.get('requested') is not True or
                result.get('revision') != revision or result.get('ready_revision') != revision or
                result.get('observed') is not False or result.get('observed_revision') != 0):
            raise ValueError('Setter result is not an unobserved request acknowledgement')
        if result['duplicate'] is not True:
            self.fence_setters += 1
        return {'requested': True, 'revision': revision, 'observed': False}

    def observe_fence(self, revision):
        result = self._call({'op': 'fence_sample', 'revision': revision})
        if (result.get('source') != 'owned-native-fixture' or result.get('observed_revision') != revision or
                result.get('ready_revision') != revision or result.get('reward_error') != 0 or
                result.get('held_delta') != 1 or type(result.get('thread_id')) is not int or result['thread_id'] <= 0):
            raise ValueError('No current physical Owner observation')
        self.fence_observations += 1
        observation = {'schema': FENCE_SCHEMA, 'coverage': COVERAGE, **{key: result[key] for key in
                ('revision', 'requested', 'observed', 'active', 'queued', 'uncertain', 'owner_stopped',
                 'owner_error', 'user_native_started_delta', 'user_native_returned_delta',
                 'user_finally_delta', 'all_input_held')}}
        validate_fence(observation, revision)
        return observation

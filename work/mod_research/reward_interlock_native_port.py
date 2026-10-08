"""Test-only, source-pinned port for the broader planning input interlock.

The old Ready wire contract still certifies only its original User coverage.
Extra Game/UI/panel evidence is checked locally and retained in IPC transcripts;
it is not silently promoted to full input, save or simulation authorization.
"""
from copy import deepcopy
import json
from pathlib import Path
import queue
import secrets
import subprocess
import threading

from reward_room_flow_native_port import sha
from reward_ready_flow_native_port import ReadyNativePort


def validate_interlock(result, *, observed):
    def integer(name, expected=None, positive=False):
        value = result.get(name)
        if type(value) is not int or (expected is not None and value != expected) or (positive and value <= 0):
            raise ValueError('Invalid interlock evidence: ' + name)
    integer('input_missing_mask', 31)
    integer('input_interlock_error', 0)
    integer('input_gate_revision', positive=True)
    if result.get('input_interlock_uncertain') is not False:
        raise ValueError('Interlock outcome uncertain')
    for field in ('all_input_held', 'room_ready', 'save_authorized', 'native_gameplay_enabled'):
        if result.get(field) is not False:
            raise ValueError('Partial coverage cannot grant ' + field)
    if observed:
        integer('input_coverage_mask', 7)
        integer('input_observation', positive=True)
        for field in ('game_finally_delta', 'global_ui_suppressed_delta', 'panel_suppressed_delta'):
            integer(field, 1)
    else:
        integer('input_coverage_mask', 0)
        for field in ('game_finally_delta', 'global_ui_suppressed_delta', 'panel_suppressed_delta'):
            integer(field, 0)


class InterlockNativePort(ReadyNativePort):
    def __init__(self, exe, viewer, folder):
        self.exe = Path(exe).resolve()
        self._io_lock = threading.RLock()
        self.viewer, self.calls = viewer, 0
        self.fence_setters = self.fence_observations = 0
        self.last_interlock = None
        self._interlock_revision = self._interlock_gate_revision = self._interlock_observation = 0
        self._interlock_thread = None
        if viewer not in (12, 2) or self.exe.name != 'fixture.exe':
            raise ValueError('Only explicit owned fixture viewpoints supported')
        self.provenance = json.loads((self.exe.parent / 'result.json').read_text(encoding='utf-8'))
        identity = self.provenance
        if identity.get('schema') != 'san14.planning-input-interlock-owned.v1' or identity.get('result') != 'PASS':
            raise ValueError('Missing successful interlock fixture provenance')
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
            result = super()._call(packet)
            if packet['op'] in ('ready_fence', 'fence_sample'):
                observed = packet['op'] == 'fence_sample'
                validate_interlock(result, observed=observed)
                revision, gate = packet['revision'], result['input_gate_revision']
                if revision == self._interlock_revision and gate != self._interlock_gate_revision:
                    raise ValueError('Gate changed within the pinned Ready revision')
                if observed:
                    if revision != self._interlock_revision or result['input_observation'] <= self._interlock_observation:
                        raise ValueError('Stale or unordered interlock observation')
                    thread = result.get('thread_id')
                    if type(thread) is not int or thread <= 0 or self._interlock_thread not in (None, thread):
                        raise ValueError('Local observation owner thread changed')
                    self._interlock_thread = thread
                    self._interlock_observation = result['input_observation']
                    self.last_interlock = deepcopy(result)
                else:
                    if revision < self._interlock_revision:
                        raise ValueError('Old local fence revision')
                    if revision > self._interlock_revision and gate <= self._interlock_gate_revision:
                        raise ValueError('New Ready revision lacks a new gate revision')
                    self._interlock_revision, self._interlock_gate_revision = revision, gate
            return result

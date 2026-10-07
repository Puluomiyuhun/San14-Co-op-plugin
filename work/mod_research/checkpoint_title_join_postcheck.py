"""Independent read-only check after the bounded Title recorder has exited."""
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'outputs' / 'san14-link'))
from game_reader import GameReader
from checkpoint_dispatch_handoff_live import birth


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    folder = args.run.resolve()
    result_path = folder / 'result.json'
    result_raw = result_path.read_bytes()  # Never sample a still-running recorder.
    metadata = json.loads((folder / 'metadata.json').read_text(encoding='utf-8'))
    before = metadata['before']
    reader = GameReader(before['pid'])
    try:
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CheckRemoteDebuggerPresent.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
        kernel.CheckRemoteDebuggerPresent.restype = wintypes.BOOL
        debug = wintypes.BOOL()
        if not kernel.CheckRemoteDebuggerPresent(reader.memory.handle, ctypes.byref(debug)):
            raise ctypes.WinError(ctypes.get_last_error())
        actual_birth = birth(reader.memory.handle)
        record = dict(observed_at=datetime.now().astimezone().isoformat(timespec='seconds'),
            pid=reader.pid, process_birth=actual_birth,
            same_process=actual_birth == before['birth'], debugger_present=bool(debug.value),
            result_sha256=hashlib.sha256(result_raw).hexdigest(),
            read_only_independent_postcheck=True, full_world_verified=False)
        try:
            record['game_sample'] = reader.snapshot()
        except Exception as exc:
            record['game_sample_error'] = str(exc)
        target = folder / 'post-debugger-check.json'
        with target.open('x', encoding='utf-8') as out:
            json.dump(record, out, ensure_ascii=False, indent=2)
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return 0 if record['same_process'] and not debug.value else 1
    finally:
        reader.close()


if __name__ == '__main__':
    raise SystemExit(main())

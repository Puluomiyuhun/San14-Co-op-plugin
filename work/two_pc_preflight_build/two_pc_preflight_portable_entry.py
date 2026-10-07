"""Frozen entry: delegate unchanged protocol, keep private output beside EXE."""
import hashlib
import json
from pathlib import Path
import sys
import two_pc_preflight as core

CATALOG_SHA256='f4e0b5e8c62416019fedf87b410d7e3a806584608925bfdab3ba97dc39824c2f'

def main():
    if not getattr(sys,'frozen',False):
        raise RuntimeError('This entry is for the packaged executable only')
    executable_dir=Path(sys.executable).resolve().parent
    catalog=executable_dir/'catalog.json'
    if not catalog.is_file() or hashlib.sha256(catalog.read_bytes()).hexdigest()!=CATALOG_SHA256:
        raise ValueError('Missing/modified catalog.json beside executable; extract the complete matching package')
    # PyInstaller __file__ points inside a transient extraction directory.
    # This explicit override is confined to the new entry, not frozen sources.
    # --output still lets a caller choose a writable persistent output folder.
    core.HERE=executable_dir
    return core.main()

if __name__=='__main__':
    interactive=len(sys.argv)==1
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    status=0
    try:main()
    except KeyboardInterrupt:
        print('Preflight cancelled. No native backend connected.',flush=True);status=130
    except (core.RoomError,core.SyncError,OSError,ValueError,KeyError,TimeoutError,ImportError,RuntimeError,EOFError) as exc:
        print(json.dumps(dict(result='PREFLIGHT_FAILED',error=str(exc),**core.FLAGS),ensure_ascii=False),flush=True);status=1
    if interactive:
        try:input('诊断结束。按回车关闭窗口。')
        except (EOFError,KeyboardInterrupt):pass
    raise SystemExit(status)

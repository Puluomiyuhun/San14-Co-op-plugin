"""Run only bounded archived Save/User lifecycle; never opens the game."""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import os
import sys
import traceback

P = Path(__file__).resolve().parent
SOURCES = ('a_save_dispatch_test.py', 'a_save_dispatch_audit.py', 'private_checkpoint_save_apply_regression.py')
IMAGE_SHA = '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
HARNESS_SHA = '14c36c4dd807426fc057ca1cb792fb805c34280e32f5f8b7a9286074e8b058ee'


def hashes():
    return {name: hashlib.sha256((P / name).read_bytes()).hexdigest() for name in SOURCES}


def main():
    run = P / 'a_save_dispatch_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    result = dict(schema='san14.a-save-dispatch.test.v1', result='FAIL', cases=[],
                  source_sha256=hashes(), game_access=False, production_permit=False,
                  save_files_written=False, actual_os_threads=False, full_writer_exclusion=False)
    status = 1
    try:
        private = Path(os.environ['SAN14_PRIVATE_FIXTURE_ROOT']).resolve()
        sys.path.insert(0, str(private / 'python_deps'))
        raw = (private / 'game-runtime-image.bin').read_bytes()
        import a_save_dispatch_audit as audit
        audit.need(result['source_sha256']['private_checkpoint_save_apply_regression.py'] == HARNESS_SHA,
                   'frozen queue harness source')
        audit.need(hashlib.sha256(raw).hexdigest() == IMAGE_SHA, 'fixed archive image')
        result['archive_sha256'] = IMAGE_SHA
        for selected, phase in ((False, 2), (True, 2), (False, 5)):
            result['cases'].append(audit.lifecycle_case(raw, selected, phase))
        audit.need(hashes() == result['source_sha256'], 'sources unchanged')
        audit.need(hashlib.sha256((private / 'game-runtime-image.bin').read_bytes()).hexdigest() == IMAGE_SHA,
                   'archive unchanged')
        result.update(result='PASS', source_unchanged=True, archive_unchanged=True)
        status = 0
    except Exception as exc:
        result.update(error=repr(exc), traceback=traceback.format_exc())
    finally:
        (run / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(dict(result=result['result'], cases=len(result['cases']),
                              path=str(run / 'result.json'), error=result.get('error'))))
    return status


if __name__ == '__main__':
    raise SystemExit(main())

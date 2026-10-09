"""Owned-file refusal checks and the actual archived A candidate audit; no game."""
from datetime import datetime
import json
from pathlib import Path
import tempfile
import a_save_next_audit as target


def main():
    run = target.PRIVATE / 'a_save_next_audit_test_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    cases = []
    def case(name, action):
        try:
            action()
            cases.append(dict(case=name, passed=True))
        except Exception as error:
            cases.append(dict(case=name, passed=False, error=repr(error)))
    def rejects(action):
        try:
            action()
        except (ValueError, FileNotFoundError):
            return
        raise AssertionError('Expected refusal')
    with tempfile.TemporaryDirectory(prefix='owned-', dir=run) as td:
        folder = Path(td)
        file = folder / 'artifact.dll'
        file.write_bytes(b'owned non-PE hash fixture')
        digest = target.sha(file)
        case('known_file_identity', lambda: target.exact(file, digest, {}))
        case('changed_artifact_rejected', lambda: rejects(lambda: target.exact(file, '0' * 64, {})))
        case('missing_artifact_rejected', lambda: rejects(lambda: target.named(folder, 'missing.dll', digest, {})))
        second = folder / 'duplicate'
        second.mkdir()
        (second / file.name).write_bytes(file.read_bytes())
        case('ambiguous_artifact_rejected', lambda: rejects(lambda: target.named(folder, file.name, digest, {})))
        case('relative_escape_rejected', lambda: rejects(lambda: target.named(folder, '../artifact.dll', digest, {})))
    candidate = None
    def current():
        nonlocal candidate
        candidate = target.audit()
        assert candidate['result'] == 'PASS_OFFLINE_A_SINGLE_SAVE_CANDIDATE'
        assert not candidate['execution_authorized'] and candidate['native_calls'] == 0
    case('actual_archive_closure_abi_and_exports', current)
    result = dict(result='PASS' if len(cases) == 6 and all(x['passed'] for x in cases) else 'FAIL',
                  cases=cases, candidate=candidate, game_access=False, steam_access=False, native_calls=0,
                  sources={p.name: target.sha(p) for p in (Path(__file__), Path(target.__file__))})
    path = run / 'result.json'
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(result=result['result'], path=str(path), sha256=target.sha(path))))
    return 0 if result['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())

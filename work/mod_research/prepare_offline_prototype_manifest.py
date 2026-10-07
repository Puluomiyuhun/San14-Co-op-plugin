"""Pin this reviewed workspace diagnostic to an independently tested child build."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1]/'outputs'/'san14-link'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(report_path):
    report = json.loads(report_path.read_text(encoding='utf-8'))
    assert report['schema'] == 'san14.fixture-bootstrap-tests.v1'
    assert report['result'] == 'PASS' and report['sources_unchanged_during_tests']
    assert report['provenance'] == 'FIXTURE_ONLY' and not report['game_access']
    assert report['fixture_binary_sha256'] == sha(HERE/'checkpoint_session_ipc_fixture.exe')
    # The diagnostic entry is under final root testing; all bootstrap/native
    # dependencies must match the independently completed agent test exactly.
    for name, expected in report['source_sha256'].items():
        if name != 'checkpoint_offline_prototype.py':
            assert Path(name).name == name and sha(HERE/name) == expected, name
    runtime = ('checkpoint_offline_prototype.py','checkpoint_test_bootstrap.py',
        'checkpoint_session_native_port.py','checkpoint_guest_transition.py',
        'checkpoint_session_channel.py','checkpoint_visual_client.py',
        'checkpoint_visual_client_bridge.py','checkpoint_visual_client_test.py',
        'test_authoritative_sync.py','checkpoint_session_ipc_fixture.exe',
        'checkpoint_guest_native_session.h','checkpoint_guest_native_session.cpp')
    shared = ('authoritative_sync.py','checkpoint_journal.py','checkpoint_presentation.py',
              'room_session.py')
    manifest = dict(schema='san14.offline-prototype-components.v1', provenance='FIXTURE_ONLY',
        playable_mod=False, bootstrap_test=dict(path=str(report_path.resolve()), sha256=sha(report_path)),
        runtime_sha256={name: sha(HERE/name) for name in runtime},
        output_sha256={name: sha(OUT/name) for name in shared},
        note='Pinned developer fixture components; no game execution is approved by this manifest.')
    (OUT/'离线原型组件清单.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('bootstrap_report', type=Path)
    args = parser.parse_args()
    prepare(args.bootstrap_report)
    print('Offline fixture component hashes pinned.')

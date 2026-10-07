"""Read-only exact-source/binary eligibility gate for the bounded probe."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
CASES = ('dry', 'read', 'stop-before-claim', 'stop-during-original', 'guard-drift-after-original',
    'original-seh', 'original-cpp', 'concurrent-delayed-callback', 'install-publication-race',
    'stop-before-publication', 'wrong-original-stop', 'install-exception-after-protect',
    'wrong-self', 'read-short', 'read-seh', 'stop-during-read', 'absent', 'absent-present', 'absent-size-conflict', 'absent-then-present', 'absent-stop', 'absent-seh')
SOURCES = ('checkpoint_cc_file_probe.h', 'checkpoint_cc_file_probe.cpp',
    'checkpoint_cc_file_probe_guard.h', 'checkpoint_cc_file_probe_profile.h',
    'checkpoint_push_bridge.h', 'checkpoint_push_bridge.cpp', 'checkpoint_push_bridge.asm',
    'native_storage_read_core.h', 'native_storage_read_core.cpp',
    'checkpoint_cc_file_probe_fixture.cpp', 'checkpoint_cc_file_probe_build.cmd', 'checkpoint_cc_file_probe_test.py')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def validate_fixture(path, dll):
    fixture = json.loads(Path(path).read_text(encoding='utf8'))
    assert fixture['schema'] == 'san14.checkpoint-cc-file-probe-fixtures.v1'
    assert fixture['result'] == 'PASS' and fixture['game_process_access'] is False
    assert fixture['native_gameplay_enabled'] is False and fixture['live_installer_provided'] is False
    assert fixture['production_config_bytes'] == 1104 and fixture['report_bytes'] == 520
    assert fixture['dll_sha256'] == sha(dll)
    assert fixture['fixture_dll_sha256'] == sha(ROOT / 'checkpoint_cc_file_probe_fixture.dll')
    assert fixture['fixture_binary_sha256'] == sha(ROOT / 'checkpoint_cc_file_probe_fixture.exe')
    assert fixture['source_sha256'] == {name: sha(ROOT / name) for name in SOURCES}
    assert [row['case'] for row in fixture['cases']] == list(CASES)
    assert all(row['passed'] is True and row['exit_code'] == 0 and row['failures'] == 0
               and row['callback_active'] == 0 and row['game_access'] is False for row in fixture['cases'])
    abi_path = ROOT / 'native_storage_read_abi_shadow_20261006-204344-428322.json'
    abi = json.loads(abi_path.read_text(encoding='utf8'))
    assert abi['result'] == 'PASS' and len(abi['cases']) == 6 and abi['game_access'] is False
    assert abi['captured_image_sha256'] == sha(ROOT / 'game-runtime-image.bin')
    bridge_path = ROOT / 'checkpoint_push_bridge_fixture.json'
    bridge = json.loads(bridge_path.read_text(encoding='utf8'))
    assert bridge['result'] == 'PASS' and bridge['checks'] == 52 and bridge['game_process_access'] is False
    core_path = ROOT / 'native_storage_read_fixtures/20261006-204450-769948/result.json'
    core = json.loads(core_path.read_text(encoding='utf8'))
    assert core['result'] == 'PASS' and len(core['cases']) == 25 and core['game_access'] is False
    for name in ('native_storage_read_core.h', 'native_storage_read_core.cpp'):
        assert core['source_sha256'][name] == sha(ROOT / name)
    archive_path = ROOT / 'native_storage_read_fixtures/archive-20261006-204734-041207/result.json'
    archive = json.loads(archive_path.read_text(encoding='utf8'))
    assert archive['result'] == 'PASS' and archive['actual_native_local_identity_proven'] is False
    assert archive['core_cpp_sha256'] == sha(ROOT / 'native_storage_read_core.cpp')
    assert archive['bytes'] == 274880 and archive['sha256'] == '88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
    return {'fixture_path': str(Path(path).resolve()), 'fixture_sha256': sha(path),
            'dll_sha256': sha(dll), 'source_sha256': dict(fixture['source_sha256']),
            'cases': len(CASES), 'native_ABI_evidence_sha256': sha(abi_path),
            'bridge_fixture_sha256': sha(bridge_path), 'core_fixture_sha256': sha(core_path),
            'archive_fixture_sha256': sha(archive_path), 'game_access': False}

"""Compile the production encoder; exercise actual C++ bytes and Python faults.

No private game profile, game process, Steam directory, native loading, or
network access. The child constructs a codec fixture, never an actual save.
"""
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest

import checkpoint_fresh_save_packet as p

HERE = Path(__file__).resolve().parent
RUN = None
NATIVE = None
RAW = None


class PacketTests(unittest.TestCase):
    def edit(self, *, request=None, report=None):
        raw = bytearray(RAW)
        if request:
            values = list(p.REQUEST.unpack_from(raw, p.PREFIX.size))
            for name, value in request.items():
                values[p.REQUEST_FIELDS.index(name)] = value
            p.REQUEST.pack_into(raw, p.PREFIX.size, *values)
        if report:
            offset = p.PREFIX.size + p.REQUEST.size
            values = list(p.REPORT.unpack_from(raw, offset))
            for name, value in report.items():
                values[p.REPORT_FIELDS.index(name)] = value
            p.REPORT.pack_into(raw, offset, *values)
        return bytes(raw)

    def test_cpp_packet_roundtrip_and_immutable_source(self):
        a = p.decode_packet(RAW)
        self.assertEqual(a.request['room_id'], b'\1' + bytes(31))
        self.assertEqual(a.request['filename'], 'mp00000001.s14')
        self.assertEqual(a.report['original_returned'], 7)
        self.assertEqual(a.report['entries'], 9)  # unrelated scopes are balanced too
        self.assertEqual(a.data, b'\x0b' + b'c' * 65538)
        self.assertEqual(a.sha256, hashlib.sha256(a.data).hexdigest())
        self.assertFalse(a.report['room_ready'])
        with self.assertRaises(TypeError):
            a.request['period'] = 2
        with self.assertRaises(TypeError):
            a.report['status'] = 1

    def test_packet_size_magic_version_and_header(self):
        for raw in (b'', RAW[:p.HEADER_BYTES], RAW[:-1], RAW + b'x', b'BADMAGIC' + RAW[8:]):
            with self.subTest(size=len(raw)), self.assertRaises(p.PacketError):
                p.decode_packet(raw)
        for offset, value in ((8, 2), (12, p.HEADER_BYTES + 1), (16, 0), (16, p.MAX_BYTES + 1)):
            raw = bytearray(RAW)
            struct.pack_into('<I' if offset < 16 else '<Q', raw, offset, value)
            with self.subTest(offset=offset, value=value), self.assertRaises(p.PacketError):
                p.decode_packet(bytes(raw))

    def test_mutable_packet_refused(self):
        with self.assertRaises(p.PacketError):
            p.decode_packet(bytearray(RAW))

    def test_wrong_request_scope_or_basename(self):
        for key, value in (('generation', 0), ('room_epoch', 0), ('period', 0), ('room_id', bytes(32)),
                           ('year', 0), ('year', 10000), ('month', 13), ('day', 12), ('force', 0),
                           ('force', 52), ('ruler', 1000), ('reserved', 1),
                           ('filename', b'mp00000001.s14\0x'), ('filename', b'../0000001.s14\0\0')):
            with self.subTest(field=key), self.assertRaises(p.PacketError):
                p.decode_packet(self.edit(request={key: value}))

    def test_incomplete_or_unbalanced_save(self):
        for key, value in (('status', 4), ('error', 1), ('generation', 2), ('active', 1),
                           ('abnormal', 1), ('entries', 10), ('exits', 8), ('original_returned', 1),
                           ('original_returned', 10), ('first_call', 10), ('last_call', 1),
                           ('save_state', 0), ('intents', 2), ('flushed', 0), ('binds', 0),
                           ('queues', 0), ('phase_mask', 15), ('worker_started', 0), ('worker_joined', 0),
                           ('native_success', 0), ('finalizer_returned', 0), ('return_matched', 0),
                           ('executor_thread', 0), ('completed_requests', 0), ('completed_requests', 3),
                           ('stop_after_commit', 2)):
            with self.subTest(field=key), self.assertRaises(p.PacketError):
                p.decode_packet(self.edit(report={key: value}))

    def test_unsupported_authority_refused(self):
        for key, value in (('room_ready', 1), ('full_world', 1), ('file_bytes_verified', 0),
                           ('file_bytes_verified', 2)):
            with self.subTest(field=key), self.assertRaises(p.PacketError):
                p.decode_packet(self.edit(report={key: value}))

    def test_corrupt_payload_or_hash_refused(self):
        for offset in (p.HEADER_BYTES, p.HEADER_BYTES - 1, len(RAW) - 1):
            raw = bytearray(RAW);raw[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(p.PacketError):
                p.decode_packet(bytes(raw))

    def test_stop_after_committed_save_observable_but_not_permission(self):
        a = p.decode_packet(self.edit(report={'stop_after_commit': 1}))
        self.assertEqual(a.report['stop_after_commit'], 1)
        self.assertFalse(a.report['room_ready'])
        self.assertFalse(a.report['full_world'])


def main():
    global RUN, NATIVE, RAW
    RUN = HERE / 'checkpoint_fresh_save_packet_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    RUN.mkdir(parents=True)
    names = ('checkpoint_fresh_save_packet.h', 'checkpoint_fresh_save_packet.cpp',
             'checkpoint_fresh_save_packet.py', 'checkpoint_fresh_save_packet_fixture.cpp',
             'checkpoint_fresh_save_packet_test.py', 'checkpoint_fresh_save.h',
             'native_storage_read_core.h', 'native_storage_read_core.cpp')
    sources = {name: hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in names}
    vc = r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    flags = '/nologo /std:c++17 /EHa /W4 /WX /wd4324 /O2 /MT'
    commands = [f'cl {flags} /c "{HERE/name}" /Fo:{obj}.obj' for name, obj in (
        ('checkpoint_fresh_save_packet.cpp', 'packet'), ('native_storage_read_core.cpp', 'storage'),
        ('checkpoint_fresh_save_packet_fixture.cpp', 'fixture'))]
    commands += ['lib /nologo /OUT:packet.lib packet.obj',
                 'link /nologo /OUT:fixture.exe packet.obj storage.obj fixture.obj bcrypt.lib']
    build = RUN / 'build.cmd'
    build.write_text('@echo off\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\n'+
                     '\n'.join(c+'\nif errorlevel 1 exit /b 1' for c in commands)+'\n')
    built = subprocess.run(['cmd', '/c', str(build)], cwd=RUN, capture_output=True, text=True)
    (RUN/'build.log').write_text(built.stdout+built.stderr, encoding='utf-8')
    if built.returncode:
        print(built.stdout+built.stderr)
        return built.returncode
    process = subprocess.run([str(RUN/'fixture.exe'), str(RUN/'fixture.packet')],
                             cwd=RUN, capture_output=True, text=True, timeout=20)
    NATIVE = json.loads(process.stdout)
    (RUN/'native-result.json').write_text(json.dumps(NATIVE, indent=2), encoding='utf-8')
    RAW = (RUN/'fixture.packet').read_bytes()
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(PacketTests))
    unchanged = all(hashlib.sha256((HERE/n).read_bytes()).hexdigest() == v for n,v in sources.items())
    ok = result.wasSuccessful() and process.returncode == 0 and NATIVE['result'] == 'PASS' and unchanged
    report = dict(schema='san14.fresh-save-packet-check.v1', result='PASS' if ok else 'FAIL',
        tests_run=result.testsRun, native=NATIVE, sources=sources, sources_unchanged=unchanged,
        production_sha256=hashlib.sha256((RUN/'packet.lib').read_bytes()).hexdigest(),
        fixture_sha256=hashlib.sha256((RUN/'fixture.exe').read_bytes()).hexdigest(),
        game_access=False, native_save_called=False, source_attestation=False,
        full_world=False, room_ready=False, log=output.getvalue(), stderr=process.stderr)
    (RUN/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(output.getvalue());print(json.dumps({'result':report['result'], 'path':str(RUN/'result.json')}))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())

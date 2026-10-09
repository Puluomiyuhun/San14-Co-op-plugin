"""Offline audit of the captured warm-bank precommit native-size rejection.

Only explicit archived files are read. No process discovery, Steam access,
native call, install or retry is available. The evidence layout is the fixed
Win64 native_storage_read::Evidence ABI, not a general save metadata decoder.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
PRIVATE = HERE.parents[2] / 'mod_research'
sys.path.insert(0, str(PRIVATE / 'python_deps'))
import pefile
import b_warm_profile_contract as profile_abi

DLL_SHA = 'e9766e073b4a4b63d230c1f7e788d477c4f5ebb7e660a2ed3dcc5b7c8342bf05'
DATA_SHA = '166bd00ae336ac24b427d197a44be06d2554bd5e719ecfb891c15c01920aeb12'
STAGE = 'native_size_before'


class Evidence(C.Structure):
    _fields_ = [('matched', C.c_uint8), ('stage', C.c_uint64),
                ('osError', C.c_uint32), ('exceptionCode', C.c_uint32),
                ('existsCalls', C.c_uint32), ('sizeCalls', C.c_uint32),
                ('readCalls', C.c_uint32), ('sizes', C.c_int32 * 3),
                ('readReturns', C.c_int32 * 2), ('localSha256', C.c_uint8 * 32),
                ('nativeSha256', C.c_uint8 * 64)]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def audit(archive):
    archive = Path(archive).resolve(strict=True)
    dll = archive / 'bank-1/bank.dll'
    data_path = archive / 'own-bank-static-data.bin'
    config_path = archive / 'bank-1/config.bin'
    metas = []
    for path in archive.glob('own-bank-static-*.json'):
        item = json.loads(path.read_text(encoding='utf-8'))
        if item.get('purpose') == 'read-only own diagnostic DLL static-data for missing request evidence':
            metas.append((path, item))
    require(len(metas) == 1, 'Exactly one original capture metadata record required')
    metadata_path, metadata = metas[0]
    require(metadata['result'] == 'CAPTURED' and metadata['game_writes'] == 0 and metadata['native_calls'] == 0,
            'Wrong capture provenance')
    require(sha(dll) == metadata['dll_sha256'] == DLL_SHA, 'Approved bank DLL differs')
    require(sha(data_path) == DATA_SHA, 'Captured static data differs')
    sections = metadata['sections']
    require(len(sections) == 1 and sections[0]['name'] == '.data', 'Exact own-bank data capture required')
    section = sections[0]
    require(Path(section['path']).resolve() == data_path and section['sha256'] == DATA_SHA,
            'Metadata/data pairing differs')
    data = data_path.read_bytes()
    require(len(data) == section['size'] == 60724, 'Capture length differs')
    require(C.sizeof(Evidence) == 152 and Evidence.stage.offset == 8 and Evidence.sizes.offset == 36
            and Evidence.localSha256.offset == 56, 'Win64 Evidence layout differs')
    config_bytes = config_path.read_bytes()
    require(len(config_bytes) == C.sizeof(profile_abi.Config), 'Config ABI length differs')
    config = profile_abi.Config.from_buffer_copy(config_bytes)
    require((config.magic, config.size, config.version) == (profile_abi.MAGIC, C.sizeof(config), 1),
            'Config header differs')
    profile = profile_abi.validate_profile(config.profile)
    expected_hash = bytes(profile.file.sha256).hex()
    local_path = archive / 'bank-1/svdexccSC03.s14'
    require(Path(config.owner.localPath).resolve() == local_path and sha(local_path) == expected_hash
            and local_path.stat().st_size == profile.file.size, 'Original local input/config binding differs')
    image = dll.read_bytes()
    pe = pefile.PE(str(dll))
    matches = []
    string_locations = []
    try:
        pe_data = [s for s in pe.sections if s.Name.rstrip(b'\0') == b'.data']
        require(len(pe_data) == 1 and pe_data[0].VirtualAddress == section['rva']
                and pe_data[0].Misc_VirtualSize == len(data), 'PE section provenance differs')
        needle = (STAGE + '\0').encode('ascii')
        position = image.find(needle)
        while position >= 0:
            rva = pe.get_rva_from_offset(position)
            region = pe.get_section_by_rva(rva)
            require(region is not None and not region.Characteristics & 0x80000000,
                    'Evidence stage must refer to immutable DLL bytes')
            string_locations.append(dict(file_offset=position, rva=rva))
            pointer = metadata['module'] + rva
            for offset in range(0, len(data) - C.sizeof(Evidence) + 1, 8):
                if struct.unpack_from('<Q', data, offset + Evidence.stage.offset)[0] != pointer:
                    continue
                raw = data[offset:offset + C.sizeof(Evidence)]
                e = Evidence.from_buffer_copy(raw)
                require(raw[1:8] == bytes(7) and e.matched == 0, 'Not a valid unmatched Evidence structure')
                require(bytes(e.localSha256).hex() == expected_hash, 'Evidence local hash is not this input')
                require((e.osError, e.exceptionCode, e.existsCalls, e.sizeCalls, e.readCalls) == (0, 0, 1, 1, 0),
                        'Unexpected read evidence; do not infer the same failure')
                require(list(e.sizes) == [274880, 0, 0] and list(e.readReturns) == [0, 0]
                        and bytes(e.nativeSha256) == bytes(64), 'Native size/read evidence differs')
                matches.append(dict(data_offset=offset, module_rva=section['rva'] + offset,
                    stage_pointer_data_offset=offset + Evidence.stage.offset,
                    stage_string_rva=rva, stage=STAGE, matched=False,
                    os_error=e.osError, exception_code=e.exceptionCode, exists_calls=e.existsCalls,
                    size_calls=e.sizeCalls, read_calls=e.readCalls, sizes=list(e.sizes),
                    read_returns=list(e.readReturns), local_sha256=bytes(e.localSha256).hex(),
                    native_sha256=[bytes(e.nativeSha256[:32]).hex(), bytes(e.nativeSha256[32:]).hex()],
                    structure_sha256=hashlib.sha256(raw).hexdigest()))
            position = image.find(needle, position + 1)
    finally:
        pe.close()
    require(len(matches) == 2 and matches[0]['structure_sha256'] == matches[1]['structure_sha256'],
            'Expected two identical complete evidence structures')
    require(profile.file.size == 274920 and profile.file.size != matches[0]['sizes'][0], 'No expected-size mismatch')
    inputs = [dll, data_path, metadata_path, config_path, local_path,
              HERE/'native_storage_read_core.h', HERE/'native_storage_read_core.cpp',
              HERE/'b_warm_profile_request.cpp', HERE/'b_warm_profile_contract.py', Path(__file__)]
    return dict(result='CONFIRMED_NATIVE_SIZE_MISMATCH_BEFORE_READ', game_access=False,
        steam_access=False, native_calls=0, archive=str(archive), expected_size=profile.file.size,
        native_reported_size=matches[0]['sizes'][0], stage_strings=string_locations, evidence=matches,
        inputs={str(p.resolve()): sha(p) for p in inputs},
        proven=['Local file and local SHA matched the accepted profile',
                'Native FileExists returned true; native GetFileSize returned 274880',
                'Expected size was 274920, so Verify rejected before native FileRead',
                'Verify input and initial context checks had already passed'],
        unproven=['Reason native metadata differs (cache/path/namespace) is not established by this snapshot',
                  'Lease address/value was not decoded; no lease initialization failure is implied',
                  'No native refresh/write repair has been executed or approved'],
        retry_authorized=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    if args.archive is None:
        parser.print_help()
        return 0
    value = audit(args.archive)
    if args.output is not None:
        with args.output.open('x', encoding='utf-8', newline='\n') as out:
            json.dump(value, out, indent=2)
            out.write('\n')
    print(json.dumps(dict(result=value['result'], evidence_count=len(value['evidence']),
                          output=str(args.output) if args.output else None)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

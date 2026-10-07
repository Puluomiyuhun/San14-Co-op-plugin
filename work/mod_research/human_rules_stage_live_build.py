"""Build the production pass-through DLL; no game access."""
from datetime import datetime
import ctypes as C
import hashlib
import json
from pathlib import Path
import subprocess

P = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    folder = P/'human_rules_stage_live_builds'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    sources = ['human_rules_stage_live_control.cpp', 'human_rules_passthrough_stage.cpp',
               'human_rules_hook_transport.cpp']
    dll = folder/'live_stage.dll'
    command = ('cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /LD ' +
               f'/I"{P.parents[1]/"outputs/san14-link"}" ' +
               ' '.join(f'"{P/name}"' for name in sources) + f' /Fe:"{dll}"')
    build = folder/'build.cmd'
    build.write_text('@echo off\ncall "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul\nif errorlevel 1 exit /b 1\n'+command+'\n', encoding='utf8')
    run = subprocess.run(['cmd', '/d', '/c', str(build)], cwd=folder, capture_output=True)
    (folder/'build.stdout.txt').write_bytes(run.stdout)
    (folder/'build.stderr.txt').write_bytes(run.stderr)
    assert run.returncode == 0, run.stdout.decode(errors='replace')+run.stderr.decode(errors='replace')
    module = C.WinDLL(str(dll))
    info = (C.c_ubyte*48)()
    report = (C.c_ubyte*128)()
    for name, output in [('HumanRulesStageDescribeLive', info), ('HumanRulesStageReadReport', report)]:
        func = getattr(module, name)
        func.argtypes = [C.c_void_p]
        func.restype = C.c_uint32
        assert func(output) == 0
        assert func(None) == 87
    import struct
    fields = struct.unpack('<Q6I2Q', bytes(info))
    assert fields[:8] == (0x31544753524c5548, 1, 48, 24, 1208, 128, 1200,
                           C.addressof((C.c_ubyte*1208).in_dll(module, 'HumanRulesStageDescriptor')))
    assert bytes(report) == bytes(128)
    result = dict(result='PASS_PRODUCTION_BUILD_AND_CONTROL_ABI', dll=str(dll), dll_sha256=sha(dll),
                  source_sha256={name:sha(P/name) for name in sources + ['human_rules_passthrough_stage.h',
                      'human_rules_hook_transport.h','human_rules_hook_unwind.h','human_ai_runtime_profile.h',
                      'human_economy_runtime_profile.h','human_rules_stage_live_build.py']},
                  prepare_called=False, game_access=False, control_info_hex=bytes(info).hex())
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()

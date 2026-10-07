"""Fixed archived-source checks and explicit UNHANDLED paths; never process IO."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import os
import struct

ARCHIVE_SHA = '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
CODE = ((0x3F8140, 0x3F871B, '6689167731d268ca838b2490569022f8412b40f75869f9933aaf0e8af004b69f'),
        (0x1AC3C0, 0x1AC423, '8d941d86ab42f55bbf1878f46d1e05aca7dd298474030c8cc0fd7d534b8670d6'))
# Each is already decoded in the frozen archive audits. These short fixed
# fingerprints re-check that the exact known bypass still exists in this build.
UNHANDLED = (
    (0x3F8606, 'e815220000', 'Game direct panel consumer -> 3FA820'),
    (0x3FA857, '8b88b0010000', 'Panel reads latched +1B0 command, independent of global UI'),
    (0x3F9EFA, 'e8a18efaff', 'Raw User queries keyboard Modifier22 -> 3A2DA0'),
    (0x3A2DA9, 'f6405022', 'Modifier reads physical keyboard +50 bypassing neutral normalized cache'),
    (0x3F9F9D, '83b8b001000001', 'Raw User tests latched panel advance request'),
    (0x3F9FA6, '39ab7c040000', 'Raw User tests second Game+47C advance request'),
    (0x3FA06D, 'e82ee4eeff', 'Raw User starts native advance save -> 2E84A0'),
    (0x3FA09A, 'e8d1210000', 'Raw User planning command dispatch -> 3FC270'),
    (0x51234A, 'e891e8ffff', 'Window dispatch -> 510BE0 remains outside Game/UI owner'),
    (0x510C1C, 'e8af2de9ff', 'Message mouse preprocessing -> 3A39D0 happens before ordinary dispatch'),
    (0x510D59, 'ba01020000', 'Enter can be reposted as left-button down'),
    (0x510D7C, 'ba02020000', 'Enter release can be reposted as left-button up'),
    (0x510E0F, 'ba04020000', 'Backspace/Escape can be reposted as right-button down'),
    (0xF4C948, 'ff5050', 'Buffered DirectInput keyboard GetDeviceData still drains physical events'),
    (0xF4B458, 'ff5048', 'DirectInput mouse GetDeviceState still reads physical buttons/motion'),
    (0xF4AB13, 'ff5048', 'DirectInput controller GetDeviceState remains uncovered'),
    (0xF4AAB9, 'ff5008', 'Alternate controller callback is separate from DirectInput'),
    (0x509BEA, 'e8e199e9ff', 'Root translates keyboard/controller -> 3A35D0; may repopulate normalized cache'),
    (0x509BFA, 'e81196e9ff', 'Root translates mouse -> 3A3210; may repopulate normalized cache'),
)


def inspect(private: Path):
    raw = (private/'game-runtime-image.bin').read_bytes()
    if hashlib.sha256(raw).hexdigest() != ARCHIVE_SHA:
        raise ValueError('Private archive identity mismatch')
    for begin, end, expected in CODE:
        if hashlib.sha256(raw[begin:end]).hexdigest() != expected:
            raise ValueError(f'Code profile mismatch: {begin:x}')
    runtime_base = struct.unpack_from('<Q', raw, 0x12CC9B8+0x28)[0]-0x3F8140
    if struct.unpack_from('<Q', raw, 0x1297CF8+0x18)[0] != runtime_base+0x1AC3C0:
        raise ValueError('Global UI original vtable source mismatch')
    if raw[0x3F85F2:0x3F85F6] != bytes.fromhex('41ff5018'):
        raise ValueError('Game actual global UI virtual-call site mismatch')
    paths=[]
    for at, fingerprint, meaning in UNHANDLED:
        expected=bytes.fromhex(fingerprint)
        if raw[at:at+len(expected)] != expected:
            raise ValueError(f'Uncovered path fingerprint differs: {at:x}')
        paths.append(dict(rva=hex(at), description=meaning, covered=False))
    return dict(schema='san14.a-save-input-source-coverage.v1', result='PASS',
        archive_sha256=ARCHIVE_SHA, game_access=False,
        sources=[dict(slot='12CC9B8+28', original='3F8140', role='transparent Game parent'),
                 dict(slot='1297CF8+18', original='1AC3C0', caller='3F85F2', role='scoped global UI consumer')],
        code=[dict(rva=hex(a), length=b-a, sha256=h) for a,b,h in CODE],
        covered_descendant_calls=['1AC3FB [r8+18]', '1AC40D [r8+18]'],
        covered_descendant_limit='Only when reached through the actually suppressed 1AC3C0 call. Direct calls to those dynamic child objects are not covered.',
        unhandled_paths=paths, global_input_hold=False, save_authorized=False,
        unknowns=['Other indirect/script consumers outside these fixed archive anchors',
                  'Physical-release/quarantine across window focus changes',
                  'Real scheduler ordering and all thread writes'])


def main():
    value=os.environ.get('SAN14_PRIVATE_FIXTURE_ROOT', '')
    if not value:
        raise SystemExit('Set SAN14_PRIVATE_FIXTURE_ROOT; no archive was read.')
    result=inspect(Path(value).resolve())
    run=Path(__file__).resolve().parent/'a_save_input_sources_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True)
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(result=result['result'], unhandled_anchors=len(result['unhandled_paths']), path=str(run/'result.json'))))


if __name__=='__main__':
    main()

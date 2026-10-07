"""Create a distinct type0 pilot from reviewed utility code; no process access.

Retired sources/binaries/once files are never modified. The copied low-level
string/path/storage helpers are retained; dispatch and ABI are replaced.
"""
from pathlib import Path
P = Path(__file__).resolve().parent
for suffix in ('pilot.h', 'pilot.cpp', 'fixture.cpp', 'contract.py', 'test.py', 'build.cmd'):
    source = (P / ('private_checkpoint_save_' + suffix)).read_text(encoding='utf8')
    source = source.replace('PRIVATE_CHECKPOINT_SAVE_FIXTURE','CHECKPOINT_PUSH_FIXTURE')
    source = source.replace('PrivateCheckpointSave','CheckpointPush')
    source = source.replace('private_checkpoint_save_','checkpoint_push_')
    source = source.replace('mpckpt01.s14','mppush01.s14')
    source = source.replace('0x53414E1450535631','0x53414E1450534832')
    source = source.replace('0x1414E101','0x1414E201')
    target = P / ('checkpoint_push_' + suffix)
    with target.open('x', encoding='utf8') as stream:
        stream.write(source)
print('Created new candidate source copies; no game access, no build or install')

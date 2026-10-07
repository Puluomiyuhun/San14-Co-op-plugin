"""Reuse the tested debug lifecycle; add a small adaptive load-only payload."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=(ROOT/'observe_load_rng.cpp').read_text(encoding='utf-8')
# Retain only helpers needed by the new payload, not old RNG diagnostics.
a=s.index('static void contextDetails(')
b=s.index('int wmain(',a)
s=s[:a]+'#include "startup_identity_observe.inc"\n\n'+s[b:]
s=s.replace('rva!=0x3AA3E0','rva!=0x2EE64C')
old='''c.Dr0=target; c.Dr6=0;
                        c.Dr7=(c.Dr7&~DWORD64(0xffff00ff))|1;
                        if(!fixtureMode) { c.Dr1=base+0x3AA3D5;c.Dr2=base+0x3AA43B;c.Dr3=base+0x3AA805;c.Dr7|=0x54; }'''
assert old in s
s=s.replace(old,'armPoints(c,base,target);')
a=s.index('bool ours=');b=s.index('if(ours)',a)
s=s[:a]+'''bool ours=((c.Dr6&1)&&c.Rip==c.Dr0)||(!fixtureMode&&
                            (((c.Dr6&2)&&c.Rip==c.Dr1)||((c.Dr6&4)&&c.Rip==c.Dr2)||((c.Dr6&8)&&c.Rip==c.Dr3)));
                        '''+s[b:]
s=s.replace('bool wasStarted=started;','auto oldEpoch=pointEpoch;')
s=s.replace('if(started) c.Dr7|=0x40;','armPoints(c,base,target);')
s=s.replace('if(!wasStarted && started) {','if(oldEpoch!=pointEpoch) {')
s=s.replace('otherContext.Dr7|=0x40;','armPoints(otherContext,base,target);')
s=s.replace('Arm planning return observation','Rearm load boundary observation')
assert 'WriteProcessMemory(' not in s and 'wasStarted' not in s
(ROOT/'observe_startup_identity.cpp').write_text(s,encoding='utf-8')
t=(ROOT/'test_load_rng_observer.py').read_text(encoding='utf-8')
t=t.replace('observe_load_rng.exe','observe_startup_identity.exe').replace('load-rng-fixtures.json','startup-identity-observer-tests.json')
(ROOT/'test_startup_identity_observer.py').write_text(t,encoding='utf-8')
print('Generated startup observer; no game attachment')

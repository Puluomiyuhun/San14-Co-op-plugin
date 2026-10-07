import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=subprocess.run([str(ROOT/'rng_route_dll_fixture.exe'),str(ROOT/'rng_route_fixture.dll')],capture_output=True,text=True,timeout=20)
assert p.returncode==0,(p.returncode,p.stdout,p.stderr)
rows=[json.loads(line) for line in p.stdout.splitlines()]
assert len(rows)==10 and all(r['result']=='PASS' for r in rows)
assert sum(r['checks'] for r in rows)==5145
files=['rng_route_fixture_api.h','rng_route_fixture_dll.cpp','rng_route_fixture.dll',
       'rng_route_fixture_bridges.asm','rng_route_dll_fixture.cpp','rng_route_dll_fixture.exe',
       'rng_route_native_fixture.h','native_rng_fixture_code.h','build_rng_route_fixture.cmd',
       'validate_rng_route_dll_fixture.py']
report={'result':'PASS','cases':rows,'game_hook_installed':False,
        'scope':'Dedicated executable loads this DLL into itself. Native leaf helper copies serve as result/state references; MASM bridges exercise CALL and tail JMP. No game process opened by either binary.',
        'limits':['Private-state algorithm is equivalent on tested seeds, boundaries and sequence checks; this is not battlefield simulation.',
                  'Representative nonvolatile checks cover RBX/RSI, not an exhaustive processor-context conformance suite.',
                  'Ordinary C++ throw and explicit RaiseException were tested; this does not promise recovery from memory corruption or process termination.',
                  'Only one logical draw thread was tested. Child threads intentionally default to native.',
                  'No live relay allocation, instruction replacement, dynamic unwind registration, or concurrent DLL unloading is implemented.'],
        'files':[{'path':f,'sha256':hashlib.sha256((ROOT/f).read_bytes()).hexdigest()} for f in files]}
(ROOT/'rng-route-dll-validation-m.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'result':'PASS','cases':len(rows),'checks':sum(r['checks'] for r in rows),'game_hook_installed':False}))

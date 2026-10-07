from pathlib import Path
import subprocess
P=Path(__file__).resolve().parent
run=P/'checkpoint_persistent_runtime_runs/20261007-183820-659107'
lines=(run/'build.cmd').read_text().splitlines()
commands=lines[:5]+[x for x in lines if (x.startswith('cl ') and 'checkpoint_persistent_runtime_fixture.cpp' in x) or x.startswith('link ') ]
script=run/'diagnostic-build.cmd';script.write_text('\n'.join(commands)+'\n')
result=subprocess.run(['cmd','/c',str(script)],cwd=P,capture_output=True);print(result.stdout.decode(errors='replace'));assert not result.returncode
import shutil
folder=run/'padding-diagnostic';folder.mkdir(exist_ok=False)
for i in ['0','1']:
 (folder/i).mkdir();shutil.copyfile(run/'user-exception'/i/'svdexccSC03.s14',folder/i/'svdexccSC03.s14')
result=subprocess.run([str(run/'fixture.exe'),'user-exception',str(folder/'0/svdexccSC03.s14'),str(folder)],cwd=P,capture_output=True)
(folder/'stdout.txt').write_bytes(result.stdout);print(result.stdout.decode(errors='replace'))

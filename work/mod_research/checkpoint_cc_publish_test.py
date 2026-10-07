"""Build and test only our own EXE/DLL. Never opens a game process."""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import subprocess

P=Path(__file__).resolve().parent
RUN=P/'checkpoint_cc_publish_fixtures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
RUN.mkdir(parents=True)
sources=['checkpoint_cc_publish.h','checkpoint_cc_publish.cpp',
    'checkpoint_cc_publish_guard.h','checkpoint_cc_publish_profile.h',
    'checkpoint_push_bridge.h','checkpoint_push_bridge.cpp','checkpoint_push_bridge.asm',
    'native_storage_read_core.h','native_storage_read_core.cpp','native_storage_publish_core.h','native_storage_publish_core.cpp','checkpoint_cc_publish_binding.h',
    'checkpoint_cc_publish_fixture.cpp','checkpoint_cc_publish_build.cmd','checkpoint_cc_publish_test.py']
def sha(name):return hashlib.sha256((P/name).read_bytes()).hexdigest()
build=subprocess.run(['cmd','/c',str(P/'checkpoint_cc_publish_build.cmd')],cwd=P,capture_output=True)
(RUN/'build.stdout.txt').write_bytes(build.stdout)
(RUN/'build.stderr.txt').write_bytes(build.stderr)
if build.returncode:raise SystemExit(build.returncode)
cases=['dry','read','stop-before-claim','stop-during-original','guard-drift-after-original',
    'original-seh','original-cpp','concurrent-delayed-callback','install-publication-race',
    'stop-before-publication','wrong-original-stop','install-exception-after-protect',
    'wrong-self','read-short','read-seh','stop-during-read','write-false','write-seh','stop-during-write','wrong-stage-identity','existing-intent','native-present']
rows=[]
for case in cases:
    target=RUN/case;target.mkdir()
    try:
        proc=subprocess.run([str(P/'checkpoint_cc_publish_fixture.exe'),case,str(target/'svdexccSC03.s14')],
            cwd=P,capture_output=True,timeout=15)
        (target/'stdout.txt').write_bytes(proc.stdout);(target/'stderr.txt').write_bytes(proc.stderr)
        output=proc.stdout.decode('utf8',errors='replace')
        lines=[line for line in output.splitlines() if line.startswith('{')]
        row=json.loads(lines[-1]) if lines else {'case':case,'passed':False,'error':'No fixture report'}
        row['exit_code']=proc.returncode;row['passed']=row['passed'] and proc.returncode==0
    except subprocess.TimeoutExpired:
        row={'case':case,'passed':False,'error':'Fixture timeout; subprocess killed, no game access'}
    rows.append(row)
result={'schema':'san14.checkpoint-cc-publish-fixtures.v1',
    'result':'PASS' if all(r['passed'] for r in rows) else 'FAIL','cases':rows,
    'source_sha256':{name:sha(name) for name in sources},
    'dll_sha256':sha('checkpoint_cc_publish.dll'),
    'fixture_dll_sha256':sha('checkpoint_cc_publish_fixture.dll'),
    'fixture_binary_sha256':sha('checkpoint_cc_publish_fixture.exe'),
    'production_config_bytes':1104,'report_bytes':680,
    'scope':'Own process with synthetic storage providers and injectable fixture-only guard; production guard is compile/static-reviewed, not live-tested.',
    'game_process_access':False,'live_installer_provided':False,'native_gameplay_enabled':False}
(RUN/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps({'result':result['result'],'cases':len(rows),'failed':[r['case'] for r in rows if not r['passed']],
                  'report':str(RUN/'result.json')},ensure_ascii=False))
raise SystemExit(0 if result['result']=='PASS' else 1)

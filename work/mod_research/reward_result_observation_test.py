"""Owned process/owned memory tests only; no SAN14 discovery or access."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import reward_result_observation as observer
import reward_result_observation_events as events
import a_save_observation_test as predecessor
P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
MODES=('matched','zero-return','wrapper-no-common','unreturned','orphan-return','wrong-return-rsp',
 'wrong-return-thread','wrong-return-state','wrong-common-frame','nested','duplicate-common',
 'world-change','date-change','draft-change','funding-change','missing-return','duplicate-return')
ACCEPT=('matched','zero-return','wrapper-no-common','unreturned')
def main():
 run=PRIVATE/'reward_result_observation_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 result=dict(schema='san14.reward-result-observation-owned-tests.v1',result='FAIL',sources={n:observer.sha(P/n) for n in observer.SOURCES},cases=[],game_access=False,native_execution_verified=False,production_permit=False)
 try:
  # Debug ownership/cleanup engine is byte-for-byte predecessor after include renames.
  assert (P/'reward_result_observation.cpp').read_text()==(P/'reward_menu_observation.cpp').read_text().replace('reward_menu_observation','reward_result_observation')
  for suffix in ('_decode.inc','_binding.inc','_anchors.h','_debug_status.inc'):
   assert (P/('reward_result_observation'+suffix)).read_text()==(P/('reward_menu_observation'+suffix)).read_text().replace('reward_menu_observation','reward_result_observation')
  image=PRIVATE/'game-runtime-image.bin'
  result['archived_image_sha256']=observer.sha(image)
  with image.open('rb') as stream:
   for rva,expected in observer.anchors():
    stream.seek(rva);assert stream.read(len(expected))==expected,hex(rva)
  result['cases'].append(dict(case='frozen-core-and-archived-instruction-anchors',passed=True))
  flags='/nologo /std:c++17 /EHsc /W4 /WX /I"'+str(P)+'"'
  commands=[f'cl {flags} "{P/"reward_result_observation.cpp"}" /Fe:observer.exe /Fo:production.obj /link /INCREMENTAL:NO',
   f'cl {flags} /DA_SAVE_OBSERVATION_FIXTURE "{P/"reward_result_observation.cpp"}" /Fe:observer-fixture.exe /Fo:fixture.obj /link /INCREMENTAL:NO',
   f'cl {flags} "{P/"a_save_observation_debug_fixture.cpp"}" /Fe:submit_probe_fixture.exe /Fo:debug-fixture.obj /link /INCREMENTAL:NO',
   f'cl {flags} "{P/"reward_result_observation_semantic_fixture.cpp"}" /Fe:semantic.exe /Fo:semantic.obj /link /INCREMENTAL:NO',
   f'cl {flags} "{P/"reward_result_observation_status_fixture.cpp"}" /Fe:status-fixture.exe /Fo:status.obj /link /INCREMENTAL:NO']
  build=run/'build.cmd';build.write_text('@echo off\nsetlocal\ncall "'+predecessor.VC+'" >nul\nif errorlevel 1 exit /b 1\n'+'\n'.join(c+'\nif errorlevel 1 exit /b 1' for c in commands)+'\n',encoding='utf-8')
  proc=subprocess.run(['cmd','/c',str(build)],cwd=run,capture_output=True);(run/'build.log').write_bytes(proc.stdout+proc.stderr)
  assert not proc.returncode,run/'build.log'
  proc=subprocess.run([str(run/'status-fixture.exe'),str(run/'status-cases.jsonl')],capture_output=True,timeout=15)
  (run/'status-fixture.stdout').write_bytes(proc.stdout);status=json.loads(proc.stdout)
  assert not proc.returncode and status['passed'] and status['checks']==26
  result['cases'].append(dict(case='debug-status-owned-roundtrips',passed=True,checks=26))
  for mode in predecessor.MODES:
   result['cases'].append(predecessor.hardware(run,mode));print('hardware',mode,'PASS',flush=True)
  for mode in MODES:
   folder=run/('semantic-'+mode);folder.mkdir();trace=folder/'trace.jsonl'
   proc=subprocess.run([str(run/'semantic.exe'),str(trace),mode],capture_output=True,timeout=15)
   (folder/'stdout.txt').write_bytes(proc.stdout);(folder/'stderr.txt').write_bytes(proc.stderr)
   data=json.loads(proc.stdout);reject=mode not in ACCEPT
   assert proc.returncode==int(reject) and data['rejected']==reject,(mode,data,proc.stderr)
   allrows=observer.records(trace,allow_partial=False);rows=[r for r in allrows if 'seq' in r]
   meta={k:allrows[0][k] for k in ('pid','birth','base','run_id')};meta.update(capture_complete=not reject,capture_errors=['rejected'] if reject else [])
   analysis=events.analyze(rows,meta)
   expected='INCOMPLETE_CAPTURE' if reject or mode=='unreturned' else 'INCONCLUSIVE' if mode=='wrapper-no-common' else 'NATIVE_BUSINESS_RETURN_PAIRED'
   assert analysis['classification']==expected and not analysis['production_permit'],(mode,analysis)
   if mode in ('matched','zero-return'):
    pair=analysis['pairs'][0];assert pair['native_return_raw']==(7 if mode=='matched' else 0) and pair['wrapper_result_raw']==99
    assert not pair['native_return_success_verified'] and pair['common_return_seq']==3
   observer.write(folder/'analysis.json',analysis)
   result['cases'].append(dict(case=mode,passed=True,contexts_are_models=True,classification=expected))
  rows=observer.records(run/'semantic-matched'/'trace.jsonl',allow_partial=False)
  meta={k:rows[0][k] for k in ('pid','birth','base','run_id')};meta.update(capture_complete=True,capture_errors=[])
  rows=[r for r in rows if 'seq' in r]
  variants=[('wrong-return-rva',lambda r,m:r[2].update(rva=0x67A998)),('lost-events',lambda r,m:r[2].update(lost_events=1)),
   ('wrong-thread',lambda r,m:r[2].update(thread=12)),('wrong-run',lambda r,m:r[2].update(run_id='other')),
   ('wrong-frame',lambda r,m:r[2].update(rsp=r[2]['rsp']+8)),('extra-field',lambda r,m:r[2].update(success=True)),
   ('bool-return',lambda r,m:r[2].update(eax=True)),('incomplete-lifecycle',lambda r,m:m.update(capture_complete=False)),
   ('truncated-common-return',lambda r,m:r.pop(2)),('duplicate-common-return',lambda r,m:r.insert(3,deepcopy(r[2])))]
  for name,fn in variants:
   r=deepcopy(rows);m=deepcopy(meta);fn(r,m);a=events.analyze(r,m)
   assert a['classification']=='INCOMPLETE_CAPTURE' and not a['network_submission_allowed'],(name,a)
   result['cases'].append(dict(case=name,passed=True))
  for args in ([],['--preflight']):
   proc=subprocess.run([sys.executable,str(P/'reward_result_observation.py'),*args],capture_output=True,timeout=10)
   assert proc.returncode==(2 if args else 0)
  result['cases'].append(dict(case='inert-help-explicit-pid',passed=True))
  assert all(observer.sha(P/n)==v for n,v in result['sources'].items())
  result.update(result='PASS',sources_unchanged=True,production_sha256=observer.sha(run/'observer.exe'))
 except Exception as error:
  result['error']=repr(error);raise
 finally:
  result['artifacts']={str(p.relative_to(run)):observer.sha(p) for p in run.rglob('*') if p.is_file()}
  observer.write(run/'result.json',result);print(json.dumps(dict(result=result['result'],cases=len(result['cases']),path=str(run/'result.json'))),flush=True)
if __name__=='__main__':main()

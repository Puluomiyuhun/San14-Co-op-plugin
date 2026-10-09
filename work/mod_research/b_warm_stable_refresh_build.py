"""Bind tested stable Python capture to the unchanged approved native refresh DLL.

No native recompilation or game access. Input receipts are local, hash-pinned
evidence; the copied DLL remains subject to all live guards.
"""
from pathlib import Path
from datetime import datetime
import hashlib,json,shutil
P=Path(__file__).resolve().parent;PRIVATE=P.parents[2]/'mod_research'
INPUTS={
 'native':('b_warm_refresh_pair_runs/20261009-215046-831686/result.json','2af0e06f5f0823450f3195be5feeae796f36cefc230e0fafa52b6dde0ea88a2d'),
 'capture':('b_warm_stable_capture_runs/20261009-220004-423346/result.json','d6cb178390febdab93e9f0b9dc67735595e360607c7b51016825e2a88d6ccffd'),
 'python':('b_warm_stable_refresh_python_runs/20261009-220120-150754/result.json','aa56f4e8200725096526c5f47b4013f2f597c75eced87256f896ab571a191fab')}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 run=PRIVATE/'b_warm_stable_refresh_build_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 out=dict(family='san14.b-warm-refresh-pair.v1',result='FAIL',game_process_access=False,steam_save_access=False)
 try:
  approved={};sources={str(Path(__file__).resolve()):sha(__file__)};private={}
  for label,(name,h) in INPUTS.items():
   path=PRIVATE/name;assert sha(path)==h;data=json.loads(path.read_text(encoding='utf8'));assert data['result']=='PASS'
   for section in ('sources','private','generated','binaries','artifacts'):
    for n,digest in data.get(section,{}).items():assert sha(n)==digest,(label,section,n)
   for n,digest in data['sources'].items():
    assert n not in sources or sources[n]==digest,n
    sources[n]=digest
   private[str(path)]=h;private.update(data.get('private',{}));approved[label]=data
  native=approved['native'];assert native['refresh_factory_pair_passed'] is True
  assert approved['capture']['tests']==8 and approved['python']['tests']==9
  product=run/'production';product.mkdir();dll=product/'checkpoint_complete_live_owner_v2.dll'
  shutil.copyfile(native['production_dll']['path'],dll);assert sha(dll)==native['production_dll']['sha256']
  out.update(result='PASS',inputs_unchanged=all(sha(n)==h for n,h in sources.items()),sources=sources,private=private,
   generated=native['generated'],binaries={**native['binaries'],str(dll):sha(dll)},
   production_dll=dict(path=str(dll),sha256=sha(dll)),refresh_factory_pair_passed=True,full_factory_pair_passed=True,
   stable_capture_passed=True,native_reused_without_recompile=True,capture_tests=8,python_tests=9,
   live_two_loads_passed=False,room_ready=False)
  assert out['inputs_unchanged']
 except Exception as exc:out.update(result='FAIL',error=repr(exc))
 path=run/'result.json';path.write_text(json.dumps(out,indent=2)+'\n',encoding='utf8')
 print(json.dumps(dict(result=out['result'],path=str(path),sha256=sha(path),error=out.get('error'))))
 return int(out['result']!='PASS')
if __name__=='__main__':raise SystemExit(main())

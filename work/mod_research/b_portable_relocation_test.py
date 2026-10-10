"""Owned isolated Python relocation checks; no process discovery or game access.

The source-only import bundle below tests dependency/layout portability, not
native approval or execution. Production release/entry checks can be run against
an explicitly supplied, content-pinned release without invoking --execute.
"""
from datetime import datetime
import hashlib,json,subprocess,sys,shutil,os
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import b_portable_release_export as collector
import b_portable_package as package
from portable_release import write_bundle,Release

CHILD=r'''
import sys,json,sysconfig,importlib.abc,importlib.machinery
from pathlib import Path
root=Path(sys.argv[1]).resolve();mode=sys.argv[2]
stdlib=Path(sysconfig.get_path('stdlib')).resolve()
base=Path(sys.base_prefix).resolve()
allowed=[root,stdlib,base/'DLLs']
sys.path[:]=[str(root/'repo/work/mod_research'),str(root/'repo/outputs/san14-link'),
             str(root/'deps'),str(stdlib),str(base/'DLLs')]
blocked={'capstone','unicorn','cryptography','numpy','psutil','requests'}
class OnlyBundle(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in blocked:raise ImportError('Non-runtime dependency blocked: '+fullname)
  spec=importlib.machinery.PathFinder.find_spec(fullname,path)
  if spec and spec.origin and spec.origin not in ('built-in','frozen'):
   p=Path(spec.origin).resolve()
   if not any(p.is_relative_to(x) for x in allowed) or 'site-packages' in p.parts:
    raise ImportError('Import escaped isolated bundle: '+fullname)
  return spec
sys.meta_path.insert(0,OnlyBundle())
try:
 import b_simple_remote_guest as guest
except ModuleNotFoundError as exc:
 if mode=='missing-pefile' and exc.name=='pefile':
  print(json.dumps(dict(result='EXPECTED_MISSING_PEFILE',module=exc.name)));raise SystemExit(0)
 raise
if mode=='missing-pefile':raise AssertionError('pefile unexpectedly available')
assert guest.ROOT==root/'repo'
assert sys.modules['b_warm_start'].PRIVATE==root/'mod_research'
assert 'pefile' in sys.modules and Path(sys.modules['pefile'].__file__).resolve()==root/'deps/pefile.py'
assert not blocked.intersection(sys.modules)
if mode=='help':assert guest.main([])==0
if mode=='verify':
 from portable_release import Release
 import b_portable_guest as entry
 import hashlib
 manifest_sha=hashlib.sha256((root/'release.json').read_bytes()).hexdigest()
 reads=[]
 def audit(event,args):
  if event!='open' or not isinstance(args[0],(str,bytes)):return
  p=Path(os.fsdecode(args[0])).resolve()
  if not any(p.is_relative_to(x) for x in allowed):raise AssertionError('File access escaped release: '+str(p))
  reads.append(str(p))
 import os
 sys.addaudithook(audit)
 assert entry.main(['--verify','--release-root',str(root),'--release-sha256',manifest_sha])==0
 assert not Path(os.environ['LOCALAPPDATA']).exists(),'Verification created machine state'
 assert reads and all(not Path(p).name.endswith('.s14') for p in reads)
projects={}
for name,module in list(sys.modules.items()):
 if name=='__main__':continue  # This exact owned harness lives beside the release.
 file=getattr(module,'__file__',None)
 if not file:continue
 p=Path(file).resolve()
 if p.is_relative_to(root):projects[name]=str(p.relative_to(root))
 elif not any(p.is_relative_to(x) for x in allowed[1:]):raise AssertionError('Foreign loaded module: '+name)
print(json.dumps(dict(result='PASS',mode=mode,project_modules=projects,
 third_party_loaded=['pefile'],blocked_dependencies=sorted(blocked),
 private=str(sys.modules['b_warm_start'].PRIVATE),game_access=False)))
'''


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def native_spec():
    return dict(schema=collector.SCHEMA,
        pair=dict(result=str(PRIVATE/'b_warm_refresh_pair_runs/20261009-215046-831686/result.json'),sha256='2af0e06f5f0823450f3195be5feeae796f36cefc230e0fafa52b6dde0ea88a2d'),
        helper=dict(result=str(PRIVATE/'b_warm_coordinator_build_runs/20261009-181031-457801/result.json'),sha256='4204df275c981b6c35c6bea01a25e040a0cea04be84e20ff2998079917e3b43a'),
        reward=dict(run=str(PRIVATE/'b_reward_owner_runs/20261010-095208-139540'),sha256='028ce8040e91c1b3a1b8d27b4a1e55bbdbe22e728204dec0f717419884974478'),
        input=dict(run=str(PRIVATE/'player_input_lease_bootstrap_runs/20261010-101506-064151'),sha256='55359a4455a267b98c59d247a10aefe4c6c479582329bdf6cef28c543d91fb2e'),
        rules=dict(stage=str(PRIVATE/'human_rules_activation_v2_runs/20261008-000431-509932/production.dll'),publisher=str(PRIVATE/'human_rules_activation_publish_v2_runs/20261008-000527-938626/inputs/publisher-production.exe')))


def main():
    folder=PRIVATE/'b_portable_relocation_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True,exist_ok=False)
    sources,_,_=collector.python_closure([HERE/'b_simple_remote_guest.py'])
    sources.update({Path(__file__).resolve():sha(__file__),HERE/'b_portable_release_export.py':sha(HERE/'b_portable_release_export.py'),
                    HERE/'portable_release.py':sha(HERE/'portable_release.py'),HERE/'b_portable_package.py':sha(HERE/'b_portable_package.py')})
    assets=[dict(source=p,path='repo/'+p.relative_to(ROOT).as_posix(),sha256=h,role='source') for p,h in sorted(sources.items())]
    dep_assets=package.collect_dependencies()['assets']
    dependencies=[a['source'] for a in dep_assets]
    dependency_pins={str(p):sha(p) for p in dependencies}
    result=dict(result='INCOMPLETE',scope='source-only isolated import/default-help',game_access=False,
                native_execution=False,producer_native_approval_executed=False,
                sources={str(p):h for p,h in sources.items()},private=dependency_pins,cases=[])
    try:
        for name,extra in (('relocated',dep_assets),('missing-pefile',[])):
            release=folder/name
            info=write_bundle(release,assets+extra,dict(test_only=True,game_access=False))
            manifest_sha=sha(release/'release.json');Release(release,manifest_sha)
            for mode in (('import','help') if extra else ('missing-pefile',)):
                child=folder/(name+'-'+mode+'.py');child.write_text(CHILD,encoding='utf-8')
                command=[sys.executable,'-I','-S','-B',str(child),str(release),mode]
                run=subprocess.run(command,cwd=folder,capture_output=True,text=True,timeout=45)
                (folder/(name+'-'+mode+'.stdout.log')).write_text(run.stdout,encoding='utf-8')
                (folder/(name+'-'+mode+'.stderr.log')).write_text(run.stderr,encoding='utf-8')
                if run.returncode:raise AssertionError(f'{mode} child exit {run.returncode}: '+run.stderr)
                row=json.loads(run.stdout.splitlines()[-1]);row.update(command=command,exit_code=run.returncode,manifest_sha256=manifest_sha)
                result['cases'].append(row)
            Release(release,manifest_sha).verify_all()
        selection=collector.collect(native_spec(),extra_sources=[HERE/'b_portable_guest.py',HERE/'b_portable_approval.py'])
        for asset in selection['assets']:
            result['sources' if asset['role']=='source' else 'private'][str(asset['source'])]=asset['sha256']
        produced=folder/'producer-release';moved=folder/'other machine with spaces'
        made=package.assemble(native_spec(),destination=produced,zip_path=folder/'portable.zip')
        result['package']=made
        shutil.copytree(produced,moved)
        child=folder/'production-verify.py';child.write_text(CHILD,encoding='utf-8')
        command=[sys.executable,'-I','-S','-B',str(child),str(moved),'verify']
        env={**os.environ,'LOCALAPPDATA':str(folder/'unused-local-profile')}
        run=subprocess.run(command,cwd=folder,env=env,capture_output=True,text=True,timeout=90)
        (folder/'production-verify.stdout.log').write_text(run.stdout,encoding='utf-8')
        (folder/'production-verify.stderr.log').write_text(run.stderr,encoding='utf-8')
        if run.returncode:raise AssertionError(f'Production verify exit {run.returncode}: '+run.stderr+' '+run.stdout[-1500:])
        row=json.loads(run.stdout.splitlines()[-1]);row.update(command=command,exit_code=run.returncode,manifest_sha256=sha(moved/'release.json'))
        result['cases'].append(row);result['producer_native_approval_executed']=True
        result['scope']='isolated relocated import/help, real producer approvals and actual portable file verification'
        Release(moved,sha(moved/'release.json')).verify_all()
        result['inputs_unchanged']=all(sha(p)==h for p,h in result['sources'].items()) and all(sha(p)==h for p,h in result['private'].items())
        if not result['inputs_unchanged']:raise AssertionError('Source/dependency changed during test')
        result.update(result='PASS',tests=len(result['cases']))
    except BaseException as exc:
        result['error']=repr(exc)
    result['artifacts']={str(p.relative_to(folder)):sha(p) for p in sorted(folder.rglob('*')) if p.is_file()}
    (folder/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(dict(result=result['result'],tests=result.get('tests'),path=str(folder/'result.json'))))
    return 0 if result['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())

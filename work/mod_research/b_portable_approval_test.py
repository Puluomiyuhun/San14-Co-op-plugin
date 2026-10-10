"""Owned relocated release/child Python tests; no process, Steam or native calls.

Real frozen approval call sites are imported from the copied source closure.
Native assets and producer receipts are explicitly synthetic. They are suitable
only for testing release selection/path bindings, never for live installation.
"""
from copy import deepcopy
from datetime import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
from portable_release import write_bundle,Release
from b_portable_release_export import python_closure
from b_portable_approval import FAMILIES,NAMES

OUTPUT=None;SOURCES={};ROWS=[]


CHILD=r'''
import builtins,hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]);digest=sys.argv[2];case=sys.argv[3]
sys.path[:0]=[str(root/'repo/work/mod_research'),str(root/'repo/outputs/san14-link')]
from portable_release import Release
import b_portable_approval as a
import b_remote_session as s
import b_observed_start as start
import b_reward_runner as runner
import b_simple_remote_guest as guest
import b_warm_coordinator as warm
import b_warm_start as state
import b_reward_native_port as reward
import player_input_lease_bootstrap_port as inputs
import checkpoint_complete_live_capture as capture
import b_warm_start_support as support
import a_runtime_reward_port as common

def need(v,m):
 if not v:raise AssertionError(m)
def denied(fn,part):
 try:fn()
 except (ValueError,RuntimeError) as e:
  need(part in str(e),repr(e));return
 raise AssertionError('expected refusal: '+part)

r=Release(root,digest);b=a.FileApprovalBindings(r)
originals=[(m,n,getattr(m,n)) for m,n,_ in a._BINDINGS]
untouched=[(builtins,'open',builtins.open),(Path,'open',Path.open),(Path,'resolve',Path.resolve),
 (capture,'module_approval',capture.module_approval),(capture,'process_birth',capture.process_birth),
 (support,'storage_bindings',support.storage_bindings),(support,'live_hook_evidence',support.live_hook_evidence),
 (state,'refuse_prior_attempt',state.refuse_prior_attempt),(state,'PRIVATE',state.PRIVATE),
 (s.Session,'open',s.Session.open.__func__),(reward.NativePort,'open',reward.NativePort.open.__func__),
 (inputs,'window_identity',inputs.window_identity),(common.RemoteTransport,'_identity',common.RemoteTransport._identity)]
def unchanged():
 for m,n,f in untouched:
  current=getattr(m,n);current=getattr(current,'__func__',current)
  need(current is f,'changed non-file-approval: '+n)
def params(name):
 c=r.metadata['components'][name];p=r.resolve(c['producer_provenance']);return p,c['producer_result_sha256']

if case=='full-call-sites':
 with b:
  unchanged()
  for f in (s.verify_sources,start.verify_sources,runner.verify_sources,guest.verify_sources):f(b.source_pins)
  pp,ph=params('pair');hp,hh=params('helper')
  for f in (s.approved_builds,start.approved_builds,guest.approved_builds):
   pair,helper=f(pp,ph,hp,hh)
   need(pair['approval_kind']=='producer_verified_release' and pair['private_archive_revalidated'] is False,'false provenance')
   need(pair['sources']==helper['sources'],'owned shared native source mismatch')
   need(Path(pair['production_dll']['path']).is_relative_to(root),'escaped runtime')
  rp,rh=params('reward');ip,ih=params('input')
  owner=reward.approved_build(reward.NativeBuild(rp.parent,rh))
  need(owner['dll'].name=='b_reward_owner.dll' and len(owner['dependencies'])==1,'owner view wrong')
  dll,h=inputs.approved(inputs.Build(ip.parent,ih));need(dll.name=='player_input_lease_bootstrap.dll','input view wrong')
  need(s.Session.open.__func__.__globals__['verify_sources']==s.verify_sources,'Session global bypass')
  need(reward.NativePort.open.__func__.__globals__['approved_build']==reward.approved_build,'reward open bypass')
  need(inputs.bootstrap.__globals__['approved']==inputs.approved,'input bootstrap bypass')
  need(runner.Runner.run.__globals__['preflight'].__globals__['verify_sources']==start.verify_sources,'star-import preflight bypass')
  unchanged()
elif case=='foreign-result':
 with b:
  pp,ph=params('pair');hp,hh=params('helper')
  denied(lambda:s.approved_builds(pp,'0'*64,hp,hh),'does not belong')
  denied(lambda:b.approved_component(hp,hh,a.FAMILIES['pair']),'does not belong')
  denied(lambda:b.approved_component(pp,ph,'unapproved-family'),'Only retained')
elif case=='partial-source-manifest':
 with b:
  pins=b.source_pins;pins.pop(next(iter(pins)))
  denied(lambda:s.verify_sources(pins),'complete selected release')
elif case=='nested-and-replay':
 with b:
  c=a.FileApprovalBindings(r)
  denied(lambda:c.__enter__(),'Another portable')
 denied(lambda:b.__enter__(),'cannot be replayed')
elif case=='source-drift':
 with b:
  p=r.resolve('repo/work/mod_research/b_remote_session.py');old=p.read_bytes()
  try:
   p.write_bytes(old+b'\n# owned drift\n')
   denied(lambda:s.verify_sources(b.source_pins),'asset changed')
  finally:p.write_bytes(old)
elif case=='prior-binding':
 old=guest.verify_sources;guest.verify_sources=lambda _:None
 try:denied(lambda:b.__enter__(),'Unexpected prior')
 finally:guest.verify_sources=old
elif case=='exception-restores':
 try:
  with b:raise RuntimeError('owned primary exception')
 except RuntimeError as e:need(str(e)=='owned primary exception','primary exception lost')
elif case=='foreign-project-import':
 import importlib.util
 foreign=root.parent/'foreign'/'game_reader.py';foreign.parent.mkdir()
 foreign.write_bytes(r.resolve('repo/outputs/san14-link/game_reader.py').read_bytes())
 spec=importlib.util.spec_from_file_location('owned_foreign_reader',foreign)
 module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module
 try:
  spec.loader.exec_module(module)
  denied(lambda:b.__enter__(),'Foreign imported project source')
 finally:sys.modules.pop(spec.name,None)
else:raise AssertionError(case)
for m,n,f in originals:need(getattr(m,n) is f,'file binding not restored')
unchanged()
print(json.dumps(dict(case=case,passed=True,approval_kind='producer_verified_release',
 original_dynamic_checks_unchanged=True,process_calls=0,native_calls=0)))
'''


class Cases(unittest.TestCase):
    def setUp(self):
        self.folder=OUTPUT/self._testMethodName;self.folder.mkdir()

    def bundle(self,*,missing_shared=False):
        assets=[]
        def asset(path,raw,role):
            file=self.folder/'inputs'/path;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(raw)
            h=hashlib.sha256(raw).hexdigest();assets.append(dict(source=file,path=path,sha256=h,role=role));return h
        pins={}
        # Actual transitive source modules, including file-loader dependencies.
        for path,digest in SOURCES.items():
            relative='repo/'+path.relative_to(ROOT).as_posix()
            assets.append(dict(source=path,path=relative,sha256=digest,role='source'));pins[relative]=digest
        header='repo/work/mod_research/owned_portable_handover.h'
        pins[header]=asset(header,b'// owned synthetic shared header\n','source')
        components={}
        for name,family in FAMILIES.items():
            original=dict(result='PASS',family=family,inputs_unchanged=True,game_access=False,
                          refresh_factory_pair_passed=name=='pair',sources={'X:/producer-only/owned_portable_handover.h':pins[header]},
                          private={'X:/not-distributed/game-archive.bin':'e'*64})
            record='native/'+name+'/result.json';h=asset(record,(json.dumps(original)+'\n').encode(),'provenance')
            dll='native/'+name+'/'+NAMES[name];dh=asset(dll,('OWNED NONEXECUTABLE '+name).encode(),'native')
            subset={header:pins[header]}
            if missing_shared and name=='pair':subset={next(iter(pins)):pins[next(iter(pins))]}
            row=dict(family=family,producer_provenance=record,producer_result_sha256=h,
                     production_dll=dll,production_sha256=dh,source_pins=subset,
                     producer_approval_verified=True,recipient_native_execution_verified=False)
            if name=='reward':
                dep='native/reward/checkpoint_planning_hold.dll'
                row['dependencies']=[dict(path=dep,sha256=asset(dep,b'OWNED NONEXECUTABLE DEPENDENCY','native'))]
            components[name]=row
        stage='native/rules/production.dll';publisher='native/rules/publisher-production.exe'
        components['rules']=dict(stage=stage,publisher=publisher,stage_sha256=asset(stage,b'OWNED RULES','native'),
                                 publisher_sha256=asset(publisher,b'OWNED PUBLISHER','native'))
        metadata=dict(kind='san14.b-portable-assets.v1',components=components,source_pins=pins,
                      producer_provenance_only=True,recipient_native_execution_verified=False)
        return write_bundle(self.folder/'relocated-package',assets,metadata)

    def child(self,case):
        result=self.bundle();script=self.folder/'child.py';script.write_text(CHILD,encoding='utf-8')
        env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1'
        # External installed libraries remain outside managed source approval.
        env['PYTHONPATH']=str(PRIVATE/'python_deps')
        cmd=[sys.executable,'-B',str(script),result['root'],result['manifest_sha256'],case]
        run=subprocess.run(cmd,cwd=self.folder,env=env,capture_output=True,text=True,encoding='utf-8',timeout=45)
        (self.folder/'stdout.log').write_text(run.stdout,encoding='utf-8');(self.folder/'stderr.log').write_text(run.stderr,encoding='utf-8')
        self.assertEqual(run.returncode,0,run.stderr)
        row=json.loads(run.stdout.splitlines()[-1]);self.assertTrue(row['passed'])
        Release(result['root'],result['manifest_sha256']).verify_all()
        ROWS.append(dict(**row,release_sha256=result['manifest_sha256'],own_child=True,native_assets='NONEXECUTABLE_TEST_BYTES'))

    def test_actual_aliases_and_dynamic_calls_from_relocated_sources(self):self.child('full-call-sites')
    def test_foreign_receipt_family_and_digest_refused(self):self.child('foreign-result')
    def test_source_subset_refused(self):self.child('partial-source-manifest')
    def test_nested_lifetime_and_reentry_refused(self):self.child('nested-and-replay')
    def test_source_drift_before_next_approval_refused(self):self.child('source-drift')
    def test_foreign_previous_function_binding_refused(self):self.child('prior-binding')
    def test_original_exception_restores_file_functions(self):self.child('exception-restores')
    def test_byte_identical_foreign_import_refused(self):self.child('foreign-project-import')
    def test_component_shared_source_membership_preserved(self):
        result=self.bundle(missing_shared=True)
        from b_portable_approval import FileApprovalBindings
        with self.assertRaisesRegex(ValueError,'do not share'):FileApprovalBindings(Release(result['root'],result['manifest_sha256']))


if __name__=='__main__':
    OUTPUT=PRIVATE/'b_portable_approval_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    SOURCES,external,dynamic=python_closure([HERE/'b_portable_approval.py'])
    before={str(path):digest for path,digest in SOURCES.items()}
    # Include the test and actual collector/core used to assemble owned packages.
    for name in ('b_portable_approval_test.py','b_portable_release_export.py','portable_release.py'):
        path=HERE/name;before[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8')
    stable=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in before.items())
    result=dict(result='PASS' if r.wasSuccessful() and stable else 'FAIL',tests=r.testsRun,sources=before,sources_unchanged=stable,
                game_access=False,steam_access=False,process_calls=0,native_calls=0,own_python_children=True,
                synthetic_producer_receipts=True,native_assets_nonexecutable=True,cases=ROWS,
                declared_external_dependencies=external,dynamic_source_closure=dynamic,
                failures=[(str(t),d) for t,d in r.errors+r.failures])
    result['artifacts']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(stream.getvalue());print(OUTPUT/'result.json');raise SystemExit(result['result']!='PASS')

"""Offline launcher audit and fake-kernel buffer tests; never opens a process."""
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import argparse
import ast
import copy
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import struct

ROOT=Path(__file__).resolve().parent
RUNS=('20261006-211028-162474','20261006-211040-957998')


def sha(data):return hashlib.sha256(data).hexdigest()


def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def encode_report(api,value):
    r=api['Report']()
    for key,_ in r._fields_:
        v=value[key]
        if key=='bridge':
            for sub,n in v.items():setattr(r.bridge,sub,n)
        elif key in ('expectedSha256','localSha256'):
            getattr(r,key)[:]=bytes.fromhex(v)
        elif key=='nativeSha256':
            for i,item in enumerate(v):r.nativeSha256[i][:]=bytes.fromhex(item)
        elif key in ('sizes','readReturns'):getattr(r,key)[:]=v
        elif key=='stage':r.stage=v.encode('ascii')
        else:setattr(r,key,v)
    return bytes(r)


class FakeKernel:
    def __init__(self,raw,*,wait=0,create=True,exit_code=0,read_error=False):
        self.raw=raw;self.wait=wait;self.create=create;self.exit_code=exit_code;self.read_error=read_error
        self.frees=[];self.closed=[];self.reads=0
    def VirtualAllocEx(self,*args):return 0x12340000
    def CreateRemoteThread(self,*args):return 91 if self.create else 0
    def WaitForSingleObject(self,*args):return self.wait
    def GetExitCodeThread(self,thread,pointer):C.cast(pointer,C.POINTER(W.DWORD)).contents.value=self.exit_code;return True
    def CloseHandle(self,handle):self.closed.append(handle);return True
    def VirtualFreeEx(self,process,pointer,*args):self.frees.append(pointer);return True
    def read(self,at,size):
        self.reads+=1
        if self.read_error:raise OSError('synthetic read failure')
        assert at==0x12340000 and size==520
        return self.raw


def run(launcher_path):
    source=launcher_path.read_bytes()
    # Execute definitions from these exact saved bytes. __main__ is never run;
    # the module has no process API construction outside main/precheck.
    target={'__name__':'offline_launcher_audit_target','__file__':str(launcher_path)}
    exec(compile(source,str(launcher_path),'exec'),target)
    cases=[]
    def check(name,condition):
        assert condition,name
        cases.append({'case':name,'passed':True})
    class Config(C.Structure):
        _fields_=[('magic',C.c_uint64),('size',C.c_uint32),('version',C.c_uint32),('mode',C.c_uint32),('pid',C.c_uint32),
                  ('birth',C.c_uint64),('base',C.c_uint64),('user',C.c_uint64),('path',C.c_wchar*512),('reserved',C.c_uint64*4)]
    check('config1104_offsets',C.sizeof(Config)==1104 and Config.path.offset==48 and Config.reserved.offset==1072)
    check('report520_key_offsets',C.sizeof(target['Report'])==520 and all(getattr(target['Report'],k).offset==v for k,v in
          {'state':16,'base':40,'observedSlot':136,'sizes':160,'readReturns':172,'storage':208,
           'expectedSha256':248,'nativeSha256':312,'stage':376,'bridge':440,'bridgeDrainedSnapshot':504,'fullWorldVerified':516}.items()))
    config=struct.pack('<QIIIIQQQ',target['MAGIC'],1104,1,1,53908,134355726122897449,0x7ff749440000,0x201b58bc130)+bytes(1024+32)
    parsed=Config.from_buffer_copy(config)
    check('config_pack_matches_header',parsed.mode==1 and parsed.pid==53908 and parsed.birth==134355726122897449 and parsed.user==0x201b58bc130)

    from checkpoint_push_contract import compare_known_coverage
    verified=[]
    results=[]
    for name in RUNS:
        folder=ROOT/'native_file_identity_runs'/name;r=load(folder/'result.json');trace=load(folder/'trace.json')
        before=load(folder/'known-before.json');after=load(folder/'known-after.json')
        check(name+'_report_ok',r['result']=='PASS' and target['report_ok'](r['adapter'],int(r['mode']=='read'),r['before']))
        check(name+'_two_equal_terminal_reports',len(trace)>=2 and trace[-1]['adapter']==trace[-2]['adapter']==r['adapter'])
        check(name+'_coverage_and_files',compare_known_coverage(before,after)['matched'] and before['save_files']==after['save_files'])
        b=int(r['before']['base'],0)
        check(name+'_actual_hook_slots_pages',r['actual_hook_slots_restored'] and r['hook_slots_after']=={'user':b+0x3F9B00,'save':b+0x4AA650}
              and r['hook_pages_after']==r['before']['hook_pages'])
        check(name+'_decode_roundtrip',target['decode'](encode_report(target,r['adapter']))==r['adapter'])
        verified.append({'run':name,'result_sha256':sha((folder/'result.json').read_bytes()),'trace_sha256':sha((folder/'trace.json').read_bytes()),
                         'report_size':520,'mode':r['mode'],'read_calls':r['adapter']['readCalls'],'sizes':r['adapter']['sizes'],
                         'native_sha256':r['adapter']['nativeSha256'],'final_two_reports_equal':True,'coverage_and_files_unchanged':True})
        results.append(r)
    check('dry_read_same_process_lifetime',all(results[0]['after'][k]==results[1]['before'][k] for k in ('pid','process_birth','base','pinned_user','pinned_game','pinned_world','global_rng','cache_mode','cache_slots')))
    a=load(ROOT/'checkpoint_push_runs/20261006-203111-687580/known-after.json')
    dry_before=load(ROOT/'native_file_identity_runs'/RUNS[0]/'known-before.json')
    source_comparison=compare_known_coverage(a,dry_before)
    check('historical_A_export_to_dry_business_equal',source_comparison['matched'])
    check('read_count_size_sha',results[1]['adapter']['readCalls']==2 and results[1]['adapter']['readReturns']==[274880,274880]
          and results[1]['adapter']['nativeSha256']==[target['SHA']]*2)

    raw=encode_report(target,results[1]['adapter'])
    for name,kwargs,should_raise,free_expected in (
        ('success',{},False,True),('wait_timeout',{'wait':258},True,False),('wait_failed',{'wait':0xffffffff},True,False),
        ('thread_creation_failed',{'create':False},True,True),('remote_exit_error',{'exit_code':1},True,True),
        ('report_read_error',{'read_error':True},True,True),('decode_error',{},True,True)):
        kernel=FakeKernel(bytes(520) if name=='decode_error' else raw,**kwargs)
        api=SimpleNamespace(k=kernel,handle=11);reader=SimpleNamespace(memory=SimpleNamespace(read=kernel.read))
        failed=False
        try:value=target['get_report'](api,reader,0x50000)
        except (AssertionError,OSError):failed=True
        check('buffer_'+name,failed==should_raise and bool(kernel.frees)==free_expected
              and len(kernel.closed)==int(kernel.create))
    # Static/pure demonstration of the original timeout-gate edge. No main(),
    # thread or API is executed: evaluate only the final boolean expression.
    tree=ast.parse(source)
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    passed=next(n.value for n in ast.walk(main) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='passed' for t in n.targets))
    names={n.id for n in ast.walk(passed) if isinstance(n,ast.Name)}
    env={'installed':0,'report_ok':target['report_ok'],'value':results[1]['adapter'],'args':SimpleNamespace(read=True),
         'before':results[1]['before'],'restored':True,'after':{'result':'PASS'},'coverage':{'matched':True},'files_equal':True,'stable_terminal':False}
    bypass=bool(eval(compile(ast.Expression(passed),str(launcher_path),'eval'),env))
    # Record, do not weaken current code or convert actual passing runs to failure.
    return {'schema':'san14.native-file-launcher-offline-audit.v1','result':'PASS_WITH_PREEXISTING_FAILURE_PATH_GAPS',
            'reviewed_launcher':str(launcher_path),'reviewed_launcher_sha256':sha(source),
            'reviewed_fixture_gate_sha256':sha((ROOT/'native_file_identity_fixture_gate.py').read_bytes()),
            'cases':cases,'case_count':len(cases),'actual_runs':verified,'A_export_to_dry_coverage':source_comparison,
            'terminal_gate_edge':{'final_pass_expression_requires_stable_terminal':'stable_terminal' in names,
                                  'can_accept_good_first_terminal_on_deadline':bypass,
                                  'affected_actual_runs':False,'actual_both_runs_last_two_reports_equal':True},
            'findings':[
                'Original final passed expression omits stable_terminal. A deadline at the first good terminal report can bypass the intended two-sample condition. Actual two runs each have two equal terminal reports.',
                'Original precheck binds source identity/RNG/cache; it does not itself compare the complete known source capture. The actual A-export-to-dry known captures independently match; allocator pool changes are disclosed.',
                'Original BaseException path suppresses Stop/GetReport cleanup exceptions and saves only the primary error, so failed cleanup is not independently evidenced. Successful runs separately verified real hook slots/pages.',
                'CREATE_NEW-style x-mode once files block ordinary reruns. The Python journal writer closes but does not fsync; durable crash-surviving intent is not independently established.',
            ],
            'root_followup':'Parent is archiving old launcher/gate and tightening gates/evidence only; no actual once is rerun and old results are preserved.',
            'scope':'ctypes ABI + fake-kernel report-buffer lifetime + saved actual reports/captures. No game/process access, native call, DLL load or new observation.',
            'game_access':False,'changes_to_launcher':False,'future_load_byte_identity_proven':False}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--launcher',type=Path,default=ROOT/'native_file_identity_start.py');args=p.parse_args()
    report=run(args.launcher.resolve())
    output=ROOT/('native_file_identity_launcher_audit_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
    with output.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps({'result':report['result'],'cases':report['case_count'],'output':str(output),'reviewed_launcher_sha256':report['reviewed_launcher_sha256'],'game_access':False}))

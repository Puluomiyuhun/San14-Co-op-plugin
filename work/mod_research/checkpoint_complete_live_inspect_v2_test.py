"""Self-contained file/transport doubles; never opens a game or process handle."""
import ctypes as C
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import checkpoint_complete_live_inspect_v2 as subject
import checkpoint_complete_live_owner_contract as abi


def write(path, value):
    path.write_text(json.dumps(value), encoding='utf8')


class CallError(RuntimeError):
    def __init__(self, *, completed=False, started=True, cleanup=()):
        super().__init__('mock remote outcome')
        self.completed, self.may_have_started, self.cleanup_errors = completed, started, list(cleanup)


class Fixture:
    def __init__(self, root):
        self.root = root
        self.run = root / 'checkpoint_complete_live_runs' / 'owned-fixture'
        self.run.mkdir(parents=True)
        shutil.copyfile(P / 'checkpoint_complete_live_owner_contract.py', root / 'checkpoint_complete_live_owner_contract.py')
        self.dll = b'owned fake PE; transport itself is a double'
        self.policy = subject.Policy(root, subject.digest(self.dll), subject.APPROVED_CONTRACT)
        self.claim_path = root / 'checkpoint_complete_live_once.json'
        self.claim = dict(run=str(self.run), pid=999, birth=1234, base=0x140000000,
            attempt=4567, epoch=8901, generation=4567, attachment='aa'*32,
            owner_binding='bb'*32, dll_sha256=self.policy.dll_sha,
            target_sha256='cc'*32, target=str(self.run/'svdexccSC03.s14'))
        self.result = dict(self.claim, schema='san14.complete-live-load.v1',
            result='PASS_NATIVE_LOAD_IDENTITY_PLANNING', install_completed=True,
            install_exit=0, control_lifetime_uncertain=False)
        self.description = abi.Description()
        self.description.magic, self.description.size, self.description.version = abi.MAGIC, abi.DESCRIPTION_SIZE, 1
        self.description.configSize, self.description.reportSize = abi.CONFIG_SIZE, abi.REPORT_SIZE
        self.description.valueCount, self.description.module = len(abi.VALUE_NAMES), 0x70000000
        for i in range(4): self.description.dispatchBridge[i] = 0x70001000 + 0x100*i
        self.description.workerBridge, self.description.readBridge, self.description.authorizedForward = 0x70002000,0x70002100,0x70002200
        self.cfg = abi.Config()
        for key in ('pid', 'birth', 'base', 'attempt', 'epoch', 'generation'): setattr(self.cfg, key, self.claim[key])
        self.cfg.attachment[:] = bytes.fromhex(self.claim['attachment'])
        self.cfg.ownerBinding[:] = bytes.fromhex(self.claim['owner_binding'])
        self.cfg.gameSha256[:] = bytes.fromhex(subject.GAME_SHA)
        self.cfg.localPath = self.claim['target']
        self.cfg.storageModuleCount = 3
        self.cfg.storageModules[2].base = self.description.module
        self.cfg.storageModules[2].fileSha256[:] = bytes.fromhex(self.policy.dll_sha)
        self.cfg.storageModules[2].headerSha256[:] = b'\x55' * 32
        self.cfg.ownedReadBridge.address = self.description.readBridge
        self.raw = abi.Report()
        self.raw.magic, self.raw.size, self.raw.version = abi.MAGIC, abi.REPORT_SIZE, 1
        self.raw.attempt, self.raw.epoch = self.claim['attempt'], self.claim['epoch']
        self.calls = []; self.opens = 0; self.closes = 0
        self.on_open = None; self.on_call = None
        self.persist()

    def persist(self):
        write(self.claim_path, self.claim)
        write(self.run/'result.json', self.result)
        write(self.run/'description.json', abi.decode_description(bytes(self.description)))
        write(self.run/'trace.json', [])
        write(self.run/'bindings.json', dict(config_sha256=subject.digest(bytes(self.cfg))))
        (self.run/'config.bin').write_bytes(bytes(self.cfg))
        (self.run/'checkpoint_complete_live_owner.dll').write_bytes(self.dll)

    def factory(self, claim, copied, description, mapped_header_sha):
        self.opens += 1
        if self.on_open: self.on_open()
        def call(name, size):
            self.calls.append(name)
            if self.on_call: self.on_call(name)
            return 0, bytes(self.description) if name == subject.DESCRIBE else bytes(self.raw)
        def close(): self.closes += 1
        return SimpleNamespace(call=call, close=close)

    def inspect(self, live=False):
        return subject.inspect(self.claim_path, live=live, policy=self.policy, transport_factory=self.factory)[0]


def run(case, root):
    f = Fixture(root)
    if case == 'offline-never-opens-process':
        r=f.inspect(); assert r['result']=='FILES_ONLY_SUMMARY' and f.opens==0 and f.calls==[]
    elif case == 'running-result-absent':
        (f.run/'result.json').unlink(); r=f.inspect(True); assert not r['eligible_for_live_report'] and f.opens==0
    elif case == 'missing-uncertainty-refused':
        del f.result['control_lifetime_uncertain'];f.persist();r=f.inspect(True);assert f.opens==0
    elif case == 'nested-uncertainty-refused':
        f.result['control_log']={'control_lifetime_uncertain':True};f.persist();r=f.inspect(True);assert f.opens==0
    elif case == 'cleanup-unknown-refused':
        f.result['control_cleanup_errors']=['BUFFER_RELEASE_UNCERTAIN'];f.persist();r=f.inspect(True);assert f.opens==0
    elif case == 'install-not-complete-refused':
        f.result['install_completed']=False;f.persist();r=f.inspect(True);assert f.opens==0
    elif case == 'claim-result-binding-mismatch':
        f.result['epoch']+=1;f.persist();r=f.inspect(True);assert f.opens==0
    elif case == 'copied-dll-changed':
        (f.run/'checkpoint_complete_live_owner.dll').write_bytes(b'changed');r=f.inspect(True);assert f.opens==0
    elif case == 'config-binding-mismatch':
        f.cfg.attempt+=1;f.persist();r=f.inspect(True);assert f.opens==0
    elif case == 'two-fixed-exports-one-get-report':
        r=f.inspect(True);assert r['result']=='REPORT_OBSERVED_NO_READINESS_AUTHORITY'
        assert f.calls==[subject.DESCRIBE,subject.GET_REPORT] and f.closes==1
        assert not r['ready_authorized'] and not r['full_world_verified']
        again=f.inspect(True);assert again['result']=='REFUSED_OR_UNCERTAIN' and f.opens==1
    elif case == 'wrong-process-or-module-refused':
        def fail(): raise RuntimeError('mock PID birth or exact module mismatch')
        f.on_open=fail;r=f.inspect(True);assert f.calls==[] and r['result']=='REFUSED_OR_UNCERTAIN'
    elif case == 'describe-timeout-no-report-or-stop':
        def fail(name): raise CallError()
        f.on_call=fail;r=f.inspect(True);assert f.calls==[subject.DESCRIBE] and r['control_lifetime_uncertain']
        assert f.closes==1 and f.inspect(True)['result']=='REFUSED_OR_UNCERTAIN' and f.opens==1
    elif case == 'get-report-timeout-no-followup':
        def fail(name):
            if name==subject.GET_REPORT: raise CallError()
        f.on_call=fail;r=f.inspect(True);assert f.calls==[subject.DESCRIBE,subject.GET_REPORT] and r['control_lifetime_uncertain']
    elif case == 'describe-completed-cleanup-error-stops':
        def fail(name): raise CallError(completed=True,cleanup=['BUFFER_RELEASE_FAILED'])
        f.on_call=fail;r=f.inspect(True);assert f.calls==[subject.DESCRIBE] and not r['control_lifetime_uncertain']
        assert r['native_calls'][0]['cleanup_errors'] and r['result']=='REFUSED_OR_UNCERTAIN'
    elif case == 'evidence-drift-between-exports':
        def drift(name):
            if name==subject.DESCRIBE: write(f.run/'result.json', dict(f.result, changed=True))
        f.on_call=drift;r=f.inspect(True);assert f.calls==[subject.DESCRIBE] and r['result']=='REFUSED_OR_UNCERTAIN'
    elif case == 'report-other-attempt-refused':
        f.raw.attempt+=1;r=f.inspect(True);assert r['result']=='REFUSED_OR_UNCERTAIN' and 'report' not in r
    elif case in ('prior-v1-unknown-refused','prior-v1-precall-refusal-allowed'):
        old=f.root/'checkpoint_complete_live_inspections';where=old/'prior';where.mkdir(parents=True)
        write(old/('live-%d-%d.once.json'%(f.claim['attempt'],f.claim['epoch'])),dict(binding=f.claim,inspection=str(where)))
        unknown=case=='prior-v1-unknown-refused'
        write(where/'inspection.json',dict(control_lifetime_uncertain=unknown,native_calls=[]))
        r=f.inspect(True)
        assert (f.opens==0 and r['result']=='REFUSED_OR_UNCERTAIN') if unknown else (f.opens==1 and r['result']=='REPORT_OBSERVED_NO_READINESS_AUTHORITY')
    else: raise AssertionError(case)
    assert not r['new_load_requested'] and not r['stop_requested'] and not r['restore_requested'] and not r['unload_requested']
    # Only the fixture writes these original evidence files; inspect never does.
    return dict(case=case,result='PASS',inspector_result=r['result'],remote_exports=f.calls)


CASES=('offline-never-opens-process','running-result-absent','missing-uncertainty-refused',
    'nested-uncertainty-refused','cleanup-unknown-refused','install-not-complete-refused',
    'claim-result-binding-mismatch','copied-dll-changed','config-binding-mismatch',
    'two-fixed-exports-one-get-report','wrong-process-or-module-refused',
    'describe-timeout-no-report-or-stop','get-report-timeout-no-followup',
    'describe-completed-cleanup-error-stops','evidence-drift-between-exports','report-other-attempt-refused',
    'prior-v1-unknown-refused','prior-v1-precall-refusal-allowed')


def production_transport_with_owned_pe():
    """Real approved PE parser + actual transport.verify; OS reads are buffers."""
    sys.path.insert(0,str(P/'python_deps'))
    import pefile
    copied=P/'checkpoint_complete_live_owner.dll'
    assert subject.digest(copied.read_bytes())==subject.APPROVED_DLL
    pe=pefile.PE(str(copied));mapped=bytearray(pe.get_memory_mapped_image())
    module=0x70000000
    offset=pe.OPTIONAL_HEADER.get_field_absolute_offset('ImageBase');pe.close()
    mapped[offset:offset+8]=module.to_bytes(8,'little')
    mapped_sha=subject.digest(mapped[:4096])
    desc=dict(module=module,dispatchBridge=[module+0x1100+i*0x100 for i in range(4)],
        workerBridge=module+0x2100,readBridge=module+0x2200,authorizedForward=module+0x2300)
    claim=dict(pid=999,birth=1234,base=0x140000000,dll_sha256=subject.APPROVED_DLL)
    handles=[];read_calls=[]
    def read(address,size):
        read_calls.append((address,size));return bytes(mapped[address-module:address-module+size])
    reader=SimpleNamespace(sha256=subject.GAME_SHA,memory=SimpleNamespace(base=claim['base'],read=read),close=lambda:handles.append('reader'))
    api=SimpleNamespace(k=None,handle='mock-control-handle',modules=lambda:[(module,copied)],close=lambda:handles.append('api'))
    def birth(obj):return claim['birth']
    with patch.dict(sys.modules,{
        'game_reader':SimpleNamespace(GameReader=lambda **kw:reader),
        'run_autonomous_pilot':SimpleNamespace(ProcessAPI=lambda _:api,pefile=pefile),
        'checkpoint_push_start':SimpleNamespace(process_birth=birth),
        'checkpoint_complete_live_capture':SimpleNamespace(readable=lambda *a,**kw:None)}):
        transport=subject.LiveTransport(claim,copied,desc,mapped_sha)
        assert (module,4096) in read_calls  # exact installed mapped header, with ASLR ImageBase
        mapped[0]=0
        try:transport.verify();raise AssertionError('Changed header accepted')
        except RuntimeError as exc:assert str(exc)=='Mapped PE header differs from installed binding'
        transport.close()
    assert handles==['api','reader']
    return dict(case='production-transport-ASLR-mapped-header-owned-memory',result='PASS',
                scope='real PE/export/header/code verifier with fake WinAPI/owned byte buffer')


def main():
    folder=P/'checkpoint_complete_live_inspect_v2_tests'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    sources={str(p):subject.digest(p.read_bytes()) for p in (Path(__file__),Path(subject.__file__),Path(abi.__file__))}
    results=[]
    with tempfile.TemporaryDirectory(prefix='owned-inspection-',dir=folder) as temp:
        for i,case in enumerate(CASES): results.append(run(case,Path(temp)/str(i)))
    results.append(production_transport_with_owned_pe())
    assert sources=={p:subject.digest(Path(p).read_bytes()) for p in sources}
    report=dict(schema='san14.complete-live-inspect-v2-tests.v1',result='PASS',cases=results,
        source_sha256=sources,real_processes_opened=0,game_accessed=False,
        coverage='stdlib artifacts and ABI decode with mocked transport; production Windows attachment not run')
    subject.save_new(folder/'result.json',report)
    print(json.dumps(dict(result='PASS',cases=len(results),path=str(folder/'result.json'))))


if __name__=='__main__':main()

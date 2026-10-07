"""Cross-process protocol exercise: target and cover are both our own fixtures."""
from pathlib import Path
from datetime import datetime
import hashlib,json,queue,subprocess,threading,time,traceback
ROOT=Path(__file__).resolve().parent
SESSION='1'*32;ATTACHMENT='2'*32;VIEW='3'*32;NEW='4'*32
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
class Process:
    def __init__(self,name,folder):
        self.p=subprocess.Popen([str(ROOT/name)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',bufsize=1)
        self.q=queue.Queue();self.log=[];self.folder=folder;self.events=[];self.serial=0
        def reader():
            for line in self.p.stdout:
                try:self.q.put(json.loads(line))
                except Exception:self.q.put({'invalid_stdout':line})
        self.thread=threading.Thread(target=reader,daemon=True);self.thread.start();self.ready=self.take()
    def take(self,timeout=8):
        value=self.q.get(timeout=timeout);self.log.append({'receive':value});return value
    def send(self,op,**fields):
        self.serial+=1;request={'id':str(self.serial),'op':op,**fields};self.log.append({'send':request});self.p.stdin.write(json.dumps(request)+'\n');self.p.stdin.flush()
        until=time.monotonic()+8
        while time.monotonic()<until:
            response=self.take(max(.1,until-time.monotonic()))
            if response.get('id')==request['id']:return response
            self.events.append(response)
        raise TimeoutError(op)
    def event(self,reason,timeout=8):
        for event in self.events:
            if event.get('hold_reason')==reason:return event
        until=time.monotonic()+timeout
        while time.monotonic()<until:
            value=self.take(max(.1,until-time.monotonic()))
            if value.get('hold_reason')==reason:return value
        raise TimeoutError(reason)
    def cleanup(self):
        if self.p.poll() is None:
            try:
                if self.p.stdin and not self.p.stdin.closed:self.p.stdin.close()
                self.p.wait(timeout=.3)
            except subprocess.TimeoutExpired:self.p.terminate();self.p.wait(timeout=3)
        self.thread.join(timeout=1);self.folder.mkdir(parents=True,exist_ok=True)
        (self.folder/'protocol.json').write_text(json.dumps(self.log,indent=2)+'\n');(self.folder/'stderr.txt').write_text(self.p.stderr.read())
def own_capture(binding,folder):
    # These bindings are returned by children launched in this test and checked
    # against Popen.pid. The prepared read-only CLI is never aimed at SAN14.
    p=subprocess.run([str(ROOT/'checkpoint_map_cover_probe.exe'),'--capture',str(binding['hwnd']),str(binding['pid']),str(binding['birth']),binding['class'],str(folder)],capture_output=True,text=True,timeout=8)
    assert p.returncode==0,(p.stdout,p.stderr)
    report=json.loads((folder/'result.json').read_text());assert report['result']=='PASS';return report
def pair(out,case):
    target=Process('checkpoint_map_wait_helper_fixture.exe',out/case/'target');helper=None
    try:
        ready=target.ready;assert ready['event']=='FIXTURE_READY' and int(ready['pid'])==target.p.pid and ready['class']=='CheckpointMapWaitHelperFixture'
        helper=Process('checkpoint_map_wait_helper.exe',out/case/'helper');assert helper.ready['event']=='READY_NO_TARGET' and int(helper.ready['helper_pid'])==helper.p.pid
        bind=dict(session=SESSION,hwnd=ready['hwnd'],pid=int(ready['pid']),birth=ready['birth'],**{'class':ready['class']},attachment=ATTACHMENT,view=VIEW,window_mode='borderless',idle_timeout_ms=1500 if case=='idle_timeout' else 15000)
        if case=='wrong_birth':
            bind['birth']=str(int(bind['birth'])+1);rejected=helper.send('bind',**bind);assert not rejected['ok'] and rejected['phase']=='NEW';assert helper.send('stop',session=SESSION)['ok'];return {'case':case,'passed':True,'no_cover_created':True}
        assert helper.send('bind',**bind)['ok'];cover=helper.send('cover',session=SESSION);assert cover['ok'] and cover['phase']=='COVERED' and cover['cover_window_visible'] and not cover['input_gate_provided'];assert int(cover['cover_activations'])==0
        if case=='normal_cycle':
            own={'hwnd':cover['cover_hwnd'],'pid':cover['helper_pid'],'birth':cover['helper_birth'],'class':cover['cover_class']};assert int(own['pid'])==helper.p.pid
            before=own_capture(own,out/case/'cover-before')
            wrong=helper.send('status',session='f'*32);assert not wrong['ok'] and wrong['phase']=='COVERED'
            assert target.send('world',revision=1)['ok']
            prepared=helper.send('prepare',session=SESSION,new_attachment=NEW,view=VIEW,after_time=cover['old_capture_time']);assert prepared['ok'] and prepared['phase']=='PREPARED' and prepared['cover_window_visible'];assert int(prepared['capture_time'])>int(prepared['minimum_frame_time'])
            assert prepared['new_frame_sha256']!=cover['old_frame_sha256']
            after=own_capture(own,out/case/'cover-after-background-change');assert before['pixel_sha256']==after['pixel_sha256']
            args=dict(session=SESSION,prepared_token=prepared['prepared_token'],new_attachment=NEW,view=VIEW,new_frame=prepared['new_frame'],controller_grant='5'*32)
            stale=helper.send('reveal',**{**args,'prepared_token':'f'*32});assert not stale['ok'] and stale['phase']=='PREPARED' and stale['cover_window_visible']
            released=helper.send('reveal',**args);assert released['ok'] and released['phase']=='REVEALED' and not released['cover_window_visible'] and not released['input_gate_provided'];assert int(released['new_cover_capture_time'])>int(released['minimum_frame_time'])
            shown=own_capture(ready,out/case/'revealed-target');assert shown['pixel_sha256']==prepared['new_frame_sha256']
            assert helper.send('stop',session=SESSION)['ok'];helper.p.wait(timeout=3)
            return {'case':case,'passed':True,'old_cover_sha256':before['pixel_sha256'],'cover_after_background_change_sha256':after['pixel_sha256'],'new_target_sha256':shown['pixel_sha256'],'prepare':prepared,'reveal':released,'different_processes':helper.p.pid!=target.p.pid}
        reason={'explicit_hold':'TEST_FAILURE','idle_timeout':'CONTROLLER_TIMEOUT','geometry_change':'TARGET_BINDING_LOST','target_destroy':'TARGET_BINDING_LOST','controller_eof':'CONTROLLER_EOF','capture_timeout':'VISUAL_OPERATION_FAILED'}[case]
        if case=='explicit_hold':held=helper.send('hold',session=SESSION,message=reason)
        elif case=='geometry_change':target.send('move');held=helper.event(reason)
        elif case=='target_destroy':target.send('destroy');held=helper.event(reason)
        elif case=='controller_eof':helper.p.stdin.close();held=helper.event(reason)
        elif case=='capture_timeout':held=helper.send('prepare',session=SESSION,new_attachment=NEW,view=VIEW,after_time=str(2**63-2))
        else:held=helper.event(reason)
        assert held['phase']=='HELD' and held['old_pixels_retained'] and not held['gameplay_authorized'] and not held['input_gate_provided'];assert helper.p.poll() is None
        if case not in ('target_destroy',):assert held['cover_window_visible']
        if case!='controller_eof':
            rejected=helper.send('stop',session=SESSION);assert not rejected['ok'] and rejected['phase']=='HELD';assert helper.send('force_stop',session=SESSION,accept_cover_loss=True)['cover_loss_explicit'];helper.p.wait(timeout=3)
        return {'case':case,'passed':True,'held':held,'stayed_alive_while_held':True,'explicit_test_cleanup_on_eof':case=='controller_eof'}
    finally:
        if helper:helper.cleanup()
        try:
            if target.p.poll() is None:target.send('quit')
        except Exception:pass
        target.cleanup()
def main():
    out=ROOT/'checkpoint_map_wait_helper_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    frozen_files=['checkpoint_map_cover_capture.h','checkpoint_map_cover_capture.cpp','checkpoint_map_cover_capture.obj','checkpoint_map_cover_probe.exe','native_storage_read_core.h','native_storage_read_core.cpp','native_storage_read_core.obj'];frozen={name:sha(ROOT/name) for name in frozen_files}
    build=subprocess.run(['cmd','/c',str(ROOT/'checkpoint_map_wait_helper_build.cmd')],capture_output=True,text=True,encoding='utf8',errors='replace');(out/'build.txt').write_text(build.stdout+build.stderr,encoding='utf8');assert build.returncode==0,build.stdout+build.stderr
    cases=[]
    for case in ('normal_cycle','wrong_birth','explicit_hold','idle_timeout','geometry_change','target_destroy','controller_eof','capture_timeout'):
        try:cases.append(pair(out,case))
        except Exception as error:cases.append({'case':case,'passed':False,'error':repr(error),'traceback':traceback.format_exc()})
    assert frozen=={name:sha(ROOT/name) for name in frozen}
    sources=['checkpoint_map_wait_helper.cpp','checkpoint_map_wait_helper_common.h','checkpoint_map_wait_helper_fixture.cpp','checkpoint_map_wait_helper_build.cmd','checkpoint_map_wait_helper_test.py','checkpoint_map_wait_helper_protocol.txt']
    report={'schema':'san14.map-wait-helper-cross-process-fixtures.v1','result':'PASS' if all(c['passed'] for c in cases) else 'FAIL','cases':cases,'source_sha256':{name:sha(ROOT/name) for name in sources},'helper_binary_sha256':sha(ROOT/'checkpoint_map_wait_helper.exe'),'fixture_binary_sha256':sha(ROOT/'checkpoint_map_wait_helper_fixture.exe'),'frozen_dependencies_unchanged':frozen,'game_access':False,'cross_process_targets':'Only child fixture/helper processes launched by this test','input_injected':False,'native_input_gate':False,'physical_monitor_unoccluded_proved':False,'gameplay_enabled':False}
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'result':report['result'],'cases':len(cases),'failed':[c for c in cases if not c['passed']],'path':str(out/'result.json')}));return report['result']!='PASS'
if __name__=='__main__':raise SystemExit(main())

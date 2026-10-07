"""Create a separately scoped native CC storage probe; never modifies frozen probes."""
from pathlib import Path
P=Path(__file__).resolve().parent
names=['native_file_identity_probe.h','native_file_identity_probe.cpp',
       'native_file_identity_probe_guard.h','native_file_identity_probe_profile.h',
       'native_file_identity_probe_fixture.cpp','native_file_identity_probe_build.cmd',
       'native_file_identity_probe_test.py','native_file_identity_fixture_gate.py']
def convert(s):
    for a,b in [('native_file_identity_probe','checkpoint_cc_file_probe'),
                ('native_file_identity_fixture_gate','checkpoint_cc_file_fixture_gate'),
                ('NATIVE_FILE_IDENTITY_FIXTURE','CHECKPOINT_CC_FILE_FIXTURE'),
                ('NativeFileIdentity','CheckpointCcFile'),
                ('0x53414E1446494431','0x53414E1443434631'),
                ('mppush01.s14','svdexccSC03.s14'),
                ('san14.native-file-identity-probe-fixtures.v1','san14.checkpoint-cc-file-probe-fixtures.v1')]:
        s=s.replace(a,b)
    return s
for name in names:
    target=P/convert(name)
    text=convert((P/name).read_text(encoding='utf8'))
    if name.endswith('probe.h'):
        text=text.replace('// default dry; mode1 = one Verify attempt', '// 0 dry, 1 full read identity, 2 require native absence twice')
    if name.endswith('probe.cpp'):
        text=text.replace('cfg.mode>1','cfg.mode>2')
        text=text.replace('if(s.cacheMode>1', 'if(s.cacheMode>1')
        before='static void doVerify(){'
        absence=r'''// This only observes presence. It never creates/writes/deletes a Steam file.
static void doAbsence(){
    bool absent=true;
    for(unsigned i=0;i<2;++i){
        if(!validateStorage(nullptr)){absent=false;break;}
        AcquireSRWLockExclusive(&reportLock);++report.existsCalls;ReleaseSRWLockExclusive(&reportLock);
        bool exists=api.exists(api.storage,PROBE_BASENAME);
        if(exists){absent=false;break;}
        if(!validateStorage(nullptr)){absent=false;break;}
        AcquireSRWLockExclusive(&reportLock);++report.sizeCalls;ReleaseSRWLockExclusive(&reportLock);
        auto size=api.size(api.storage,PROBE_BASENAME);
        AcquireSRWLockExclusive(&reportLock);report.sizes[i]=size;ReleaseSRWLockExclusive(&reportLock);
        if(size>0){absent=false;break;}
    }
    if(!validateStorage(nullptr))absent=false;
    stage(absent?"native_absence_observed_twice":"native_absence_rejected");
    if(!absent)error(46);
    // No identity/lease/load claim is made for a missing file.
    InterlockedCompareExchange(&state,absent?FP_MATCHED:FP_REJECTED,FP_READING);
}
'''
        assert before in text;text=text.replace(before,absence+before)
        text=text.replace('if(acquireStorage())doVerify();else', 'if(acquireStorage()){if(cfg.mode==2)doAbsence();else doVerify();}else')
        # A delayed stop/concurrent callback must not become a successful read.
        text=text.replace('InterlockedExchange(&state,FP_MATCHED);',
            'if(!validateStorage(nullptr)){error(47);InterlockedExchange(&state,FP_UNCERTAIN);return;}\n    InterlockedCompareExchange(&state,FP_MATCHED,FP_READING);')
    if name.endswith('guard.h'):
        text=text.replace('if(s.cacheMode>1||', 'if(s.cacheMode!=0||')
    if name.endswith('fixture.cpp'):
        text=text.replace('static bool __fastcall exists(void* p,const char* name){return p==&storageObject&&!strcmp(name,"svdexccSC03.s14");}',
        '''static unsigned presenceCalls=0;
static bool __fastcall exists(void* p,const char* name){
    ++presenceCalls;
    if(scenario==L"absent-seh")RaiseException(0xE0142223,0,0,nullptr);
    if(scenario==L"absent-stop")stopFn(nullptr);
    if(scenario==L"absent"||scenario==L"absent-size-conflict"||scenario==L"absent-stop"||scenario==L"absent-then-present")
        return scenario==L"absent-then-present"&&presenceCalls==2;
    return p==&storageObject&&!strcmp(name,"svdexccSC03.s14");
}''')
        text=text.replace('static int32_t __fastcall size(void*,const char*){return static_cast<int32_t>(bytes.size());}',
        '''static int32_t __fastcall size(void*,const char*){
    if(scenario==L"absent"||scenario==L"absent-stop"||scenario==L"absent-then-present")return 0;
    return static_cast<int32_t>(bytes.size());
}''')
        text=text.replace('config.expectedPid=GetCurrentProcessId();',
            'if(scenario.rfind(L"absent",0)==0)config.mode=2;\n    config.expectedPid=GetCurrentProcessId();')
        text=text.replace('check(!r.nativeLoadAuthorized',
        '''if(scenario==L"absent")check(r.state==FP_MATCHED&&r.existsCalls==2&&r.sizeCalls==2&&r.sizes[0]==0&&r.sizes[1]==0&&!r.identityMatched,"native absence twice");
    if(scenario==L"absent-present"||scenario==L"absent-size-conflict"||scenario==L"absent-then-present"||scenario==L"absent-stop")check(r.state==FP_REJECTED&&!r.identityMatched,"uncertain or present rejected");
    if(scenario==L"absent-seh")check(r.state==FP_UNCERTAIN&&r.exceptionCode==0xE0142223,"absence exception retained");
    if(config.mode==2)check(r.verifyAttempts==0&&r.readCalls==0&&!r.identityMatched&&!r.verifiedSize,"absence never reads or claims identity");
    check(!r.nativeLoadAuthorized''')
    if name.endswith('_test.py') or name.endswith('_gate.py'):
        text=text.replace("'read-seh','stop-during-read']", "'read-seh','stop-during-read','absent','absent-present','absent-size-conflict','absent-then-present','absent-stop','absent-seh']")
        text=text.replace("'read-seh', 'stop-during-read')", "'read-seh', 'stop-during-read', 'absent', 'absent-present', 'absent-size-conflict', 'absent-then-present', 'absent-stop', 'absent-seh')")
    # Gate's unrelated frozen core archive must still check the original checkpoint bytes.
    with target.open('x',encoding='utf8') as f:f.write(text)
print('Created separate CC file probe sources; no game access.')

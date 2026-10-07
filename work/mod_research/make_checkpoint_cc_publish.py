"""Generate independent publication adapter, preserving executed read-only probe."""
from pathlib import Path
P=Path(__file__).resolve().parent
def convert(s):
    for a,b in [('checkpoint_cc_file_probe','checkpoint_cc_publish'),('CHECKPOINT_CC_FILE_FIXTURE','CHECKPOINT_CC_PUBLISH_FIXTURE'),
                ('CheckpointCcFile','CheckpointCcPublish'),('0x53414E1443434631','0x53414E1443435031')]:s=s.replace(a,b)
    return s
names=['checkpoint_cc_file_probe.h','checkpoint_cc_file_probe.cpp','checkpoint_cc_file_probe_guard.h','checkpoint_cc_file_probe_profile.h',
       'checkpoint_cc_file_probe_build.cmd','checkpoint_cc_file_probe_fixture.cpp','checkpoint_cc_file_probe_test.py']
for name in names:
    s=convert((P/name).read_text(encoding='utf8'))
    if name.endswith('probe.h'):
        s=s.replace('#include "checkpoint_push_bridge.h"','#include "checkpoint_push_bridge.h"\n#include "native_storage_publish_core.h"')
        s=s.replace('    HANDLE testPublishedEvent=', '''    native_storage_publish::FileWrite testWrite=nullptr;
    wchar_t testIntentPath[512]{};
    native_storage_publish::Identity testIdentity{};
    unsigned char testOwnerBinding[32]{};
    HANDLE testPublishedEvent=''')
        s=s.replace('struct CheckpointCcPublishReport {', '''struct PublishPart {
    std::uint32_t state=0,osError=0,exceptionCode=0,existsCalls=0,writeAttempts=0,writeReturned=0,nativeWriteReturn=0;
    std::uint32_t intentCreated=0,intentDurable=0,localPinReleased=0,sourceMatched=0,matched=0,publishAttempts=0,reserved=0;
    std::uint64_t writeMethod=0;
    unsigned char sourceSha256[32]{};
    char stage[64]{};
};
static_assert(sizeof(PublishPart)==160);
struct CheckpointCcPublishReport {''')
        s=s.replace('    std::uint32_t nativeLoadAuthorized=0, fullWorldVerified=0;','    std::uint32_t nativeLoadAuthorized=0, fullWorldVerified=0;\n    PublishPart publish{};')
        s=s.replace('sizeof(CheckpointCcPublishReport)==520','sizeof(CheckpointCcPublishReport)==680')
        s=s.replace('// 0 dry, 1 full read identity, 2 require native absence twice','// 0 dry, 1 publish owned staged bytes once through native FileWrite')
    if name.endswith('probe.cpp'):
        s=s.replace('#include "native_storage_read_core.h"','#include "native_storage_read_core.h"\n#include "checkpoint_cc_publish_binding.h"')
        s=s.replace('static native_storage_read::Api api{};','static native_storage_read::Api api{};\nstatic native_storage_publish::FileWrite writeMethod=nullptr;')
        s=s.replace('cfg.mode>2','cfg.mode>1')
        s=s.replace('api.read==cfg.testApi.read;', 'api.read==cfg.testApi.read&&writeMethod==cfg.testWrite;')
        s=s.replace('probeAt<uintptr_t>(vtable+8)!=uintptr_t(api.read))', 'probeAt<uintptr_t>(vtable+8)!=uintptr_t(api.read)||probeAt<uintptr_t>(vtable)!=uintptr_t(writeMethod))')
        s=s.replace('imageMethod(uintptr_t(api.size),false)&&imageMethod(uintptr_t(api.read),false);', 'imageMethod(uintptr_t(api.size),false)&&imageMethod(uintptr_t(api.read),false)&&imageMethod(uintptr_t(writeMethod),false);')
        s=s.replace('api=cfg.testApi;storage=', 'api=cfg.testApi;writeMethod=cfg.testWrite;storage=')
        s=s.replace('    api.read=reinterpret_cast<native_storage_read::FileRead>(probeAt<uintptr_t>(vtable+8));', '    api.read=reinterpret_cast<native_storage_read::FileRead>(probeAt<uintptr_t>(vtable+8));\n    writeMethod=reinterpret_cast<native_storage_publish::FileWrite>(probeAt<uintptr_t>(vtable));')
        s=s.replace('if(!imageMethod(uintptr_t(api.exists),true)', 'if(!imageMethod(uintptr_t(writeMethod),true)||!imageMethod(uintptr_t(api.exists),true)')
        s=s.replace('report.storage=storage;report.storageVtable=', 'report.publish.writeMethod=uintptr_t(writeMethod);report.storage=storage;report.storageVtable=')
        a=s.index('// This only observes presence.');b=s.index('static void before(',a)
        s=s[:a]+'''static native_storage_publish::Input publishInput(){
    native_storage_publish::Input input{};input.localPath=cfg.localPath;
#ifdef CHECKPOINT_CC_PUBLISH_FIXTURE
    input.intentPath=cfg.testIntentPath;input.expectedStage=cfg.testIdentity;
    memcpy(input.ownerBinding,cfg.testOwnerBinding,32);
#else
    input.intentPath=PUBLISH_INTENT;input.expectedStage=PUBLISH_IDENTITY;
    memcpy(input.ownerBinding,PUBLISH_OWNER,32);
#endif
    return input;
}
static bool validateStage(void*,const native_storage_publish::Input& value){
    if(!validateStorage(nullptr)||callbackDepth!=1)return false;
    auto expected=publishInput();
    if(wcscmp(value.localPath,expected.localPath)||wcscmp(value.intentPath,expected.intentPath)||
       memcmp(&value.expectedStage,&expected.expectedStage,sizeof expected.expectedStage)||memcmp(value.ownerBinding,expected.ownerBinding,32))return false;
#ifndef CHECKPOINT_CC_PUBLISH_FIXTURE
    if(cfg.expectedPid!=PUBLISH_PID||cfg.expectedProcessBirth!=PUBLISH_BIRTH||base!=PUBLISH_BASE||user!=PUBLISH_USER||
       !hashPath(PUBLISH_STAGE_RECEIPT,PUBLISH_STAGE_SHA))return false;
#endif
    return true;
}
static void doPublish(){
    native_storage_publish::Api publisher{};publisher.read=api;publisher.write=writeMethod;publisher.validateStage=validateStage;
    native_storage_publish::Evidence evidence{};
    auto input=publishInput();
    AcquireSRWLockExclusive(&reportLock);++report.publish.publishAttempts;ReleaseSRWLockExclusive(&reportLock);
    bool ok=native_storage_publish::Publish(input,publisher,evidence);
    const auto& read=evidence.readback;
    AcquireSRWLockExclusive(&reportLock);
    auto& p=report.publish;p.state=unsigned(evidence.state);p.osError=evidence.osError;p.exceptionCode=evidence.exceptionCode;
    p.existsCalls=evidence.existsCalls;p.writeAttempts=evidence.writeAttempts;p.writeReturned=evidence.writeReturned;
    p.nativeWriteReturn=evidence.nativeWriteReturn;p.intentCreated=evidence.intentCreated;p.intentDurable=evidence.intentDurable;
    p.localPinReleased=evidence.localPinReleased;p.sourceMatched=evidence.sourceMatched;p.matched=evidence.matched;
    memcpy(p.sourceSha256,evidence.sourceSha256,32);strncpy_s(p.stage,evidence.stage,_TRUNCATE);
    report.existsCalls=read.existsCalls;report.sizeCalls=read.sizeCalls;report.readCalls=read.readCalls;
    memcpy(report.sizes,read.sizes,sizeof read.sizes);memcpy(report.readReturns,read.readReturns,sizeof read.readReturns);
    memcpy(report.localSha256,read.localSha256,32);memcpy(report.nativeSha256,read.nativeSha256,64);
    report.identityMatched=ok;report.verifiedSize=ok?native_storage_publish::TargetSize:0;
    report.localPinReleased=evidence.localPinReleased;report.exceptionCode=evidence.exceptionCode;report.osError=evidence.osError;
    strncpy_s(report.stage,evidence.stage,_TRUNCATE);
    ReleaseSRWLockExclusive(&reportLock);
    if(!ok){error(48);InterlockedExchange(&state,evidence.state==native_storage_publish::State::Uncertain?FP_UNCERTAIN:FP_REJECTED);return;}
    if(!validateStage(nullptr,input)){error(49);InterlockedExchange(&state,FP_UNCERTAIN);return;}
    InterlockedCompareExchange(&state,FP_MATCHED,FP_READING);
}
'''+s[b:]
        s=s.replace('if(acquireStorage()){if(cfg.mode==2)doAbsence();else doVerify();}else', 'if(acquireStorage())doPublish();else')
    if name.endswith('_build.cmd'):
        insert='''cl /nologo /W4 /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_cc_publish_core.obj native_storage_publish_core.cpp
if errorlevel 1 exit /b 1
'''
        needle='cl /nologo /W4 /EHa /std:c++17 /O2 /MT /LD'
        s=s.replace(needle,insert+needle,1)
        s=s.replace('checkpoint_cc_publish_storage.obj /link','checkpoint_cc_publish_storage.obj checkpoint_cc_publish_core.obj /link')
    # Fixture body is adjusted separately, keeping the same publication/exception scheduling harness.
    with (P/convert(name)).open('x',encoding='utf8') as f:f.write(s)
print('Created independent publish adapter drafts; no game access.')

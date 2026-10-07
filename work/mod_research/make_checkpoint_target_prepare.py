"""One-time derivation of a new private-node probe; never rewrites the old probe."""
from pathlib import Path
import hashlib

P=Path(__file__).resolve().parent
mapping={
    'native_file_identity_probe.h':'checkpoint_target_prepare.h',
    'NativeFileIdentityConfig':'TargetPrepareConfig',
    'NativeFileIdentityReport':'TargetPrepareReport',
    'InstallNativeFileIdentityProbe':'InstallTargetPrepare',
    'StopNativeFileIdentityProbe':'StopTargetPrepare',
    'GetNativeFileIdentityReport':'GetTargetPrepareReport',
    'NATIVE_FILE_IDENTITY_FIXTURE':'CHECKPOINT_TARGET_PREPARE_FIXTURE',
    '0x53414E1446494431':'0x53414E1454505231',
}

def convert(text):
    for a,b in mapping.items():text=text.replace(a,b)
    return text

header=convert((P/'native_file_identity_probe.h').read_text())
leaf='''struct TargetPrepareLeaf {
    uint32_t success=0,bound=0,parsed=0,copied=0,released=0,sourceUnchanged=0;
    uint32_t headerCtorCalls=0,headerParserCalls=0,stringDtorCalls=0,allocateCalls=0,headerCopyCalls=0,freeCalls=0;
    uint32_t poisoned=0,exceptionCode=0,nodeState=0,reserved=0;
    uint64_t node=0,allocationTicket=0,consumed=0;
    unsigned char headerSha256[32]{};
    char stage[64]{};
};
static_assert(sizeof(TargetPrepareLeaf)==184);
'''
header=header.replace('struct TargetPrepareConfig {',leaf+'\nstruct TargetPrepareConfig {')
header=header.replace('    void* volatile* testSlot=nullptr;','    bool (*testNativePrepare)(const unsigned char*,size_t,TargetPrepareLeaf*)=nullptr;\n    void* volatile* testSlot=nullptr;')
header=header.replace('    std::uint32_t nativeLoadAuthorized=0, fullWorldVerified=0;','    std::uint32_t nativeLoadAuthorized=0, fullWorldVerified=0;\n    TargetPrepareLeaf leaf{};')
header=header.replace('sizeof(TargetPrepareReport)==520','sizeof(TargetPrepareReport)==704')
cpp=convert((P/'native_file_identity_probe.cpp').read_text())
# Keep the previously tested guard unchanged. Its fixture exclusion must use
# the original macro because that header belongs to the immutable old probe.
cpp=cpp.replace('#include "native_file_identity_probe_guard.h"','''#ifdef CHECKPOINT_TARGET_PREPARE_FIXTURE
#define NATIVE_FILE_IDENTITY_FIXTURE
#endif
#include "native_file_identity_probe_guard.h"
#include "checkpoint_target_metadata_native.h"''')
cpp=cpp.replace('return probeGuard(base,user,pinned,false);','return pinned.cacheMode==0 && probeGuard(base,user,pinned,false);')
cpp=cpp.replace('if(!probeGuard(base,user,pinned,true))return 8;','if(!probeGuard(base,user,pinned,true)||pinned.cacheMode!=0)return 8;')
cpp=cpp.replace('static void doVerify(){','#include "checkpoint_target_prepare_leaf.inc"\nstatic void doVerify(){')
cpp=cpp.replace('    bool releaseOk=true;','    TargetPrepareLeaf leaf{};\n    bool prepared=ok && doNativePrepare(lease,leaf);\n    {AcquireSRWLockExclusive(&reportLock);report.leaf=leaf;ReleaseSRWLockExclusive(&reportLock);}\n    bool releaseOk=true;')
cpp=cpp.replace('    InterlockedExchange(&state,FP_MATCHED);','''    if(!prepared){error(46);InterlockedExchange(&state,FP_UNCERTAIN);return;}
    if(!currentGuard()){error(47);InterlockedExchange(&state,FP_UNCERTAIN);return;}
    if(InterlockedCompareExchange(&state,FP_MATCHED,FP_READING)!=FP_READING){error(48);InterlockedExchange(&state,FP_UNCERTAIN);return;}''')
for name,text in [('checkpoint_target_prepare.h',header),('checkpoint_target_prepare.cpp',cpp)]:
    with (P/name).open('x',encoding='utf8') as f:f.write(text)
    print(name,hashlib.sha256(text.encode()).hexdigest())

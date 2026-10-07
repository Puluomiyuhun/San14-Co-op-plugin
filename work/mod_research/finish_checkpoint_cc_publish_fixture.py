from pathlib import Path
P=Path(__file__).resolve().parent
path=P/'checkpoint_cc_publish_fixture.cpp';s=path.read_text(encoding='utf8')
a=s.index('static unsigned presenceCalls=0;');b=s.index('static int32_t __fastcall read(',a)
s=s[:a]+'''static bool published=false;
static unsigned writeCalls=0;
static bool __fastcall exists(void* p,const char* name){
    return p==&storageObject&&!strcmp(name,"svdexccSC03.s14")&&(published||scenario==L"native-present");
}
static int32_t __fastcall size(void*,const char*){return published?static_cast<int32_t>(bytes.size()):0;}
static bool __fastcall write(void* p,const char* name,const void* input,int32_t amount){
    ++writeCalls;
    check(p==&storageObject&&!strcmp(name,"svdexccSC03.s14")&&amount==int32_t(bytes.size()),"write ABI");
    check(!memcmp(input,bytes.data(),bytes.size()),"full immutable source reaches write");
    HANDLE local=CreateFileW(config.localPath,GENERIC_READ|GENERIC_WRITE,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    check(local!=INVALID_HANDLE_VALUE,"read pin released before native write");
    if(local!=INVALID_HANDLE_VALUE)CloseHandle(local);
    if(scenario==L"write-seh")RaiseException(0xE0142224,0,0,nullptr);
    published=true;
    if(scenario==L"write-false")return false;
    if(scenario==L"stop-during-write")stopFn(nullptr);
    return true;
}
'''+s[b:]
s=s.replace('    bytes.resize(4096);for(size_t i=0;i<bytes.size();++i)bytes[i]=static_cast<unsigned char>((i*17+31)&255);',
'''    bytes.resize(native_storage_publish::TargetSize);
    HANDLE source=CreateFileW(L"checkpoint_push_archives\\\\20261006-204306-581930\\\\mppush01.s14",GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(source==INVALID_HANDLE_VALUE)return 20;DWORD n=0;
    check(ReadFile(source,bytes.data(),DWORD(bytes.size()),&n,nullptr)&&n==bytes.size(),"archived source");CloseHandle(source);''')
s=s.replace('    if(scenario.rfind(L"absent",0)==0)config.mode=2;\n','')
s=s.replace('config.testGuard=guard;config.testApi=', 'config.testGuard=guard;config.testWrite=write;config.testApi=')
s=s.replace('    config.testSize=static_cast<uint32_t>(bytes.size());', '''    swprintf_s(config.testIntentPath,L"%s.intent",argv[2]);memset(config.testOwnerBinding,0x5A,32);
    HANDLE staged=CreateFileW(config.localPath,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    BY_HANDLE_FILE_INFORMATION info{};check(staged!=INVALID_HANDLE_VALUE&&GetFileInformationByHandle(staged,&info),"source identity");
    if(staged!=INVALID_HANDLE_VALUE)CloseHandle(staged);
    config.testIdentity={info.dwVolumeSerialNumber,info.nFileIndexHigh,info.nFileIndexLow,info.ftLastWriteTime};
    if(scenario==L"wrong-stage-identity")++config.testIdentity.indexLow;
    if(scenario==L"existing-intent"){
        HANDLE intent=CreateFileW(config.testIntentPath,GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);
        check(intent!=INVALID_HANDLE_VALUE,"fixture prior intent");if(intent!=INVALID_HANDLE_VALUE)CloseHandle(intent);
    }
    config.testSize=static_cast<uint32_t>(bytes.size());''')
s=s.replace('r.state==FP_REJECTED&&!r.identityMatched&&r.readCalls==1','r.state==FP_UNCERTAIN&&!r.identityMatched&&r.readCalls==1')
a=s.index('    if(scenario==L"absent")');b=s.index('    check(!r.nativeLoadAuthorized',a)
s=s[:a]+'''    if(scenario==L"read")check(writeCalls==1&&r.publish.writeAttempts==1&&r.publish.writeReturned==1&&r.publish.nativeWriteReturn&&r.publish.intentDurable&&r.publish.matched,"one publish and full readback");
    if(scenario==L"write-false"||scenario==L"write-seh"||scenario==L"stop-during-write")check(r.state==FP_UNCERTAIN&&writeCalls==1&&!r.identityMatched,"possibly entered write never retry");
    if(scenario==L"wrong-stage-identity"||scenario==L"existing-intent"||scenario==L"native-present")check(r.state==FP_REJECTED&&writeCalls==0&&!r.identityMatched,"wrong ownership or occupied rejects");
    check(writeCalls<=1,"at most one FileWrite");
'''+s[b:]
path.write_text(s,encoding='utf8')
path=P/'checkpoint_cc_publish_test.py';s=path.read_text(encoding='utf8')
s=s.replace("'absent','absent-present','absent-size-conflict','absent-then-present','absent-stop','absent-seh'", "'write-false','write-seh','stop-during-write','wrong-stage-identity','existing-intent','native-present'")
s=s.replace("'native_storage_read_core.h','native_storage_read_core.cpp',", "'native_storage_read_core.h','native_storage_read_core.cpp','native_storage_publish_core.h','native_storage_publish_core.cpp','checkpoint_cc_publish_binding.h',")
s=s.replace("'report_bytes':520", "'report_bytes':680")
s=s.replace('san14.checkpoint-cc-file-probe-fixtures.v1','san14.checkpoint-cc-publish-fixtures.v1')
path.write_text(s,encoding='utf8')
print('Publish fixture now exercises full fixed archive through the new core; no game access.')

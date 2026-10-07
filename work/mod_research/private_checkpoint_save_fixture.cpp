#define PRIVATE_CHECKPOINT_SAVE_FIXTURE
#include "private_checkpoint_save_pilot.h"
#include <cstdio>
#include <cstring>
#include <cwchar>
#include <string>

static uintptr_t image=0,root=0,user=0,world=0,storageHolder=0;
static unsigned originals=0,binds=0,queues=0,storageQueries=0;
static bool argumentsOk=true,intentBeforeBinder=false;
static PrivateCheckpointSaveConfig input{};
static PrivateCheckpointSaveReportData* report=nullptr;
static std::wstring test;
template<class T>static void put(uintptr_t p,T value){*reinterpret_cast<T*>(p)=value;}
static char* globalData(uintptr_t at){auto s=reinterpret_cast<SaveShortString*>(at);return s->capacity>=16?reinterpret_cast<char*>(*reinterpret_cast<uintptr_t*>(at)):s->data;}
static void copyIntoGlobal(uintptr_t at,const SaveShortString& source){
    auto s=reinterpret_cast<SaveShortString*>(at);
    if(s->capacity>=16){memcpy(globalData(at),source.data,source.size+1);s->size=source.size;}
    else memcpy(s,&source,32);
}
static void existingFile(const wchar_t* path){HANDLE f=CreateFileW(path,GENERIC_WRITE,FILE_SHARE_READ,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);if(f!=INVALID_HANDLE_VALUE)CloseHandle(f);}
static void __fastcall original(void* self,uintptr_t a2,uintptr_t a3,uintptr_t a4){
    ++originals;
    if(uintptr_t(self)!=user || a2!=0x1122 || a3!=0x3344 || a4!=0x5566)argumentsOk=false;
    if(test==L"original-drift")put<uint32_t>(user+0x470,5);
}
static void* __cdecl contextInit(void* token){
    if(uintptr_t(token)!=image+0x18D08B8)argumentsOk=false;
    return test==L"remote-unavailable"?nullptr:reinterpret_cast<void*>(storageHolder);
}
static bool __fastcall fileExists(void* self,const char* filename){
    ++storageQueries;
    if(uintptr_t(self)!=image+0x270000 || strcmp(filename,"mpckpt01.s14"))argumentsOk=false;
    if(test==L"storage-phase-drift")put<uint32_t>(user+0x470,5);
    return test==L"remote-exists";
}
static void __fastcall binder(SaveRequest* request){
    ++binds;
    intentBeforeBinder=GetFileAttributesW(input.intentPath)!=INVALID_FILE_ATTRIBUTES && report->intentFlushed==1;
    if(!intentBeforeBinder || request->slot!=-1 || request->filename.size!=12 || request->filename.capacity!=15 ||
       strcmp(request->filename.data,"mpckpt01.s14") || request->caption.size || request->caption.capacity!=15)argumentsOk=false;
    if(test==L"binder-exception")RaiseException(0xE1234567,0,0,nullptr);
    put<int32_t>(image+0x201ED10,request->slot);
    copyIntoGlobal(image+0x201ED18,request->filename);
    copyIntoGlobal(image+0x201ED38,request->caption);
    request->filename.size=request->caption.size=0;
    request->filename.data[0]=request->caption.data[0]=0;
    if(test==L"binder-mismatch")put<int32_t>(image+0x201ED10,48);
    if(test==L"heap-bind-mismatch")globalData(image+0x201ED18)[0]='X';
}
static void __fastcall enqueue(void* manager,const char* name,uintptr_t argument){
    ++queues;
    if(uintptr_t(manager)!=image+0x19E7310 || uintptr_t(name)!=image+0x12AA8E0 || strcmp(name,"CSaveState") || argument || originals!=1)argumentsOk=false;
    auto q=image+0x250000,s=image+0x240000;
    if(*reinterpret_cast<uint64_t*>(image+0x19E7310+0x38)==0){
        if(*reinterpret_cast<uintptr_t*>(image+0x19E7310+0x40)!=0)argumentsOk=false;
        put<uint64_t>(image+0x19E7310+0x38,64);put<uintptr_t>(image+0x19E7310+0x40,q);
    }
    put<uint64_t>(image+0x19E7310+0x30,1);put<uint32_t>(q,2);
    put<uintptr_t>(q+8,test==L"queue-failure"?0:s);
    put<uintptr_t>(s,image+0x12DC5F8);put<uint32_t>(s+0x470,0);memcpy(reinterpret_cast<void*>(s+0x70),"CSaveState",11);
}
static void __fastcall saveOriginal(void* self,uintptr_t,uintptr_t,uintptr_t){
    auto s=uintptr_t(self),manager=image+0x19E7310;
    auto phase=*reinterpret_cast<uint32_t*>(s+0x470);
    if(phase==0)put<uint32_t>(s+0x470,1);
    if(phase==1){put<uint32_t>(image+0x201EC2C,0);put<uint32_t>(s+0x470,2);}
    if(phase==2 && test!=L"save-stall"){
        put<uint32_t>(image+0x201EC2C,test==L"native-failure"?0:1);put<uint32_t>(s+0x470,3);
    }
    if(phase==3)put<uint32_t>(s+0x470,4);
    if(phase==4){
        if(test!=L"globals-not-cleared"){
            put<uint64_t>(image+0x201ED18+16,0);globalData(image+0x201ED18)[0]=0;
            put<uint64_t>(image+0x201ED38+16,0);globalData(image+0x201ED38)[0]=0;put<int32_t>(image+0x201ED10,-1);
        }
        put<uint64_t>(manager+0x10,5);put<uint64_t>(manager+0x30,0);
    }
}
static DWORD WINAPI tick(void*){
    for(unsigned i=0;i<11;++i){auto f=*reinterpret_cast<SaveUpdate*>(image+0x12CC4A8+0x28);f(reinterpret_cast<void*>(user),0x1122,0x3344,0x5566);}
    if(report->status==4){
        auto manager=image+0x19E7310,stack=image+0x210000,s=image+0x240000;
        put<uint64_t>(manager+0x30,0);put<uint64_t>(manager+0x10,6);put<uintptr_t>(stack+40,s);
        if(test==L"wrong-save-object")put<uintptr_t>(stack+40,s+0x1000);
        if(test==L"request-replaced")globalData(image+0x201ED18)[0]='X';
        if(test==L"bad-save-phase")put<uint32_t>(s+0x470,9);
        for(unsigned i=0;i<8 && *reinterpret_cast<uint64_t*>(manager+0x10)==6;++i){
            auto f=*reinterpret_cast<SaveUpdate*>(image+0x12DC5F8+0x28);f(reinterpret_cast<void*>(s),0,0,0);
        }
    }
    return 0;
}
int wmain(int argc,wchar_t** argv){
    if(argc!=4)return 2;
    test=argv[2];
    image=uintptr_t(VirtualAlloc(nullptr,0x2300000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));
    root=uintptr_t(VirtualAlloc(nullptr,0x100000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));
    if(!image||!root)return 3;
    world=root+0x86000;user=image+0x204000;
    put<uintptr_t>(image+0x1FCA1E0,root);put<uintptr_t>(root,image+0x12AA6B0);put<uintptr_t>(root+0x85130,world);
    put<uintptr_t>(world,image+0x12AA638);put<uint16_t>(world+0x34,203);put<uint8_t>(world+0x36,8);put<uint8_t>(world+0x37,11);put<uint8_t>(world+0x3A,12);
    put<uint32_t>(world+0x40,1);put<uintptr_t>(image+0x2025318,image+0x290000);put<int32_t>(image+0x290000+0x3EC,-1);
    const char* names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};
    auto manager=image+0x19E7310,stack=image+0x210000;
    put<uint64_t>(manager+0x10,5);put<uintptr_t>(manager+0x20,stack);put<uintptr_t>(manager,image+0x260000);
    put<uintptr_t>(manager+0x28,image+0x260000);put<uint64_t>(manager+0x38,64);put<uintptr_t>(manager+0x40,image+0x250000);
    put<uintptr_t>(image+0x260000,image+0x1283498);
    put<uintptr_t>(image+0x1283498+0x28,image+0x12C840);put<uintptr_t>(image+0x1283498+0x38,image+0x12C290);
    put<uintptr_t>(image+0x1283498+0x40,image+0x8388D0);put<uintptr_t>(image+0x1283498+0x48,image+0x1479B0);
    for(unsigned i=0;i<5;++i){auto state=image+0x200000+i*0x1000;put<uintptr_t>(stack+i*8,state);memcpy(reinterpret_cast<void*>(state+0x70),names[i],strlen(names[i])+1);}
    put<uintptr_t>(user,image+0x12CC4A8);put<uint32_t>(user+0x470,2);put<uintptr_t>(user+0x478,image+0x280000);put<uintptr_t>(user+0x618,image+0x281000);
    auto city=root+0x8A000,person=root+0x8B000,district=root+0x8C000,force=root+0x8D000;
    put<uintptr_t>(root+0xDAA8+19*8,city);put<uintptr_t>(root+0x148+666*8,person);put<uintptr_t>(root+0xDE40+11*8,district);put<uintptr_t>(root+0xDCA0+12*8,force);
    put<uint16_t>(force+0x10,666);put<uint16_t>(person+0x10,666);put<uint8_t>(person+0x118,11);put<uint16_t>(person+0x11A,19);
    put<uint16_t>(city+0x10,19);put<uint8_t>(city+0x30,11);put<uint32_t>(city+0x3C,15204);put<uint8_t>(district+0x10,12);put<uint8_t>(district+0x14,18);
    for(unsigned i=0;i<=500;++i){auto army=root+0x90000+i*0x200;put<uintptr_t>(root+0x7DF60+i*8,army);if(i>0&&i<=56){put<uint8_t>(army+0x10,1);put<uint16_t>(army+0x12,uint16_t(100+i));}}
    put<int32_t>(image+0x201ED10,-1);put<uint64_t>(image+0x201ED18+24,15);put<uint64_t>(image+0x201ED38+24,15);
    if(test.rfind(L"heap-",0)==0){put<uintptr_t>(image+0x201ED18,image+0x2A0000);put<uint64_t>(image+0x201ED18+24,31);}
    if(test==L"heap-both-queue"){put<uintptr_t>(image+0x201ED38,image+0x2A0100);put<uint64_t>(image+0x201ED38+24,31);}
    if(test==L"heap-null")put<uintptr_t>(image+0x201ED18,0);
    if(test==L"heap-unterminated")put<char>(image+0x2A0000,'X');
    if(test==L"heap-bad-cap")put<uint64_t>(image+0x201ED18+24,7);
    memcpy(reinterpret_cast<void*>(image+0x12AA8E0),"CSaveState",11);
    storageHolder=image+0x272000;put<uintptr_t>(storageHolder,image+0x270000);put<uintptr_t>(image+0x270000,image+0x271000);
    put<uintptr_t>(image+0x271000+0x68,uintptr_t(&fileExists));put<uintptr_t>(image+0x123CB28,uintptr_t(&contextInit));put<uintptr_t>(image+0x18D08B8,image+0x2FCB90);
    *reinterpret_cast<SaveUpdate*>(image+0x12CC4A8+0x28)=&original;
    *reinterpret_cast<SaveUpdate*>(image+0x12DC5F8+0x28)=&saveOriginal;
    const bool dryCase=test==L"dry"||test==L"heap-name-dry"||test==L"empty-vector-dry";
    input.magic=SAVE_CONFIG_MAGIC;input.version=1;input.execute=dryCase?0:1;input.slot=0xFFFFFFFF;
    _snwprintf_s(input.targetPath,512,_TRUNCATE,L"%ls\\mpckpt01.s14",argv[3]);
    _snwprintf_s(input.intentPath,512,_TRUNCATE,L"%ls\\private_checkpoint_save_attempt.intent",argv[3]);
    input.testBase=image;input.testBinder=uintptr_t(&binder);input.testQueue=uintptr_t(&enqueue);
    if(test==L"slot34")input.slot=34;
    if(test==L"slot49")input.slot=49;
    if(test==L"slot0")input.slot=0;
    if(test==L"slot50")input.slot=50;
    if(test==L"slot119")input.slot=119;
    if(test==L"bad-magic")input.magic=0;
    if(test==L"reserved-nonzero")input.reservedMustBeZero=1;
    if(test==L"cache-pending-load")put<int32_t>(image+0x290000+0x3EC,34);
    if(test==L"world-mode")put<uint32_t>(world+0x40,0);
    if(test.find(L"empty-vector")!=std::wstring::npos){put<uint64_t>(manager+0x38,0);put<uintptr_t>(manager+0x40,0);}
    if(test==L"null-vector-with-capacity")put<uintptr_t>(manager+0x40,0);
    if(test==L"zero-capacity-with-pointer")put<uint64_t>(manager+0x38,0);
    if(test==L"oversized-vector")put<uint64_t>(manager+0x38,4097);
    if(test==L"bad-allocator-type")put<uintptr_t>(image+0x260000,image+0x1283400);
    if(test==L"bad-allocator-method")put<uintptr_t>(image+0x1283498+0x48,image+0x1479C0);
    if(test==L"wrong-filename")_snwprintf_s(input.targetPath,512,_TRUNCATE,L"%ls\\svdexSC49.s14",argv[3]);
    if(test==L"wrong-date")put<uint8_t>(world+0x37,21);
    if(test==L"wrong-phase")put<uint32_t>(user+0x470,5);
    if(test==L"wrong-owner")put<uint8_t>(world+0x3A,2);
    if(test==L"wrong-ruler")put<uint16_t>(force+0x10,952);
    if(test==L"busy-queue")put<uint64_t>(manager+0x30,1);
    if(test==L"busy-request")put<int32_t>(image+0x201ED10,34);
    if(test==L"existing-local")existingFile(input.targetPath);
    if(test==L"intent-exists")existingFile(input.intentPath);
    HMODULE dll=LoadLibraryW(argv[1]);if(!dll)return 4;
    auto install=reinterpret_cast<SaveInstall>(GetProcAddress(dll,"InstallPrivateCheckpointSave"));
    auto cancel=reinterpret_cast<SaveInstall>(GetProcAddress(dll,"CancelPrivateCheckpointSave"));
    auto stopObserver=reinterpret_cast<SaveInstall>(GetProcAddress(dll,"StopPrivateCheckpointSaveObserver"));
    report=reinterpret_cast<PrivateCheckpointSaveReportData*>(GetProcAddress(dll,"PrivateCheckpointSaveReport"));
    if(!install||!cancel||!report||!stopObserver)return 5;
    DWORD installed=install(&input),duplicate=install(&input);
    if(test==L"late-local")existingFile(input.targetPath);
    if(test==L"cancel")cancel(nullptr);
    HANDLE thread=CreateThread(nullptr,0,tick,nullptr,0,nullptr);
    if(!thread||WaitForSingleObject(thread,10000)!=WAIT_OBJECT_0)return 6;CloseHandle(thread);
    if(test==L"save-stall")stopObserver(nullptr);
    const bool lifecycleCase=test==L"native-failure"||test==L"globals-not-cleared"||test==L"wrong-save-object"||test==L"request-replaced"||test==L"bad-save-phase"||test==L"save-stall";
    const bool successCase=test==L"queue"||test==L"heap-name-queue"||test==L"heap-both-queue"||test==L"empty-vector-queue"||test==L"heap-empty-vector-queue";
    const bool queueWanted=successCase||test==L"queue-failure"||lifecycleCase;
    const bool binderWanted=queueWanted||test==L"binder-mismatch"||test==L"binder-exception"||test==L"heap-bind-mismatch";
    LONG expected=successCase||lifecycleCase?4:dryCase?3:test==L"cancel"?7:test==L"binder-exception"?6:5;
    bool passed=report->status==expected && binds==unsigned(binderWanted) && queues==unsigned(queueWanted) &&
        originals==11&&argumentsOk&&report->activeCallbacks==0&&duplicate==1001&&
        *reinterpret_cast<SaveUpdate*>(image+0x12CC4A8+0x28)==&original &&
        *reinterpret_cast<SaveUpdate*>(image+0x12DC5F8+0x28)==&saveOriginal && report->saveActiveCallbacks==0;
    if(binderWanted)passed=passed&&intentBeforeBinder&&report->intentFlushed==1;
    if(successCase||dryCase)passed=passed&&installed==0&&report->installerThread!=report->executorThread&&storageQueries==1;
    if(dryCase)passed=passed&&!report->intentCreated&&GetFileAttributesW(input.intentPath)==INVALID_FILE_ATTRIBUTES;
    const bool lifecycleOk=report->savePhaseMask==31 && report->saveAssociationOk==1 && report->saveWorkerStarted==1 && report->saveWorkerJoined==1 &&
        report->saveNativeSuccess==1 && report->saveFinalizerCalled==1 && report->saveFinalizerReturned==1 && report->saveGlobalsCleared==1 && report->saveObservationDone==1 && !report->saveObservationError;
    if(successCase)passed=passed&&lifecycleOk;
    if(test==L"empty-vector-dry")passed=passed&&*reinterpret_cast<uint64_t*>(manager+0x38)==0&&*reinterpret_cast<uintptr_t*>(manager+0x40)==0;
    if(test==L"empty-vector-queue"||test==L"heap-empty-vector-queue")passed=passed&&*reinterpret_cast<uint64_t*>(manager+0x38)==64&&*reinterpret_cast<uintptr_t*>(manager+0x40)==image+0x250000;
    if(test==L"heap-name-queue"||test==L"heap-both-queue"||test==L"heap-name-dry")
        passed=passed&&*reinterpret_cast<uint64_t*>(image+0x201ED18+24)==31&&*reinterpret_cast<uintptr_t*>(image+0x201ED18)==image+0x2A0000&&globalData(image+0x201ED18)[0]==0;
    if(test==L"heap-both-queue")passed=passed&&*reinterpret_cast<uint64_t*>(image+0x201ED38+24)==31&&*reinterpret_cast<uintptr_t*>(image+0x201ED38)==image+0x2A0100&&globalData(image+0x201ED38)[0]==0;
    if(lifecycleCase)passed=passed&&!lifecycleOk;
    printf("{\"case\":\"%ls\",\"passed\":%s,\"status\":%ld,\"error\":%ld,\"install_result\":%lu,\"original_calls\":%u,\"binder_calls\":%u,\"queue_calls\":%u,\"storage_queries\":%u,\"intent_created\":%lu,\"intent_flushed\":%lu,\"hook_restored\":%s,\"lifecycle_ok\":%s,\"observation_error\":%lu,\"config_size\":%zu,\"report_size\":%zu,\"native_saved\":false}\n",
        test.c_str(),passed?"true":"false",report->status,report->error,installed,originals,binds,queues,storageQueries,
        report->intentCreated,report->intentFlushed,*reinterpret_cast<SaveUpdate*>(image+0x12CC4A8+0x28)==&original?"true":"false",lifecycleOk?"true":"false",report->saveObservationError,sizeof(input),sizeof(*report));
    return passed?0:1;
}

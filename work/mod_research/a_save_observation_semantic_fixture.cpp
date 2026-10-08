// Own-memory sampler cases. CONTEXT values are deliberate models, not game traces.
#define wmain recorder_entry_not_run
#include "a_save_observation.cpp"
#undef wmain
int wmain(int argc,wchar_t** argv){
    if(argc!=3)return 2;
    FILE* log=_wfsopen(argv[1],L"wx",_SH_DENYNO);if(!log)return 2;
    auto* memory=static_cast<unsigned char*>(VirtualAlloc(nullptr,0x4000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));if(!memory)return 2;
    const auto archive=uint64_t(memory),stream=archive+0x800,saveStack=archive+0x1000,armyStack=archive+0x2000;
    const uint64_t base=0x140000000;observationPid=123;observationBirth=456;observationBase=base;setExpectedName(L"owned-semantic");
    memcpy(memory+0x10,&stream,8);const uint64_t caller=base+0x16C2D0;memcpy(reinterpret_cast<void*>(armyStack),&caller,8);
    const std::wstring mode=argv[2];bool rejected=false,stopped=false;
    auto hit=[&](uint64_t rva,DWORD tid){CONTEXT c{};c.Rip=base+rva;c.Rsp=tid==11?saveStack:armyStack;c.Rcx=rva==0x2F7C28?archive:base+0x1A24CF0;c.Rdx=stream;c.Rbx=archive;
        if(mode==L"wrong-manager"&&rva==0x16C1A0)++c.Rcx;
        if(mode==L"wrong-stream"&&rva==0x2F7C28)++c.Rdx;
        if(mode==L"wrong-save-return"&&rva==0x2F7C2D)c.Rsp+=8;
        if(mode==L"wrong-worker-return"&&rva==0x16C2B7)c.Rsp+=8;
        stopped=observe(log,GetCurrentProcess(),base,c,tid);
    };
    try{
        emitBinding(log);
        if(mode==L"orphan")hit(0x16C2B7,22);
        if(mode==L"worker-before"||mode==L"no-save"){hit(0x16C1A0,22);hit(0x16C2B7,22);}
        if(mode!=L"no-save"){
            hit(0x2F7C28,11);
            if(mode==L"nested-save")hit(0x2F7C28,11);
            if(mode!=L"save-only"&&mode!=L"worker-before"&&mode!=L"orphan"){
                hit(0x16C1A0,22);if(mode==L"duplicate-worker")hit(0x16C1A0,22);
                if(mode==L"overlap"){hit(0x2F7C2D,11);hit(0x16C2B7,22);}
                else {hit(0x16C2B7,22);hit(0x2F7C2D,11);}
            }else hit(0x2F7C2D,11);
        }
    }catch(const std::exception& error){rejected=true;std::fprintf(log,"{\"event\":\"error\",\"message\":\"%s\"}\n",error.what());}
    fclose(log);VirtualFree(memory,0,MEM_RELEASE);
    std::printf("{\"rejected\":%s,\"complete\":%s,\"stopped\":%s,\"samples\":%llu,\"game_access\":false,\"contexts_are_models\":true}\n",rejected?"true":"false",chainComplete?"true":"false",stopped?"true":"false",sequence);
    return rejected?1:0;
}

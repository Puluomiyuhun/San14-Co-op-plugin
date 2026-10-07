// Own-memory sampler exercise. Not game execution and not a scheduler proof.
#define wmain recorder_entry_not_run
#include "checkpoint_title_join_live.cpp"
#undef wmain
#include <memory>
struct Model {
    uint64_t base=0,load=0,title=0,closure=0,stack=0,scheduler=0,schedulerHandle=0,callstack=0;
    std::vector<void*> allocations;
    HANDLE self=GetCurrentProcess();FILE* log=nullptr;std::string fault;
    uint64_t alloc(size_t n){auto p=VirtualAlloc(nullptr,n,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);need(p!=nullptr,"Fixture allocation");allocations.push_back(p);return uint64_t(p);}
    template<class T>void put(uint64_t a,T v){memcpy(reinterpret_cast<void*>(a),&v,sizeof v);}
    ~Model(){if(log)fclose(log);for(auto p:allocations)VirtualFree(p,0,MEM_RELEASE);}
    Model(const wchar_t* path,const wchar_t* mode){
        for(;*mode;++mode)fault.push_back(char(*mode));
        log=_wfsopen(path,L"wx",_SH_DENYNO);need(log!=nullptr,"Fixture trace");
        base=alloc(0x2100000);load=alloc(0x1000);title=alloc(0x1000);closure=alloc(0x100);stack=alloc(0x100);scheduler=alloc(0x100);schedulerHandle=alloc(0x100);callstack=alloc(0x100);
        put<uint64_t>(load,base+0x12DBD68);put<DWORD>(load+0x470,1);put(load+0x48,closure);put(load+0x50,scheduler);
        put(scheduler+8,schedulerHandle);put<DWORD>(schedulerHandle+0x10,101);
        put<uint64_t>(closure,base+0x12EA4D0);put(closure+8,title);put<uint64_t>(base+0x12EA4D0+0x10,base+0x4FAC30);
        put<uint64_t>(title,base+0x12DAAF0);put<int>(title+0x47C,34);put<DWORD>(title+0x470,13);
        put<uint64_t>(base+0x19E7310+0x10,4);put(base+0x19E7310+0x20,stack);put(base+0x19E7310+0x48,load);
        put(stack+16,title);put(stack+24,load);put<int>(base+0x201ECD0,34);
        const char* name="svdexSC34.s14";memcpy(reinterpret_cast<void*>(base+0x201ECE0),name,14);
        put<uint64_t>(base+0x201ECE0+16,13);put<uint64_t>(base+0x201ECE0+24,15);
        put<uint64_t>(base+0x138E8D0,0x7FFA00123450); // Permitted resident forwarding address.
        need(setExpectedName(L"svdexSC34.s14"),"Fixture name");
        if(fault=="wrong-name")reinterpret_cast<char*>(base+0x201ECE0)[7]='9';
        if(fault=="wrong-closure")put<uint64_t>(closure,base+0x12EA4D8);
    }
    bool sample(uint64_t rva,DWORD tid,uint64_t rcx=0,uint64_t rdx=0,uint64_t rbx=0,uint64_t rdi=0,uint64_t ret=0){
        CONTEXT c{};c.Rip=base+rva;c.Rcx=rcx;c.Rdx=rdx;c.Rbx=rbx;c.Rdi=rdi;c.Rsp=callstack;put(callstack,base+ret);
        return observe(log,self,base,c,tid);
    }
    void start(int role,DWORD tid){
        auto& w=joinedWorkers[role];auto h=alloc(0x100),f=alloc(0x100);
        put(w.control,h);put<uint64_t>(w.control+8,0xBEEF);put(w.control+0x48,f);put<uint64_t>(w.control+0x60,0xCAFE);
        put<uint64_t>(f,base+0x138E8C0);put<uint64_t>(f+8,base+w.payload);put(h+0x10,tid);put<DWORD>(w.control+0x50,1);
        if(fault=="wrong-payload"&&role==2)put<uint64_t>(f+8,base+0x466601);
        if(fault=="alias-thread"&&role==2)put<DWORD>(h+0x10,joinedWorkers[1].thread);
        const uint64_t callers[]={0x4DA2F4,0x4BEEC2,0x4BEF2B};sample(0x834B60,101+DWORD(role),w.control,0,0,0,callers[role]);
        CONTEXT layout{};armPoints(layout,base,base+0x4DA240,tid);
        need(layout.Dr0==base+0x834D98&&layout.Dr1==base+w.payload&&layout.Dr2==base+0x834D9B&&layout.Dr3==base+0x834DB4,"Worker thread layout");
        CONTEXT parent{};armPoints(parent,base,base+0x4DA240,900);
        need(parent.Dr0==base+0x834B60&&parent.Dr2==base+0x4AAF64&&parent.Dr3==base+0x4AAF89,"Parent thread layout");
        for(const auto& active:joinedWorkers)if(active.startSequence&&!active.joinSequence){
            CONTEXT liveLayout{};armPoints(liveLayout,base,base+0x4DA240,active.thread);
            need(liveLayout.Dr0==base+0x834D98&&liveLayout.Dr1==base+active.payload&&liveLayout.Dr2==base+0x834D9B&&liveLayout.Dr3==base+0x834DB4,"Concurrent role-specific layout");
        }
        put<DWORD>(w.control+0x50,0);
    }
    void run(int role){
        auto& w=joinedWorkers[role];sample(0x834D98,w.thread,w.callable,0,w.control,w.handle);
        if(fault=="wrong-worker"&&role==2)put<DWORD>(w.handle+0x10,w.thread+1);
        sample(w.payload,w.thread,w.callable,0,w.control,w.handle,0x123456); // V2 forwarding return allowed.
        if(role==0)put<DWORD>(base+0x201EC08,1);
        if(!(fault=="missing-return"&&role==2))sample(0x834D9B,w.thread,0,0,w.control,w.handle);
        put<DWORD>(w.control+0x50,1);sample(0x834DB4,w.thread,0,0,w.control,w.handle);
        if(fault=="duplicate-done"&&role==2)sample(0x834DB4,w.thread,0,0,w.control,w.handle);
    }
    void join(int role){
        auto& w=joinedWorkers[role];put<uint64_t>(w.control,0);put<uint64_t>(w.control+8,0);put<uint64_t>(w.control+0x60,0);
        if(fault=="uncleared-join"&&role==2)put<uint64_t>(w.control+0x60,0xCAFE);
        const uint64_t rvas[]={0x4F7079,0x4AAF64,0x4AAF89};sample(rvas[role],901+DWORD(role),0,0,role?title:load);
    }
    void execute(){
        sample(0x4DA240,101,load,0,0,0,0x111111);start(0,201);put<DWORD>(load+0x470,2);run(0);join(0);
        sample(0x4CC690,902,title,load,0,0,0x497134);start(1,202);put<DWORD>(title+0x470,15);
        put<uint64_t>(base+0x19E7310+0x10,3);
        DWORD oldProtect=0;need(VirtualProtect(reinterpret_cast<void*>(load),0x1000,PAGE_NOACCESS,&oldProtect)!=FALSE,"Retire Load memory");
        run(1);start(2,203);put<DWORD>(title+0x470,16);
        if(fault=="late590"){join(1);run(2);}else {run(2);join(1);}join(2);
        need(chainComplete&&sequence==20,"Complete twenty-sample chain");
    }
};
int wmain(int argc,wchar_t** argv){
    if(argc!=3)return 2;
    try {Model model(argv[1],argv[2]);model.execute();std::printf("{\"result\":\"PASS\",\"module_base\":%llu,\"samples\":%llu,\"game_access\":false}\n",model.base,sequence);return 0;}
    catch(const std::exception& e){std::printf("{\"result\":\"REJECTED\",\"reason\":\"%s\",\"game_access\":false}\n",e.what());return 1;}
}

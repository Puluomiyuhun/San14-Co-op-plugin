#define wmain observerMain
#include "observe_rng_pairs.cpp"
#undef wmain
template<class T> static void put(uint64_t a,T v){std::memcpy(reinterpret_cast<void*>(a),&v,sizeof(v));}
static uint64_t alloc(size_t n){auto p=VirtualAlloc(nullptr,n,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);if(!p)throw std::runtime_error("fixture allocation");return reinterpret_cast<uint64_t>(p);}
int main(){try{
    uint64_t base=alloc(0x2240000),root=alloc(0x90000),world=alloc(0x1800),state=alloc(0x500),states=alloc(16),stack=alloc(4096);
    put(base+0x1fca1e0,root);put(root+0x85130,world);put(world,base+0x12aa638);
    put<uint16_t>(world+0x34,203);put<uint8_t>(world+0x36,8);put<uint8_t>(world+0x37,11);put<uint8_t>(world+0x38,10);put<uint8_t>(world+0x3a,12);
    put(base+0x19e7690+0x50,base+0x123e520);put<int32_t>(base+0x19e7690+0x230,3);
    put(base+0x19e7310+0x10,uint64_t(1));put(base+0x19e7310+0x20,states);put(states,state);put(state,base+0x12cc770);
    std::memcpy(reinterpret_cast<void*>(state+0x70),"CProgressState",15);put<uint32_t>(state+0x484,12);
    rngAddress=base+0x18eb8b0;rangeAddress=base+0x3aa7c0;percentageAddress=base+0x3aa3f0;
    put<uint32_t>(rngAddress,1234);previousObservedRng=1234;
    auto caller=reinterpret_cast<uint64_t>(&main);put(stack,caller);
    TracedThread t{};CONTEXT c{};c.Rip=rangeAddress;c.Rcx=3;c.Rsp=stack;c.Dr6=1;
    if(observe(stdout,GetCurrentProcess(),base,c,1,t)||c.Dr3!=caller||!(c.Dr7&0x40))return 1;
    c.Rip=base+0x3aa80b;c.Rax=5678;c.Dr6=4;put<uint32_t>(rngAddress,5678);
    if(observe(stdout,GetCurrentProcess(),base,c,1,t))return 2;
    c.Rip=caller;c.Rsp=stack+8;c.Rax=2;c.Dr6=8;
    if(observe(stdout,GetCurrentProcess(),base,c,1,t)||t.pending.id||c.Dr3||(c.Dr7&0x40))return 3;
    FILE* sink=nullptr;if(tmpfile_s(&sink)!=0||!sink)return 4;
    bool rejected=false;try{observe(sink,GetCurrentProcess(),base,c,1,t);}catch(const std::exception&){rejected=true;}
    std::fclose(sink);if(!rejected)return 5;
    std::printf("{\"event\":\"unpaired_return_rejected\",\"result\":\"PASS\"}\n");return 0;
}catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());return 9;}}

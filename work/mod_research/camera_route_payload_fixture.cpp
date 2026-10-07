#define wmain observerMain
#include "observe_camera_route.cpp"
#undef wmain
template<class T> static void put(uint64_t a,T v){std::memcpy(reinterpret_cast<void*>(a),&v,sizeof(v));}
static uint64_t alloc(size_t n){auto p=VirtualAlloc(nullptr,n,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);if(!p)throw std::runtime_error("fixture allocation");return reinterpret_cast<uint64_t>(p);}
int main(){
    try{
        uint64_t base=alloc(0x2240000),root=alloc(0x90000),world=alloc(0x1800),army=alloc(501*0x200);
        uint64_t state=alloc(0x500),states=alloc(16),record=alloc(0x100),stack=alloc(4096);
        put(base+0x1fca1e0,root);put(root+0x85130,world);put(world,base+0x12aa638);
        put<uint16_t>(world+0x34,203);put<uint8_t>(world+0x36,8);put<uint8_t>(world+0x37,11);put<uint8_t>(world+0x38,10);put<uint8_t>(world+0x3a,12);
        put(base+0x19e7690+0x50,base+0x123e520);put<int32_t>(base+0x19e7690+0x230,3);
        put(base+0x19e7310+0x10,uint64_t(1));put(base+0x19e7310+0x20,states);put(states,state);put(state,base+0x12cc770);
        std::memcpy(reinterpret_cast<void*>(state+0x70),"CProgressState",15);put<uint32_t>(state+0x484,12);
        for(unsigned i=0;i<501;i++)put(root+0x7df60+i*8,army+i*0x200);
        put(army+17*0x200,base+0x123e288);put<uint8_t>(army+17*0x200+0x10,1);put<uint16_t>(army+17*0x200+0x12,215);
        put<uint16_t>(army+17*0x200+0x16,11000);put<uint32_t>(record+8,0x1b);put<uint32_t>(record+12,17);
        CONTEXT c{};c.Rsp=stack;c.Rip=base+0x15b070;c.Rcx=base+0x1a38a20;c.Rdx=record;
        if(observe(stdout,GetCurrentProcess(),base,c,1))return 1;
        c.Rip=base+0x15b12f;c.Rbx=record;c.Rax=1;if(observe(stdout,GetCurrentProcess(),base,c,1))return 2;
        put<int32_t>(base+0x19e7690+0x230,4);c.Rax=0;if(observe(stdout,GetCurrentProcess(),base,c,1))return 3;
        uint64_t linked=alloc(0xb0);put(base+0x19e7690+0x280,linked);
        c.Rip=base+0x3aa805;c.Rax=5678;c.Rcx=3;put<uint32_t>(base+0x18eb8b0,1234);put(stack,base+0x3b3779);
        if(observe(stdout,GetCurrentProcess(),base,c,1))return 4;
        c.Rip=base+0x3f9344;c.Rbx=state;c.Rbp=1;c.Rsi=5;if(observe(stdout,GetCurrentProcess(),base,c,1))return 5;
        put<uint8_t>(world+0x37,21);if(!pastTurn(GetCurrentProcess(),base))return 6;
        std::printf("{\"event\":\"turn_end_boundary\",\"result\":\"PASS\"}\n");
        put(base+0x19e7690+0x50,uint64_t(0));FILE* sink=nullptr;if(tmpfile_s(&sink)!=0||!sink)return 9;bool rejected=false;
        try{cameraState(sink,GetCurrentProcess(),base);}catch(const std::exception&){rejected=true;}
        std::fclose(sink);if(!rejected)return 7;
        std::printf("{\"event\":\"wrong_camera_type_rejected\",\"result\":\"PASS\"}\n");return 0;
    }catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());return 8;}
}

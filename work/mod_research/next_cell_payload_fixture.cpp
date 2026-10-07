#define wmain observerMain
#include "observe_next_cell.cpp"
#undef wmain
template<class T> static void put(uint64_t a,T v){std::memcpy(reinterpret_cast<void*>(a),&v,sizeof(v));}
static uint64_t alloc(size_t n){auto p=VirtualAlloc(nullptr,n,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);if(!p)throw std::runtime_error("fixture allocation");return reinterpret_cast<uint64_t>(p);}
int main(){
    try{
        uint64_t base=alloc(0x2240000),root=alloc(0x90000),world=alloc(0x1800),armies=alloc(501*0x200);
        uint64_t pool=base+0x201d3a0,heads=alloc(0x14000*8),counts=alloc(0x14000*8),handle=alloc(16),node=alloc(32);
        uint64_t state=alloc(0x500),states=alloc(16),manager=base+0x1a24cf0;
        put(base+0x1fca1e0,root);put(root+0x85130,world);put(world,base+0x12aa638);
        put<uint16_t>(world+0x34,203);put<uint8_t>(world+0x36,8);put<uint8_t>(world+0x37,11);put<uint8_t>(world+0x38,10);
        put<uint8_t>(world+0x3a,12);put(root+0x7df60,armies);put(root+0x7df60+17*8,armies+17*0x200);
        uint64_t unit=armies+17*0x200;put(unit,base+0x123e288);put<uint16_t>(unit+0x12,215);
        put<uint16_t>(unit+0x16,11000);put<uint16_t>(unit+0x2a,24023);put<uint16_t>(unit+0x48,23804);
        put(pool+0x10,heads);put(pool+0x28,counts);put<uint32_t>(pool+0x40,0x14000);put<uint32_t>(handle,1);
        put(manager+8,handle);put(heads+8,node);put<uint64_t>(counts+8,1);put(node,unit);
        put<uint32_t>(manager+0x90,1);put<uint32_t>(manager+0x70,0);
        put(base+0x19e7310+0x10,uint64_t(1));put(base+0x19e7310+0x20,states);put(states,state);put(state,base+0x12cc770);
        std::strcpy(reinterpret_cast<char*>(state+0x70),"CProgressState");put<uint32_t>(state+0x484,24);
        watches[0]=unit+0x48;fixtureMode=false;
        std::printf("{\"event\":\"synthetic_snapshot\",");bool late=snapshot(stdout,GetCurrentProcess(),base);std::printf(",\"late\":%s}\n",late?"true":"false");if(late)return 1;
        put<uint8_t>(world+0x37,13);
        std::printf("{\"event\":\"synthetic_late\",");late=snapshot(stdout,GetCurrentProcess(),base);std::printf(",\"late\":%s}\n",late?"true":"false");if(!late)return 2;
        FILE* sink=std::tmpfile();if(!sink)return 3;put(node+8,node);bool rejected=false;
        try{workList(sink,GetCurrentProcess(),base,manager,0);}catch(const std::exception&){rejected=true;}
        std::fclose(sink);if(!rejected)return 4;
        std::printf("{\"event\":\"malformed_cycle\",\"result\":\"PASS\"}\n");return 0;
    }catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());return 5;}
}

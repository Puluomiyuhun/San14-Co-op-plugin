// Exercise all game-mode payload readers against a local synthetic memory map.
// No game process is opened or modified. This is not a native game simulation.
#define wmain unused_observer_main
#include "observe_first_batch.cpp"
#undef wmain
#include <array>
#include <memory>

template<class T> static void put(uint64_t address,T value) { std::memcpy(reinterpret_cast<void*>(address),&value,sizeof(value)); }
static void require(bool condition,const char* message) { if(!condition)throw std::runtime_error(message); }
int wmain(int argc,wchar_t** argv) {
    if(argc!=2)return 2;
    FILE* log=nullptr;unsigned char* module=nullptr;
    try {
        module=static_cast<unsigned char*>(VirtualAlloc(nullptr,0x2200000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));require(module!=nullptr,"allocate module");
        uint64_t base=reinterpret_cast<uint64_t>(module);
        std::vector<unsigned char> rootBytes(0x86000),worldBytes(0x1700),armyBytes(501*0x200),cityBytes(52*0x100),forceBytes(52*0x200),progressBytes(0x500),stackBytes(0x120);
        auto address=[](auto& v){return reinterpret_cast<uint64_t>(v.data());};
        uint64_t root=address(rootBytes),world=address(worldBytes),first=address(armyBytes),progress=address(progressBytes),stack=address(stackBytes);
        put<uint64_t>(base+0x1FCA1E0,root);put<uint64_t>(root+0x85130,world);put<uint64_t>(world,base+0x12AA638);
        put<uint16_t>(world+0x34,203);put<uint8_t>(world+0x36,8);put<uint8_t>(world+0x37,11);put<uint8_t>(world+0x38,10);put<uint8_t>(world+0x3a,12);
        put<uint64_t>(progress,base+0x12CC770);put<uint32_t>(progress+0x484,12);put<uint32_t>(stack+0x30,1234);put<uint64_t>(stack,base+0x3F935A);
        for(unsigned i=0;i<501;i++) {put<uint64_t>(root+0x7DF60+i*8,first+i*0x200);put<uint64_t>(first+i*0x200,base+0x123E288);}
        for(unsigned i=1;i<=2;i++) {put<uint8_t>(first+i*0x200+0x10,1);put<uint16_t>(first+i*0x200+0x12,uint16_t(i));}
        for(unsigned i=0;i<52;i++) {put<uint64_t>(root+0xDAA8+i*8,address(cityBytes)+i*0x100);put<uint64_t>(root+0xDCA0+i*8,address(forceBytes)+i*0x200);}
        std::array<uint64_t,5> heads{},tails{},counts{};std::array<uint32_t,5> handles{0,1,2,3,4};
        std::array<uint64_t,1> annHeads{},annTails{},annCounts{};
        const unsigned offsets[]={0x58,0x68,0x88,0x98,0x138};
        for(unsigned i=0;i<5;i++) {put<uint64_t>(root+offsets[i],base+(i==4?0x12AA618:i==2?0x123F3C8:i==3?0x123F3D8:0x123E200));put<uint64_t>(root+offsets[i]+8,reinterpret_cast<uint64_t>(&handles[i]));}
        handles[4]=0;
        uint64_t pointerPool=base+0x201D3A0,annPool=base+0x1FC9760;
        for(uint64_t pool:{pointerPool,annPool})put<uint64_t>(pool+8,1);
        put<uint32_t>(pointerPool+0x40,0x14000);put<uint64_t>(pointerPool+0x10,address(heads));put<uint64_t>(pointerPool+0x18,address(tails));put<uint64_t>(pointerPool+0x28,address(counts));
        put<uint32_t>(annPool+0x40,0x40);put<uint64_t>(annPool+0x10,address(annHeads));put<uint64_t>(annPool+0x18,address(annTails));put<uint64_t>(annPool+0x28,address(annCounts));
        std::array<uint64_t,3> firstNode{first+0x200,0,0},secondNode{first+0x400,0,address(firstNode)};
        firstNode[1]=address(secondNode);heads[0]=address(firstNode);tails[0]=address(secondNode);counts[0]=2;
        std::array<uint64_t,8> annNode{};annNode[0]=first+0x400;annNode[1]=first+0x200;annNode[2]=first+0x400;
        annHeads[0]=annTails[0]=address(annNode);annCounts[0]=1;
        std::array<unsigned char,32> side{};std::array<unsigned char,64> pair{};
        put<uint16_t>(address(side),1);put<uint32_t>(address(side)+4,27);put<uint64_t>(address(pair),address(side));put<uint16_t>(address(pair)+8,2);put<uint32_t>(address(pair)+12,27);
        put<uint64_t>(base+0x1A388E0,address(pair));put<uint64_t>(base+0x1A38900,1);
        log=_wfsopen(argv[1],L"w",_SH_DENYNO);require(log!=nullptr,"open output");
        CONTEXT c{};c.Rbx=progress;c.Rsp=stack;c.Rbp=0;c.Rsi=0;c.Rip=base+0x3F9344;
        put<uint8_t>(world+0x38,0);require(!observe(log,GetCurrentProcess(),base,c,1),"early gate");
        armPoints(c,base,base+0x3F9344);require(c.Dr0==base+0x3F9344&&c.Dr2==base+0x16C685,"initial points");
        put<uint8_t>(world+0x38,10);c.Rbp=1;c.Rsi=5;require(!observe(log,GetCurrentProcess(),base,c,1),"scheduled gate");
        armPoints(c,base,base+0x3F9344);require(c.Dr0==base+0x3F935F&&c.Dr2==base+0x16C685,"boundary point switch");
        c.Rip=base+0x16C640;c.Rcx=base+0x1A24CF0;require(!observe(log,GetCurrentProcess(),base,c,1),"entry");
        c.Rip=base+0x16C685;c.Rbx=base+0x1A24CF0;c.Rax=1;require(!observe(log,GetCurrentProcess(),base,c,1),"ready");
        armPoints(c,base,base+0x3F9344);require(c.Dr2==base+0x16AC60,"damage point switch");
        c.Rip=base+0x15C045;c.R15=base+0x1A38840;c.Rbx=address(pair);c.Rbp=1;
        put<uint32_t>(stack+0xA8,1);put<uint32_t>(stack+0xAC,2);require(!observe(log,GetCurrentProcess(),base,c,1),"eligibility");
        c.Rip=base+0x16AC60;c.Rcx=27;c.Rdx=2;c.R8=11;c.R9=27;put<uint32_t>(stack+0x28,1);
        require(!observe(log,GetCurrentProcess(),base,c,1),"damage");
        c.Rip=base+0x3F935F;c.Rbx=progress;c.Rbp=1;put<uint32_t>(progress+0x484,13);
        require(observe(log,GetCurrentProcess(),base,c,1),"boundary stop");
        std::fclose(log);log=nullptr;
        // Corrupt fixtures must fail before any repeated traversal or silent acceptance.
        FILE* sink=nullptr;fopen_s(&sink,"NUL","w");require(sink!=nullptr,"open fixture sink");
        auto rejects=[&](){bool rejected=false;try{inputLists(sink,GetCurrentProcess(),base,root);}catch(const std::exception&){rejected=true;}return rejected;};
        secondNode[2]=0;require(rejects(),"bad reverse link accepted");secondNode[2]=address(firstNode);
        annCounts[0]=129;require(rejects(),"oversized annihilation list accepted");annCounts[0]=1;
        annNode[6]=address(annNode);require(rejects(),"annihilation cycle accepted");annNode[6]=0;
        std::fclose(sink);
        std::printf("{\"result\":\"PASS\",\"payload_cases\":7,\"scope\":\"local synthetic memory, six event types and two adaptive point changes\"}\n");
        VirtualFree(module,0,MEM_RELEASE);return 0;
    }catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());if(log)std::fclose(log);if(module)VirtualFree(module,0,MEM_RELEASE);return 1;}
}

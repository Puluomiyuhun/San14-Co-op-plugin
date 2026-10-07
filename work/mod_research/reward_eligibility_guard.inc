// Shared bounded read-only object and indirect-target checks.
static bool readList(uintptr_t list,uintptr_t vt,uintptr_t poolRva,uint32_t capacity,
                     uintptr_t* output,uint32_t* length,bool integers=false) {
    if(at<uintptr_t>(list)!=gameBase+vt) return reject(60);
    *length=0;
    auto handle=at<uintptr_t>(list+8);
    if(!handle) return true;
    auto pool=gameBase+poolRva;
    if(!at<uintptr_t>(pool+8) || at<uint32_t>(pool+0x40)!=capacity) return reject(60);
    auto slot=at<uint32_t>(handle);
    if(slot>=capacity) return reject(60);
    auto heads=at<uintptr_t>(pool+0x10),tails=at<uintptr_t>(pool+0x18),counts=at<uintptr_t>(pool+0x28);
    if(!heads || !tails || !counts) return reject(60);
    auto count=at<uint64_t>(counts+slot*8);
    if(count>ELIGIBILITY_LIMIT) return reject(60);
    auto node=at<uintptr_t>(heads+slot*8);
    uintptr_t previous=0;
    while(node) {
        if(*length>=count || at<uintptr_t>(node+16)!=previous) return reject(60);
        output[(*length)++]=integers?at<uint32_t>(node):at<uintptr_t>(node);
        previous=node; node=at<uintptr_t>(node+8);
    }
    if(*length!=count || at<uintptr_t>(tails+slot*8)!=previous) return reject(60);
    return true;
}

static bool eligibilityObjectGuard(uintptr_t root) {
    // Validate every possible indirect target that the predicate may reach.
    for(unsigned i=0;i<=500;i++) {
        auto unit=at<uintptr_t>(root+0x7DF60+i*8);
        if(at<uintptr_t>(unit)!=gameBase+0x123E288) return reject(61);
    }
    if(at<uintptr_t>(gameBase+0x123E288+0x18)!=gameBase+0x211420 ||
       at<uintptr_t>(gameBase+0x12A00D0+0x18)!=gameBase+0x2119F0 ||
       at<uintptr_t>(gameBase+0x129FEC8+0x18)!=gameBase+0x211610 ||
       at<uintptr_t>(gameBase+0x129FE58+0x60)!=gameBase+0x20B610) return reject(61);
    for(unsigned i=0;i<=51;i++) {
        if(at<uintptr_t>(at<uintptr_t>(root+0xDE40+i*8))!=gameBase+0x129FEC8 ||
           at<uintptr_t>(at<uintptr_t>(root+0xDCA0+i*8))!=gameBase+0x129FE58) return reject(61);
    }
    uintptr_t actions[ELIGIBILITY_LIMIT]{},ids[ELIGIBILITY_LIMIT]{};
    uint32_t count=0;
    auto manager=at<uintptr_t>(root+0x85128);
    if(!readList(manager+0x10,0x129BB28,0x201D3A0,0x14000,actions,&count)) return false;
    for(unsigned i=0;i<count;i++) {
        auto action=actions[i],vt=at<uintptr_t>(action);
        auto rva=vt-gameBase;
        bool travel=rva==0x129BB48 || rva==0x129BC90;
        if(!travel && rva!=0x129BF20 && rva!=0x129C068 && rva!=0x129C2F8 && rva!=0x129C440) return reject(62);
        if(at<uintptr_t>(vt+0x18)!=gameBase+(rva==0x129BC90?0x1D4340:0x1D4330) ||
           at<uintptr_t>(vt+0xB0)!=gameBase+(travel?0x20BA50:0x20BAA0)) return reject(62);
        uint32_t length=0;
        if(!readList(action+0x18,0x123E210,NODE_POOL_RVA,0x400,ids,&length,true)) return false;
        for(unsigned n=0;n<length;n++) if(ids[n]==0 || ids[n]>=6000) return reject(62);
    }
    return true;
}


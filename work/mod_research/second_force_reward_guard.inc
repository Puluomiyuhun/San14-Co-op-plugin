// This pilot keeps the host's real local player as Zhang Lu (12).
static bool hostGuard() {
    auto root=at<uintptr_t>(gameBase+0x1FCA1E0),world=at<uintptr_t>(root+0x85130);
    auto city=at<uintptr_t>(root+0xDAA8+19*8),district=at<uintptr_t>(root+0xDE40+11*8);
    if(at<uint8_t>(world+0x3A)!=12 || at<uintptr_t>(city)!=gameBase+0x129FD10 ||
       at<uintptr_t>(district)!=gameBase+0x129FEC8 || at<uint16_t>(city+0x10)!=19 ||
       at<uint8_t>(city+0x30)!=11 || at<uint8_t>(district+0x10)!=12 ||
       at<uint32_t>(city+0x34)!=83308 || at<uint32_t>(city+0x3C)!=15204 ||
       at<uint8_t>(district+0x14)!=18) return reject(75);
    return true;
}
// Fixed checkpoint/context restrictions are deliberate: this is not a generic executor.
static bool guard(void* self) {
    if(!hostGuard())return false;
    auto manager=gameBase+0x19E7310,stack=at<uintptr_t>(manager+0x20);
    if(at<uint64_t>(manager+0x10)!=5 || !stack || at<uintptr_t>(stack+32)!=uintptr_t(self) ||
       at<uintptr_t>(uintptr_t(self))!=gameBase+PROBE_VTABLE_RVA || at<uint32_t>(uintptr_t(self)+0x470)!=2) return reject(10);
    auto root=at<uintptr_t>(gameBase+0x1FCA1E0),world=at<uintptr_t>(root+0x85130);
    if(at<uint16_t>(world+0x34)!=203 || at<uint8_t>(world+0x36)!=8 ||
       at<uint8_t>(world+0x37)!=11 || at<uint8_t>(world+0x3A)!=12) return reject(11);
    auto city=at<uintptr_t>(root+0xDAA8+13*8),district=at<uintptr_t>(root+0xDE40+2*8);
    auto ruler=at<uintptr_t>(root+0x148+952*8),force=at<uintptr_t>(root+0xDCA0+2*8);
    if(at<uintptr_t>(city)!=gameBase+0x129FD10 || at<uintptr_t>(ruler)!=gameBase+0x12A00D0 ||
       at<uintptr_t>(district)!=gameBase+0x129FEC8 || at<uintptr_t>(force)!=gameBase+0x129FE58 ||
       at<uint16_t>(force+0x10)!=952 || at<uint16_t>(city+0x10)!=13 || at<uint8_t>(city+0x30)!=2 ||
       at<uint8_t>(district+0x10)!=2 || at<uint16_t>(district+0x12)!=952 || at<uint16_t>(ruler+0x10)!=952 ||
       at<uint16_t>(ruler+0x11A)!=at<uint16_t>(city+0x4E)) return reject(12);
    if(at<uint32_t>(city+0x34)!=20804 || at<uint32_t>(city+0x3C)!=4639 || at<uint8_t>(district+0x14)!=10) return reject(13);
    for(unsigned i=0;i<3;i++) {
        auto person=at<uintptr_t>(root+0x148+PROBE_IDS[i]*8);
        auto owner=at<uintptr_t>(root+0xDE40+2*8);
        if(at<uintptr_t>(person)!=gameBase+0x12A00D0 || at<uint16_t>(person+0x10)!=PROBE_IDS[i] ||
           at<uint8_t>(person+0x118)!=2 || at<uintptr_t>(owner)!=gameBase+0x129FEC8 || at<uint8_t>(owner+0x10)!=2) return reject(14);
        if(at<uint8_t>(person+0x120)!=PROBE_LOYALTY[i] || at<uint16_t>(person+0x196)!=128 ||
           at<uint8_t>(person+0x11E)!=4) return reject(15);
    }
    return true;
}

static bool nativePreflight() {
    auto root=at<uintptr_t>(gameBase+0x1FCA1E0);
    if(!eligibilityObjectGuard(root)) return false;
    if(at<uintptr_t>(gameBase+0x129FD10+0x18)!=gameBase+0x211540 ||
       at<uintptr_t>(gameBase+0x129FD10+0x80)!=gameBase+0x209A00 ||
       at<uintptr_t>(gameBase+0x129FD10+0x90)!=gameBase+0x20C2E0) return reject(65);
    uintptr_t entries[ELIGIBILITY_LIMIT]{};uint32_t count=0;
    auto expected=at<uintptr_t>(root+0xDE40+2*8);
    if(!readList(root+0xC8,0x123F3F8,0x201D3A0,0x14000,entries,&count)) return false;
    uintptr_t main=0;
    for(unsigned i=0;i<count;i++) {
        auto d=entries[i];if(at<uintptr_t>(d)!=gameBase+0x129FEC8)return reject(66);
        if(at<uint8_t>(d+0x10)==2 && (at<uint16_t>(d+0x12)==952 || at<uint8_t>(d+0x11)==1)) {main=d;break;}
    }
    if(main!=expected)return reject(66);
    if(!readList(root+0x78,0x123F3B8,0x201D3A0,0x14000,entries,&count))return false;
    auto city=at<uintptr_t>(root+0xDAA8+13*8),ruler=at<uintptr_t>(root+0x148+952*8);
    uintptr_t funding=0;
    for(unsigned i=0;i<count;i++) {
        if(at<uint16_t>(entries[i]+0x4E)==at<uint16_t>(ruler+0x11A)) {funding=entries[i];break;}
    }
    if(funding!=city)return reject(67);
    for(unsigned i=0;i<3;i++) {
        RewardExecutionReport.predicateCalls++;
        if(eligibilityPredicate(at<uintptr_t>(root+0x148+PROBE_IDS[i]*8))!=1)return reject(68);
        RewardExecutionReport.loyaltyBefore[i]=PROBE_LOYALTY[i];
    }
    RewardExecutionReport.goldBefore=20804;RewardExecutionReport.actionsBefore=10;
    return true;
}

static bool postcheck() {
    if(!hostGuard())return false;
    auto root=at<uintptr_t>(gameBase+0x1FCA1E0);
    auto city=at<uintptr_t>(root+0xDAA8+13*8),district=at<uintptr_t>(root+0xDE40+2*8);
    RewardExecutionReport.goldAfter=at<uint32_t>(city+0x34);
    RewardExecutionReport.actionsAfter=at<uint8_t>(district+0x14);
    bool ok=RewardExecutionReport.goldAfter==20504 && RewardExecutionReport.actionsAfter==9 && at<uint32_t>(city+0x3C)==4639;
    for(unsigned i=0;i<3;i++) {
        auto person=at<uintptr_t>(root+0x148+PROBE_IDS[i]*8);
        auto loyalty=at<uint8_t>(person+0x120);RewardExecutionReport.loyaltyAfter[i]=loyalty;
        ok=ok && loyalty>PROBE_LOYALTY[i] && loyalty<=100 && at<uint16_t>(person+0x196)==130;
    }
    RewardExecutionReport.postconditions=ok;
    return ok?true:reject(74);
}

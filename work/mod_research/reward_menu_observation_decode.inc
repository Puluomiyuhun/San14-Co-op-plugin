// Bounded read-only decoder corresponding to DomesticDecoder reward layout.
// Debug events stop the process; no game function, constructor or write is used.
#include <sstream>
static void need(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
static uint64_t ptr(HANDLE p,uint64_t a){auto v=rd<uint64_t>(p,a);need(v>=0x10000&&v<0x7fffffffffffULL&&!(v&7),"Invalid object pointer");return v;}
static void typeIs(HANDLE p,uint64_t b,uint64_t object,const char* expected){
    const auto vt=ptr(p,object);need(vt>=b+8&&vt<b+0x2400000,"Vtable outside supported image");
    const auto loc=ptr(p,vt-8);need(loc>=b&&loc<b+0x2400000-24,"RTTI locator outside image");
    uint32_t col[6];readExact(p,loc,col,sizeof col);
    need(col[0]==1&&col[5]==loc-b&&col[3]<0x2400000-160,"RTTI metadata differs");
    char name[128]{};readExact(p,b+col[3]+16,name,sizeof name);need(memchr(name,0,sizeof name)!=nullptr,"Unterminated RTTI name");
    const std::string desired=std::string(".?AV")+expected+"@@";need(desired==name,"RTTI type differs");
}
static unsigned districtOf(HANDLE p,uint64_t b,uint64_t root,uint64_t object){
    typeIs(p,b,object,"CDistrictData");
    for(unsigned id=1;id<=51;++id)if(rd<uint64_t>(p,root+0xDE40+id*8)==object)return id;
    throw std::runtime_error("District does not belong to root table");
}
static unsigned personId(HANDLE p,uint64_t b,uint64_t root,uint64_t object,unsigned force){
    typeIs(p,b,object,"CPersonData");auto id=rd<uint16_t>(p,object+0x10);
    need(id>0&&id<6000&&ptr(p,root+0x148+id*8)==object,"Person identity differs");
    auto did=rd<uint8_t>(p,object+0x118);need(did>0&&did<=51,"Person district invalid");
    auto district=ptr(p,root+0xDE40+did*8);typeIs(p,b,district,"CDistrictData");
    need(rd<uint8_t>(p,district+0x10)==force,"Foreign person selected");return id;
}
static unsigned cityId(HANDLE p,uint64_t b,uint64_t root,uint64_t object,unsigned force){
    typeIs(p,b,object,"CCityData");auto id=rd<uint16_t>(p,object+0x10);
    need(id>0&&id<=51&&ptr(p,root+0xDAA8+id*8)==object,"City identity differs");
    const auto did=rd<uint8_t>(p,object+0x30);need(did>0&&did<=51,"City district invalid");
    auto district=ptr(p,root+0xDE40+did*8);typeIs(p,b,district,"CDistrictData");
    need(rd<uint8_t>(p,district+0x10)==force,"Foreign funding city");return id;
}
struct MenuDraft {
    uint64_t root=0,world=0,state=0;unsigned force=0,district=0,city=0,viewer=0,event=0,year=0,month=0,day=0;
    std::vector<unsigned> officers;
    std::string preview()const{
        std::ostringstream s;s<<"{\"kind\":\"reward\",\"force_id\":"<<force<<",\"district_id\":"<<district
            <<",\"funding_city_id\":"<<city<<",\"officer_ids\":[";
        for(size_t i=0;i<officers.size();++i){if(i)s<<',';s<<officers[i];}s<<"]}";return s.str();
    }
};
static void readPeople(HANDLE p,uint64_t b,MenuDraft& d,uint64_t list,bool ids){
    need(rd<uint64_t>(p,list)==b+(ids?0x123E210:0x123F448),"Unexpected list vtable");
    auto handle=rd<uint64_t>(p,list+8);if(!handle)return;need(!(handle&7)&&handle>=0x10000,"Invalid list handle");
    auto pool=b+(ids?0x19E1BF0:0x201D3A0);need(rd<uint64_t>(p,pool+8)!=0,"List pool disabled");
    auto cap=rd<uint32_t>(p,pool+0x40),slot=rd<uint32_t>(p,handle);
    need(cap>0&&cap<=(ids?0x400U:0x20000U)&&slot<cap,"List pool capacity/slot differs");
    auto heads=ptr(p,pool+0x10),counts=ptr(p,pool+0x28),node=rd<uint64_t>(p,heads+slot*8);
    auto count=rd<uint64_t>(p,counts+slot*8);need(count<=64,"Selection exceeds bounded observation capacity");
    uint64_t previous=0;std::set<uint64_t> seen;std::set<unsigned> people;
    while(node){
        need(!(node&7)&&node>=0x10000&&seen.insert(node).second&&seen.size()<=count,"Cyclic or invalid list");
        unsigned id=0;
        if(ids){id=rd<uint32_t>(p,node);need(id>0&&id<6000,"Invalid ID list element");
            need(rd<uint64_t>(p,node+16)==previous,"ID list predecessor differs");
            need(personId(p,b,d.root,ptr(p,d.root+0x148+id*8),d.force)==id,"ID/person mismatch");}
        else id=personId(p,b,d.root,ptr(p,node),d.force);
        need(people.insert(id).second,"Repeated person");d.officers.push_back(id);previous=node;node=rd<uint64_t>(p,node+8);
    }
    need(d.officers.size()==count,"List count mismatch");
    if(ids)need(rd<uint64_t>(p,ptr(p,pool+0x18)+slot*8)==previous,"ID list tail differs");
}
static MenuDraft decodeMenu(HANDLE p,uint64_t b,uint64_t state,uint64_t args=0){
    MenuDraft d;d.state=state;d.root=ptr(p,b+0x1FCA1E0);typeIs(p,b,d.root,"CSan14Data");
    d.world=ptr(p,d.root+0x85130);typeIs(p,b,d.world,"CWorldData");
    d.viewer=rd<uint8_t>(p,d.world+0x3A);d.year=rd<uint16_t>(p,d.world+0x34);
    d.month=rd<uint8_t>(p,d.world+0x36);d.day=rd<uint8_t>(p,d.world+0x37);
    need(d.viewer>0&&d.viewer<=51&&d.year>0&&d.year<10000&&d.month>0&&d.month<=12&&d.day>0&&d.day<=30,"Invalid world identity/date");
    typeIs(p,b,state,"CStrategyRewardState");const auto manager=b+0x19E7310;
    auto n=rd<uint64_t>(p,manager+0x10),stack=ptr(p,manager+0x20);
    need(n>=6&&n<=16&&rd<uint64_t>(p,stack+(n-1)*8)==state,"Reward menu is not active stack top");
    need(rd<uint64_t>(p,stack+32)==selectedUser&&rd<uint32_t>(p,selectedUser+0x470)==2,"Planning User identity changed");
    auto district=ptr(p,state+0x470);d.district=districtOf(p,b,d.root,district);d.force=rd<uint8_t>(p,district+0x10);
    need(d.force==d.viewer,"Reward menu not local viewer");
    auto leaderId=rd<uint16_t>(p,district+0x12);need(leaderId>0&&leaderId<6000,"District leader invalid");
    auto leader=ptr(p,d.root+0x148+leaderId*8);personId(p,b,d.root,leader,d.force);
    const auto location=rd<uint16_t>(p,leader+0x11A);uint64_t city=0;
    for(unsigned id=1;id<=51;++id){auto candidate=ptr(p,d.root+0xDAA8+id*8);if(rd<uint16_t>(p,candidate+0x4E)==location){city=candidate;break;}}
    need(city!=0,"Funding location is not a supported city");d.city=cityId(p,b,d.root,city,d.force);
    auto layout=ptr(p,state+0x478);d.event=rd<uint32_t>(p,layout+0x170);
    if(args){need(ptr(p,args+0x10)==city,"Common funding differs from menu");readPeople(p,b,d,args,true);}
    else readPeople(p,b,d,state+0x480,false);
    return d;
}

#include "checkpoint_target_metadata_core.h"
#include <cstdio>
#include <cstring>
#include <fstream>
#include <vector>
#include <stdexcept>
#include <filesystem>
using namespace checkpoint_target_metadata;
template<class T>static void put(void*p,std::size_t o,T v){std::memcpy((unsigned char*)p+o,&v,sizeof v);}
template<class T>static T get(void*p,std::size_t o){T v;std::memcpy(&v,(unsigned char*)p+o,sizeof v);return v;}
static void require(bool v,const char*what){if(!v)throw std::runtime_error(what);}
struct Context {
    std::string test;std::vector<unsigned char> bytes;
    unsigned char manager[0x500]{},head[16]{},groups[4][16]{},old[0x160]{},foreign[0x160]{},extra[50][0x160]{};
    void* allocation=nullptr;unsigned guards=0,parses=0,copies=0,frees=0,reads=0;
    bool drift=false,nativeOccupied=false,postCommitFail=false;
    std::uint64_t currentGeneration=301;
    ~Context(){if(allocation)free(allocation);}
};
static bool storageValid(void*){return true;}
static bool storageExists(void*,const char*name){return !std::strcmp(name,TargetName);}
static std::int32_t storageSize(void*,const char*){return TargetSize;}
static std::int32_t storageRead(void*p,const char*,void*out,std::int32_t amount){auto&c=*(Context*)p;++c.reads;std::memcpy(out,c.bytes.data(),amount);if(c.test=="bad_native_bytes")((unsigned char*)out)[100]^=1;return amount;}
static bool boundary(void*p,const Boundary&b){auto&c=*(Context*)p;++c.guards;return b.cacheGeneration==c.currentGeneration&&!c.drift&&!(c.postCommitFail&&get<std::uint64_t>(c.manager,0x18)>0);}
static Presence presence(void*p,const char*n){auto&c=*(Context*)p;
    if(!std::strcmp(n,TargetName))return c.test=="target_missing"?Presence::Absent:Presence::Present;
    if(c.test=="native_unknown")return Presence::Unknown;
    return (c.nativeOccupied||c.test=="native_occupied")?Presence::Present:Presence::Absent;
}
static bool slotName(void*,unsigned slot,char out[16]){sprintf_s(out,16,"svdexCC%02u.s14",slot-60);return true;}
static bool parse(void*p,const unsigned char*src,std::size_t n,Header&out,ParseReceipt&r){auto&c=*(Context*)p;++c.parses;
    require(n==TargetSize,"parser length");out=ExpectedParsedHeader;r={src,n,294,0,0};
    if(c.test=="parser_wrong_buffer")r.source=src+1;
    if(c.test=="parser_reopens")r.nativeFileOpens=1;
    if(c.test=="parser_bad_header")out.bytes[0xe2]^=1;
    if(c.test=="parser_mutates_bytes")const_cast<unsigned char*>(src)[300]^=1;
    if(c.test=="parser_cache_drift")c.manager[0x3e0]^=1;
    return c.test!="parser_failure";
}
static bool copy(void*p,void*head,void*tail,const Header&header,OwnedNode&out){auto&c=*(Context*)p;++c.copies;
    if(c.test=="copy_foreign"){out={c.foreign,900};return true;}
    c.allocation=malloc(0x160);require(c.allocation!=nullptr,"fixture malloc");out={c.allocation,900};
    put(c.allocation,0,std::uintptr_t(head));put(c.allocation,8,std::uintptr_t(tail));std::memcpy((unsigned char*)c.allocation+16,&header,sizeof header);
    if(c.test=="copy_bad_links")put(c.allocation,8,std::uintptr_t(0));
    if(c.test=="copy_exception")throw std::runtime_error("fixture copy exception");
    if(c.test=="copy_guard_drift")c.drift=true;
    if(c.test=="copy_native_occupied")c.nativeOccupied=true;
    return c.test!="copy_failure"&&c.test!="cleanup_failure";
}
static bool owns(void*p,const OwnedNode&n){auto&c=*(Context*)p;return n.pointer==c.allocation&&n.allocation==900;}
static bool release(void*p,OwnedNode&n){auto&c=*(Context*)p;if(c.test=="cleanup_failure")return false;
    require(owns(p,n),"release foreign");free(c.allocation);c.allocation=nullptr;n={};++c.frees;return true;
}
static void initialize(Context&c){put(c.manager,8,unsigned(0));put(c.manager,0x10,std::uintptr_t(c.head));put(c.manager,0x3ec,int(-1));put(c.head,0,std::uintptr_t(c.head));put(c.head,8,std::uintptr_t(c.head));
    for(unsigned g=0;g<4;++g){put(c.manager,0x400+g*16,std::uintptr_t(c.groups[g]));put(c.groups[g],0,std::uintptr_t(c.groups[g]));put(c.groups[g],8,std::uintptr_t(c.groups[g]));}
    if(c.test=="mode1")put(c.manager,8,unsigned(1));
    if(c.test=="pending")put(c.manager,0x3ec,int(34));
    if(c.test=="secondary")put(c.manager,0x3f0,int(1));
    if(c.test=="table_foreign")put(c.manager,0x20,std::uintptr_t(c.foreign+16));
    if(c.test=="slot_occupied")put(c.manager,0x20+63*8,std::uintptr_t(c.foreign+16));
    if(c.test=="list_corrupt")put(c.head,8,std::uintptr_t(c.foreign));
    if(c.test=="list_over_bound")put(c.manager,0x18,std::uint64_t(120));
    if(c.test=="existing_unindexed"||c.test=="existing_indexed"){
        put(c.manager,0x18,std::uint64_t(1));put(c.head,0,std::uintptr_t(c.old));put(c.head,8,std::uintptr_t(c.old));
        put(c.old,0,std::uintptr_t(c.head));put(c.old,8,std::uintptr_t(c.head));put(c.old,0x150,std::uint64_t(15));
        if(c.test=="existing_indexed")put(c.manager,0x20,std::uintptr_t(c.old+16));
    }
    if(c.test=="group0"||c.test=="group2"||c.test=="cross_owned"||c.test=="group_drift"||c.test=="table_alias"||c.test=="head_is_node"){
        unsigned g=c.test=="group2"?2:0;put(c.manager,0x408+g*16,std::uint64_t(1));put(c.groups[g],0,std::uintptr_t(c.old));put(c.groups[g],8,std::uintptr_t(c.old));
        put(c.old,0,std::uintptr_t(c.groups[g]));put(c.old,8,std::uintptr_t(c.groups[g]));put(c.old,0x150,std::uint64_t(15));put(c.manager,0x20+(g==2?60:0)*8,std::uintptr_t(c.old+16));
        if(c.test=="cross_owned"){put(c.manager,0x410,std::uintptr_t(c.groups[g]));put(c.manager,0x418,std::uint64_t(1));}
        if(c.test=="table_alias")put(c.manager,0x28,std::uintptr_t(c.old+16));
        if(c.test=="head_is_node")put(c.manager,0x410,std::uintptr_t(c.old));
    }
    if(c.test=="real_shape_50_unindexed"){
        put(c.manager,0x408,std::uint64_t(50));put(c.groups[0],0,std::uintptr_t(c.extra[0]));put(c.groups[0],8,std::uintptr_t(c.extra[49]));
        for(unsigned i=0;i<50;++i){put(c.extra[i],0,std::uintptr_t(i==49?c.groups[0]:c.extra[i+1]));put(c.extra[i],8,std::uintptr_t(i?c.extra[i-1]:c.groups[0]));
            sprintf_s((char*)c.extra[i]+0x138,16,"svdexSC%02u.s14",i);put(c.extra[i],0x148,std::uint64_t(13));put(c.extra[i],0x150,std::uint64_t(15));}
    }
    if(c.test=="all_groups"){
        for(unsigned g=0;g<4;++g){put(c.manager,0x408+g*16,std::uint64_t(1));put(c.groups[g],0,std::uintptr_t(c.extra[g]));put(c.groups[g],8,std::uintptr_t(c.extra[g]));
            put(c.extra[g],0,std::uintptr_t(c.groups[g]));put(c.extra[g],8,std::uintptr_t(c.groups[g]));put(c.extra[g],0x150,std::uint64_t(15));}
    }
}
static bool rejectedCase(const std::string&s){return s=="mode1"||s=="pending"||s=="secondary"||s=="slot_range"||s=="slot_occupied"||s=="local_occupied"||s=="native_occupied"||s=="native_unknown"||s=="target_missing"||s=="table_foreign"||s=="cross_owned"||s=="table_alias"||s=="list_corrupt"||s=="list_over_bound"||s.rfind("parser_",0)==0||s=="copy_bad_links"||s=="copy_failure"||s=="copy_guard_drift"||s=="copy_native_occupied"||s=="existing_intent";}
int wmain(int argc,wchar_t**argv){try{
    require(argc==3,"args");Context c;for(auto p=argv[1];*p;++p){require(*p<128,"ascii case");c.test.push_back(char(*p));}auto dir=std::filesystem::path(argv[2]);auto path=dir/L"mppush01.s14",intent=dir/L"checkpoint_target_metadata_mppush01.intent";
    std::ifstream file(path,std::ios::binary);c.bytes=std::vector<unsigned char>((std::istreambuf_iterator<char>(file)),{});require(c.bytes.size()==TargetSize,"fixture archive size");
    native_storage_read::Api storage{&c,storageExists,storageSize,storageRead,storageValid,&c};VerifiedTarget target;
    bool acquired=target.Acquire(path.c_str(),storage);
    if(c.test=="bad_native_bytes"){require(!acquired&&c.reads==1,"reject native byte divergence");puts("{\"passed\":true,\"acquire_rejected\":true}");return 0;}
    require(acquired&&target.Intact()&&c.reads==2,"full archive lease acquired");
    HANDLE writer=CreateFileW(path.c_str(),GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,nullptr,OPEN_EXISTING,0,nullptr);
    require(writer==INVALID_HANDLE_VALUE&&GetLastError()==ERROR_SHARING_VIOLATION,"lease excludes writer");
    initialize(c);Adapter adapter{&c,boundary,presence,slotName,parse,copy,owns,release};
    Config config{{c.manager,GetCurrentThreadId(),101,201,301,401},c.test=="slot109"?109u:63u,intent.c_str()};
    if(c.test=="slot_range")config.slot=62;
    if(c.test=="local_occupied")std::ofstream(dir/L"svdexCC03.s14").put('x');
    if(c.test=="existing_intent")std::ofstream(intent).put('x');
    if(c.test=="postcommit_guard_drift")c.postCommitFail=true;
#ifdef CHECKPOINT_TARGET_METADATA_FIXTURE
    bool partial=c.test.rfind("commit_fault_",0)==0;
    unsigned stopAfter=partial?unsigned(c.test.back()-'0'):0;
    if(partial){require(stopAfter<=4,"fault point");config.fixtureFailAfterStore=int(stopAfter);}
#else
    constexpr bool partial=false;
    constexpr unsigned stopAfter=0;
#endif
    Registration registration;auto report=registration.Register(config,adapter,target);
    if(partial){
        require(report.status==Status::Uncertain&&report.commitEntered&&report.registrationStores==stopAfter&&report.storeAttempt==stopAfter,"partial commit milestones");
        require(report.node==std::uintptr_t(c.allocation)&&report.allocationTicket==900&&c.allocation,"candidate identity retained");
        require(!report.privateNodeReleased&&c.frees==0&&report.nodeTransferred==(stopAfter==4),"partial commit never frees or invents ownership");
        require(get<std::uint64_t>(c.manager,0x18)==(stopAfter>=1?1:0),"count prefix store");
        require(get<std::uintptr_t>(c.head,8)==std::uintptr_t(stopAfter>=2?c.allocation:c.head),"head previous prefix store");
        require(get<std::uintptr_t>(c.head,0)==std::uintptr_t(stopAfter>=3?c.allocation:c.head),"tail next prefix store");
        require(get<std::uintptr_t>(c.manager,0x20+config.slot*8)==(stopAfter>=4?std::uintptr_t(c.allocation)+16:0),"table prefix store");
        require(report.intentDurable&&std::filesystem::exists(intent)&&!report.loadAuthorized,"durable uncertainty no load");
        require(registration.Validate(config,adapter,target).status==Status::Uncertain,"partial cannot validate to registered");
        auto initialParses=c.parses,initialCopies=c.copies;
        Registration reopened;auto restarted=reopened.Register(config,adapter,target);
        require(restarted.status==Status::Rejected&&c.parses==initialParses&&c.copies==initialCopies&&c.frees==0,"reopened partial cannot retry");
    }
    else if(rejectedCase(c.test)||c.test=="head_is_node")require(report.status==Status::Rejected,"expected rejected");
    else if(c.test=="copy_foreign"||c.test=="copy_exception"||c.test=="cleanup_failure"||c.test=="postcommit_guard_drift")require(report.status==Status::Uncertain,"expected uncertain");
    else {
        require(report.status==Status::Registered&&report.nodeTransferred&&report.registrationStores==4,"registration success");
        require(registration.Validate(config,adapter,target).status==Status::Registered,"initial revalidation");
        if(c.test=="invalidate_clear"){put(c.manager,0x18,std::uint64_t(0));put(c.manager,0x20+config.slot*8,std::uintptr_t(0));put(c.head,0,std::uintptr_t(c.head));put(c.head,8,std::uintptr_t(c.head));}
        if(c.test=="invalidate_payload")((unsigned char*)c.allocation)[0x20]^=1;
        if(c.test=="invalidate_attachment")++config.binding.attachment;
        if(c.test=="invalidate_generation")++config.binding.cacheGeneration;
        if(c.test=="invalidate_observed_epoch")++c.currentGeneration;
        if(c.test=="invalidate_adapter")adapter.slotName=nullptr;
        if(c.test=="invalidate_mode")put(c.manager,8,unsigned(1));
        if(c.test=="invalidate_native_presence")c.nativeOccupied=true;
        if(c.test=="group_drift"){c.old[0x20]^=1;require(registration.Validate(config,adapter,target).status==Status::Invalidated,"group snapshot invalidation");}
        if(c.test.rfind("invalidate_",0)==0){report=registration.Validate(config,adapter,target);require(report.status==Status::Invalidated,"invalidation");require(registration.Validate(config,adapter,target).status==Status::Invalidated,"sticky invalidation");}
        if(c.test=="restart_intent"){
            // Simulate separate registration session after target cleared, while
            // durable intent remains. It must not parse/allocate a second time.
            put(c.manager,0x18,std::uint64_t(0));put(c.manager,0x20+config.slot*8,std::uintptr_t(0));put(c.head,0,std::uintptr_t(c.head));put(c.head,8,std::uintptr_t(c.head));
            Registration restarted;auto other=restarted.Register(config,adapter,target);require(other.status==Status::Rejected&&!std::strcmp(other.reason,"intent_exists_or_unwritable")&&c.parses==1,"durable no retry");
        }
    }
    auto calls=c.parses,allocations=c.copies;require(registration.Register(config,adapter,target).status==Status::Rejected,"duplicate cannot return stale success");require(c.parses==calls&&c.copies==allocations,"same-session no retry");
    require(!report.loadAuthorized&&get<int>(c.manager,0x3ec)==(c.test=="pending"?34:-1),"never submit pending");
    require(partial||(report.registrationStores==0||report.registrationStores==4),"fixture commit shape");
    if(c.test=="copy_bad_links"||c.test=="copy_failure"||c.test=="copy_exception"||c.test=="copy_guard_drift"||c.test=="copy_native_occupied")require(c.frees==1&&report.privateNodeReleased,"private cleanup");
    if(report.nodeTransferred)require(c.frees==0,"game-owned node not freed by core");
    printf("{\"passed\":true,\"status\":%u,\"reason\":\"%s\",\"parses\":%u,\"copies\":%u,\"frees\":%u,\"native_full_reads\":%u,\"stores\":%u,\"store_attempt\":%u,\"commit_entered\":%s,\"candidate_node\":\"0x%llx\",\"allocation_ticket\":%llu,\"node_transferred\":%s,\"load_authorized\":false}\n",unsigned(report.status),report.reason,c.parses,c.copies,c.frees,c.reads,report.registrationStores,report.storeAttempt,report.commitEntered?"true":"false",std::uint64_t(report.node),report.allocationTicket,report.nodeTransferred?"true":"false");return 0;
}catch(const std::exception&e){fprintf(stderr,"FAIL %s\n",e.what());return 1;}catch(...){fputs("FAIL unknown\n",stderr);return 2;}}

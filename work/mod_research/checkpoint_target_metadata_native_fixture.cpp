#include "checkpoint_target_metadata_native.h"
#include <cstdio>
#include <cstring>
#include <fstream>
#include <filesystem>
#include <vector>
#include <stdexcept>
namespace leaf=checkpoint_target_metadata_native;
using checkpoint_target_metadata::Header;using checkpoint_target_metadata::OwnedNode;using checkpoint_target_metadata::ParseReceipt;
template<class T>T at(void*p,std::size_t off){T value;std::memcpy(&value,static_cast<unsigned char*>(p)+off,sizeof value);return value;}
template<class T>void put(void*p,std::size_t off,T value){std::memcpy(static_cast<unsigned char*>(p)+off,&value,sizeof value);}
void need(bool yes,const char*why){if(!yes)throw std::runtime_error(why);}
struct Context {std::string name;leaf::Adapter*adapter=nullptr;OwnedNode*out=nullptr;void*allocation=nullptr;unsigned frees=0;bool valid=true,privateNode=true;~Context(){if(allocation)free(allocation);}};
static Context*c=nullptr;
bool valid(void*){return c->valid;}
bool privateNode(void*,const OwnedNode&n){return c->privateNode&&n.pointer==c->allocation&&n.allocation==1;}
Header* __fastcall ctor(Header*h){if(c->name=="ctor_exception")RaiseException(0xE14A1001,0,0,nullptr);*h={};put(h->bytes,0x140,std::uint64_t(15));h->bytes[0x148]=255;return h;}
bool __fastcall parse(Header*h,void*s){
    need(at<unsigned>(s,0x20)==1&&at<unsigned>(s,0x88)==92,"borrowed read mode/version");
    need(at<std::uintptr_t>(s,0x40)==0&&at<std::uintptr_t>(s,0x58)==0&&at<std::uintptr_t>(s,0x90)==0,"borrowed stream must have no owner state");
    auto source=at<std::uintptr_t>(s,0x30)-4;need(at<std::uintptr_t>(s,0x38)==source+274880,"borrowed source length");
    if(c->name=="parser_exception")RaiseException(0xE14A1002,0,0,nullptr);
    *h=checkpoint_target_metadata::ExpectedParsedHeader;put(s,0x30,source+294);
    if(c->name=="parser_header_mismatch")h->bytes[0xe2]^=1;
    if(c->name=="parser_error")put(s,0x50,unsigned(1));
    if(c->name=="parser_cursor")put(s,0x30,source+100);
    if(c->name=="parser_owner_write")put(s,0x40,source);
    if(c->name=="parser_heap_string")put(h->bytes,0x140,std::uint64_t(64));
    if(c->name=="parser_source_write")reinterpret_cast<unsigned char*>(source)[500]^=1;
    return c->name!="parser_false";
}
Header* __fastcall copy(Header*h,const Header*source){
    auto report=c->adapter->GetReport();need(report.allocationTicket==1&&report.node==std::uintptr_t(c->allocation)&&c->out->pointer==c->allocation&&c->out->allocation==1,"ticket before native copy");
    const unsigned char zero[0x150]{};need(!std::memcmp(h,zero,sizeof zero),"private allocation padding zeroed before native copy");
    if(c->name=="copy_exception")RaiseException(0xE14A1003,0,0,nullptr);
    if(c->name=="copy_reentrant"){Header ignored{};ParseReceipt receipt{};c->adapter->ParseVerifiedBytes(nullptr,0,ignored,receipt);}
    *h=*source;if(c->name=="copy_mismatch")h->bytes[0xe2]^=1;
    if(c->name=="copy_wrong_return")return nullptr;
    return h;
}
void __fastcall destroyString(void*p){
    bool node=c->allocation&&p==static_cast<unsigned char*>(c->allocation)+0x138;
    if((node&&c->name=="release_dtor_exception")||(!node&&c->name=="parse_dtor_exception"))RaiseException(0xE14A1004,0,0,nullptr);
    need(at<std::uint64_t>(p,24)==15,"only SSO destroyed");put(p,16,std::uint64_t(0));static_cast<unsigned char*>(p)[0]=0;
}
void* __fastcall alloc(std::size_t size){need(size==0x160,"allocation ABI size");if(c->name=="allocation_null")return nullptr;
    if(c->name=="allocation_exception")RaiseException(0xE14A1005,0,0,nullptr);
    c->allocation=malloc(size);need(c->allocation!=nullptr,"fixture malloc");std::memset(c->allocation,0xA5,size);
    if(c->name=="allocation_guard_drift")c->valid=false;return c->allocation;
}
void __fastcall freeNode(void*p){need(p==c->allocation,"allocator family/identity");
    if(c->name=="release_free_exception")RaiseException(0xE14A1006,0,0,nullptr);
    free(p);c->allocation=nullptr;++c->frees;
    if(c->name=="release_free_return_unknown")RaiseException(0xE14A1007,0,0,nullptr);
}
int wmain(int argc,wchar_t**argv){try{
    need(argc==3,"args");Context context;c=&context;for(auto p=argv[1];*p;++p){need(*p<128,"ascii");c->name.push_back(char(*p));}
    std::ifstream f(std::filesystem::path(argv[2]),std::ios::binary);std::vector<unsigned char>bytes((std::istreambuf_iterator<char>(f)),{});need(bytes.size()==274880,"archive size");
    leaf::Adapter adapter;c->adapter=&adapter;leaf::Access access{c,valid,privateNode};leaf::Functions functions{ctor,parse,copy,destroyString,alloc,freeNode};
    if(c->name=="production_bind_reject_fixture_exe"){need(!adapter.BindProduction(std::uintptr_t(GetModuleHandleW(nullptr)),GetCurrentThreadId(),access),"foreign image rejected");need(adapter.GetReport().allocateCalls==0,"bind makes no native calls");puts("{\"passed\":true,\"production_bind_rejected\":true}");return 0;}
    need(adapter.BindFixture(GetCurrentThreadId(),access,functions),"fixture bind");need(!adapter.BindFixture(GetCurrentThreadId(),access,functions),"cannot rebind");
    if(c->name=="wrong_bytes")bytes[500]^=1;
    Header header{};ParseReceipt receipt{};bool parsed=adapter.ParseVerifiedBytes(bytes.data(),bytes.size(),header,receipt);
    bool parseFailure=c->name=="wrong_bytes"||c->name=="ctor_exception"||c->name.rfind("parser_",0)==0||c->name=="parse_dtor_exception";
    if(parseFailure){need(!parsed,"parser rejects");need(adapter.GetReport().allocateCalls==0&&adapter.GetReport().freeCalls==0,"failed parser does not allocate/free");}
    else {
        need(parsed&&receipt.source==bytes.data()&&receipt.length==bytes.size()&&receipt.consumed==294&&!receipt.streamError,"same buffer parser receipt");
        need(!std::memcmp(&header,&checkpoint_target_metadata::ExpectedParsedHeader,sizeof header),"fixed native header");
        std::memcpy(header.bytes+0x128,checkpoint_target_metadata::TargetName,13);put(header.bytes,0x138,std::uint64_t(12));
        unsigned char head[16]{},tail[16]{};OwnedNode node{};c->out=&node;
        if(c->name=="bad_prepared_header")header.bytes[0xe2]^=1;
        bool copied=adapter.CopyNode(head,tail,header,node);
        bool copyFailure=c->name=="bad_prepared_header"||c->name.rfind("allocation_",0)==0||c->name.rfind("copy_",0)==0;
        if(copyFailure){need(!copied,"copy rejects");need(!adapter.OwnsNode(node)&&!adapter.ReleaseNode(node)&&adapter.GetReport().freeCalls==0,"unknown copy never freed");
            if(c->allocation)need(node.pointer==c->allocation&&node.allocation==1,"allocation identity preserved");}
        else {
            need(copied&&adapter.OwnsNode(node),"private ownership");auto wrong=node;++wrong.allocation;need(!adapter.ReleaseNode(wrong),"wrong ticket cannot release");
            if(c->name=="published")c->privateNode=false;
            bool released=adapter.ReleaseNode(node);bool releaseFailure=c->name=="published"||c->name.rfind("release_",0)==0;
            need(released!=releaseFailure,"release outcome");
            if(released)need(!node.pointer&&c->frees==1&&adapter.GetReport().nodeState==leaf::NodeState::Released,"native free completed");
            auto freeCount=adapter.GetReport().freeCalls;need(!adapter.ReleaseNode(node)&&adapter.GetReport().freeCalls==freeCount,"release at most once");
        }
        auto count=adapter.GetReport().allocateCalls;OwnedNode duplicate{};need(!adapter.CopyNode(head,tail,header,duplicate)&&adapter.GetReport().allocateCalls==count,"copy no retry");
    }
    Header other{};ParseReceipt otherReceipt{};auto parserCount=adapter.GetReport().headerParserCalls;need(!adapter.ParseVerifiedBytes(bytes.data(),bytes.size(),other,otherReceipt)&&adapter.GetReport().headerParserCalls==parserCount,"parser no retry");
    const auto&r=adapter.GetReport();need(!r.nativeLoadAuthorized&&!r.metadataRegistered,"leaf only");
    printf("{\"passed\":true,\"poisoned\":%s,\"exception\":%u,\"parses\":%u,\"allocates\":%u,\"copies\":%u,\"string_dtors\":%u,\"free_calls\":%u,\"free_returned\":%u,\"node_state\":%u,\"ticket\":%llu,\"reentrant_calls\":%u,\"native_calls_are_fixture_stubs\":true}\n",r.poisoned?"true":"false",r.exceptionCode,r.headerParserCalls,r.allocateCalls,r.headerCopyCalls,r.stringDtorCalls,r.freeCalls,r.freeReturned,unsigned(r.nodeState),r.allocationTicket,r.reentrantCalls);return 0;
}catch(const std::exception&e){fprintf(stderr,"FAIL %s\n",e.what());return 1;}catch(...){fputs("FAIL unknown\n",stderr);return 2;}}

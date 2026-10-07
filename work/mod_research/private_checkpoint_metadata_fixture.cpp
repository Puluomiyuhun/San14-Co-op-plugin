#include "private_checkpoint_metadata_core.h"
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include <fstream>
#include <stdexcept>
static void need(bool b,const char* why){if(!b)throw std::runtime_error(why);}
template<class T>static void put(void* p,size_t off,T x){memcpy(static_cast<unsigned char*>(p)+off,&x,sizeof x);}
template<class T>static T get(void* p,size_t off){T x;memcpy(&x,static_cast<unsigned char*>(p)+off,sizeof x);return x;}
struct Test {std::string name;unsigned guards=0,allocated=0,freed=0,opened=0,closed=0,ctors=0,dtors=0,parsers=0;PCMHeader header{};};
static Test* t=nullptr;
static bool stable(void*){++t->guards;return t->name!="not_idle"&&!(t->name=="drift_before_node"&&t->guards>=3)&&!(t->name=="drift_before_commit"&&t->guards>=4);}
static bool exists(void*,const char* name){return !strcmp(name,"mpckpt01.s14")?t->name!="missing_native_target":t->name=="native_slot_exists";}
static const char* slotName(uint32_t slot,uint32_t a,uint32_t b){need(!a&&!b,"formatter args");static char value[16];sprintf_s(value,"svdexCC%02u.s14",slot-60);return value;}
static void* auxCtor(void* x){++t->ctors;return x;}
static void auxDtor(void*){++t->dtors;}
static void* streamCtor(void* x,int mode){need(!mode,"stream ctor mode");++t->ctors;return x;}
static void streamDtor(void*){++t->dtors;}
static bool openStream(void* s,const PCMString* name,int mode,int zero1,int zero2,int max,int last){
    need(name->size==12&&name->capacity==15&&!strcmp(name->data,"mpckpt01.s14"),"open name");
    need(mode==1&&!zero1&&!zero2&&max==0x7d000&&last==-1,"open args");
    if(t->name=="open_fails")return false;++t->opened;
    put(s,0x20,uint32_t(t->name=="wrong_stream_mode"?0:1));return true;
}
static void readStream(void*,void* dst,size_t n){need(n==4,"version bytes");put(dst,0,uint32_t(t->name=="wrong_version"?0x5B:0x5C));}
static void version(void* s,uint32_t value){put(s,0x88,value);}
static bool readHeader(PCMHeader* h,void*){
    ++t->parsers;*h=t->header;
    if(t->name=="header_magic")h->bytes[0]^=1;
    if(t->name=="header_date")h->bytes[0xE5]=21;
    if(t->name=="header_ruler")h->bytes[0x10]^=1;
    return t->name!="parse_fails";
}
static void closeStream(void*){++t->closed;}
static PCMHeader* headerCtor(PCMHeader* h){*h={};put(h->bytes,0x140,uint64_t(15));return h;}
static void assign(void* x,const char* name,size_t n){need(n==12,"assign size");auto s=static_cast<PCMString*>(x);memset(s,0,sizeof *s);memcpy(s->data,name,n);s->size=n;s->capacity=15;}
static void stringDtor(void* x){auto s=static_cast<PCMString*>(x);s->data[0]=0;s->size=0;s->capacity=15;}
static void* nodeCopy(void*,void* next,void* prev,const PCMHeader* h){
    auto node=static_cast<unsigned char*>(HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,0x160));need(node!=nullptr,"fixture heap");++t->allocated;
    put(node,0,uintptr_t(next));put(node,8,uintptr_t(prev));memcpy(node+0x10,h,0x150);
    if(t->name=="copy_filename")node[0x138]^=1;return node;
}
static void freeNode(void* node){++t->freed;HeapFree(GetProcessHeap(),0,node);}
int wmain(int argc,wchar_t** argv){
    try{
        need(argc==5,"directory case hash header required");Test test;t=&test;
        for(const wchar_t* p=argv[2];*p;++p)t->name+=char(*p);
        std::ifstream headerFile(argv[4],std::ios::binary);headerFile.read(reinterpret_cast<char*>(&t->header),sizeof t->header);need(headerFile.gcount()==sizeof t->header,"fixture header file");
        std::vector<unsigned char> manager(0x400),head(16),old(0x160);auto mp=manager.data();auto hp=head.data();
        put(mp,0x10,uintptr_t(hp));put(mp,0x3EC,int32_t(-1));put(hp,0,uintptr_t(hp));put(hp,8,uintptr_t(hp));
        PCMConfig c;c.execute=t->name!="dry";c.slot=63;c.manager=mp;
        PCMHeader expectedHeader=t->header;c.expectedParsedHeader=&expectedHeader;
        if(t->name=="header_snapshot_mismatch")expectedHeader.bytes[0x90]^=1;
        std::wstring directory=argv[1],target=directory+L"\\mpckpt01.s14",once=directory+L"\\private_checkpoint_metadata_mpckpt01_once.json";
        c.remoteDirectory=directory.c_str();c.targetPath=target.c_str();c.oncePath=once.c_str();c.expectedSize=512;
        for(unsigned i=0;i<32;++i){unsigned value=0;need(swscanf_s(argv[3]+2*i,L"%2x",&value)==1,"hash argument");c.expectedSha256[i]=static_cast<unsigned char>(value);}
        if(t->name=="wrong_slot")c.slot=34;
        if(t->name=="wrong_hash")c.expectedSha256[0]^=1;
        if(t->name=="wrong_mode")put(mp,8,uint32_t(1));
        if(t->name=="pending")put(mp,0x3EC,int32_t(12));
        if(t->name=="occupied")put(mp,0x20+c.slot*8,uintptr_t(old.data()+16));
        if(t->name=="table_foreign")put(mp,0x20+62*8,uintptr_t(old.data()+16));
        if(t->name=="list_corrupt")put(hp,8,uintptr_t(old.data()));
        if(t->name=="preexisting"||t->name=="existing_name"){
            headerCtor(reinterpret_cast<PCMHeader*>(old.data()+16));
            if(t->name=="existing_name")assign(old.data()+0x138,"mpckpt01.s14",12);
            put(old.data(),0,uintptr_t(hp));put(old.data(),8,uintptr_t(hp));put(hp,0,uintptr_t(old.data()));put(hp,8,uintptr_t(old.data()));put(mp,0x18,uint64_t(1));
            put(mp,0x20+62*8,uintptr_t(old.data()+16));
        }
        PCMNative a{t,stable,exists,slotName,auxCtor,auxDtor,streamCtor,streamDtor,openStream,readStream,version,readHeader,closeStream,headerCtor,assign,stringDtor,nodeCopy,freeNode};
        auto before=manager;auto result=preparePrivateCheckpointMetadata(c,a);
        bool success=t->name=="execute"||t->name=="preexisting"||t->name=="duplicate";
        if(success){
            need(result.status==PCMStatus::Registered&&result.nodeGameOwned&&result.registrationStores==4,"register succeeds");
            need(get<uintptr_t>(mp,0x20+c.slot*8)==result.node+16&&get<int32_t>(mp,0x3EC)==-1,"target prebound without load");
            need(t->allocated==1&&!t->freed&&t->opened==1&&t->closed==1&&t->ctors==t->dtors,"successful ownership");
            if(t->name=="duplicate"){
                auto again=preparePrivateCheckpointMetadata(c,a);need(again.status==PCMStatus::Rejected&&!strcmp(again.reason,"slot_occupied")&&t->allocated==1,"duplicate rejected");
            }
            // The fixture is now the game owner; release its node after checking.
            freeNode(reinterpret_cast<void*>(result.node));
        }else if(t->name=="dry")need(result.status==PCMStatus::Dry&&!result.intentCreated&&manager==before&&t->allocated==0,"dry no mutation");
        else{
            need(result.status==PCMStatus::Rejected&&!result.nodeGameOwned&&result.registrationStores==0,"reject before registration");
            need(manager==before&&t->allocated==t->freed&&t->opened==t->closed&&t->ctors==t->dtors,"rejection preserves manager and releases owned objects");
        }
        std::printf("{\"result\":\"PASS\",\"case\":\"%s\",\"status\":%d,\"reason\":\"%s\",\"intent_created\":%s,\"parsed_header_snapshot_matched\":%s,\"registration_stores\":%u,\"allocated\":%u,\"freed\":%u,\"pending_unchanged\":true,\"game_access\":false}\n",t->name.c_str(),int(result.status),result.reason,result.intentCreated?"true":"false",result.parsedHeaderSnapshotMatched?"true":"false",result.registrationStores,t->allocated,t->freed);return 0;
    }catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());return 1;}
}

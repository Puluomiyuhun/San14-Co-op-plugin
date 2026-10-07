#include "private_checkpoint_metadata_core.h"
#include <bcrypt.h>
#include <cstring>
#include <cwchar>
#include <cstdio>
#include <string>
#include <vector>
#include <algorithm>
#include <stdexcept>
#pragma comment(lib,"bcrypt.lib")
namespace {
constexpr const char* NAME="mpckpt01.s14";
template<class T> T at(uintptr_t p){T v{};std::memcpy(&v,reinterpret_cast<void*>(p),sizeof v);return v;}
template<class T> void put(uintptr_t p,T v){std::memcpy(reinterpret_cast<void*>(p),&v,sizeof v);}
void need(bool yes,const char* why){if(!yes)throw std::runtime_error(why);}
bool span(uintptr_t p,size_t n,bool write=false){
    if(p<0x10000||p+n<p)return false;
    for(uintptr_t end=p+n;p<end;){MEMORY_BASIC_INFORMATION m{};
        if(!VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)||m.State!=MEM_COMMIT||m.Protect&(PAGE_GUARD|PAGE_NOACCESS))return false;
        unsigned prot=m.Protect&0xff;
        if(write&&prot!=PAGE_READWRITE&&prot!=PAGE_WRITECOPY&&prot!=PAGE_EXECUTE_READWRITE&&prot!=PAGE_EXECUTE_WRITECOPY)return false;
        uintptr_t next=uintptr_t(m.BaseAddress)+m.RegionSize;if(next<=p)return false;p=next;
    }return true;
}
bool hash(HANDLE f,const unsigned char* expected){
    LARGE_INTEGER zero{};if(!SetFilePointerEx(f,zero,nullptr,FILE_BEGIN))return false;
    BCRYPT_ALG_HANDLE a=nullptr;BCRYPT_HASH_HANDLE h=nullptr;unsigned char out[32],data[65536];bool ok=false;
    if(BCryptOpenAlgorithmProvider(&a,BCRYPT_SHA256_ALGORITHM,nullptr,0)>=0&&BCryptCreateHash(a,&h,nullptr,0,nullptr,0,0)>=0){
        ok=true;DWORD n=0;for(;;){if(!ReadFile(f,data,sizeof data,&n,nullptr)){ok=false;break;}if(!n)break;if(BCryptHashData(h,data,n,0)<0){ok=false;break;}}
        if(ok)ok=BCryptFinishHash(h,out,32,0)>=0&&!memcmp(out,expected,32);
    }if(h)BCryptDestroyHash(h);if(a)BCryptCloseAlgorithmProvider(a,0);return ok;
}
struct Graph {uintptr_t head,tail;uint64_t count;std::vector<uintptr_t> nodes;};
Graph inspect(const PCMConfig& c){
    uintptr_t m=uintptr_t(c.manager);need(span(m,0x400,true),"manager_memory");
    need(at<uint32_t>(m+8)==0&&at<int32_t>(m+0x3EC)==-1,"manager_mode_or_pending");
    need(at<uintptr_t>(m+0x20+c.slot*8)==0,"slot_occupied");
    Graph g{at<uintptr_t>(m+0x10),0,at<uint64_t>(m+0x18),{}};
    need(g.count<120&&span(g.head,16,true),"invalid_list_head_or_count");g.tail=at<uintptr_t>(g.head+8);
    uintptr_t previous=g.head,node=at<uintptr_t>(g.head);
    for(uint64_t i=0;i<g.count;++i){
        need(node!=g.head&&span(node,0x160,true)&&at<uintptr_t>(node+8)==previous,"invalid_list_links");
        g.nodes.push_back(node);auto string=node+0x138;auto size=at<uint64_t>(string+16),cap=at<uint64_t>(string+24);
        need(size<=512&&size<=cap,"metadata_string_bounds");auto text=cap>=16?at<uintptr_t>(string):string;
        need(span(text,size+1)&&at<unsigned char>(text+size)==0,"metadata_string_memory");
        need(size!=12||memcmp(reinterpret_cast<void*>(text),NAME,12),"private_name_already_registered");
        previous=node;node=at<uintptr_t>(node);
    }
    need(node==g.head&&previous==g.tail,"list_tail_or_count_mismatch");
    for(unsigned i=0;i<120;++i){auto p=at<uintptr_t>(m+0x20+i*8);if(p)need(p>=16&&std::find(g.nodes.begin(),g.nodes.end(),p-16)!=g.nodes.end(),"table_not_owned_by_list");}
    return g;
}
bool same(const Graph& a,const Graph& b){return a.head==b.head&&a.tail==b.tail&&a.count==b.count&&a.nodes==b.nodes;}
}
PCMReport preparePrivateCheckpointMetadata(const PCMConfig& c,const PCMNative& a){
    PCMReport r;HANDLE pinned=INVALID_HANDLE_VALUE;void* node=nullptr;bool auxLive=false,streamLive=false,streamOpen=false,headerLive=false,commitStarted=false;
    alignas(16) unsigned char aux[0x38]{},stream[0x98]{};PCMHeader header{};
    try{
        need(c.slot>=63&&c.slot<=109,"slot_not_reserved_CC_range");
        need(c.targetPath&&c.remoteDirectory&&c.oncePath&&c.expectedSize>=294&&c.expectedSize<=0x7d000,"bad_checkpoint_config");
        need(c.expectedParsedHeader&&span(uintptr_t(c.expectedParsedHeader),sizeof(PCMHeader)),"missing_pinned_file_header_snapshot");
        const wchar_t* onceLeaf=wcsrchr(c.oncePath,L'\\');onceLeaf=onceLeaf?onceLeaf+1:c.oncePath;
        need(!wcscmp(onceLeaf,L"private_checkpoint_metadata_mpckpt01_once.json"),"wrong_once_scope");
        need(c.year==203&&c.month==8&&c.day==11,"unsupported_world_contract");
        need(a.stablePlanning&&a.fileExists&&a.slotName&&a.auxCtor&&a.auxDtor&&a.streamCtor&&a.streamDtor&&a.open&&a.read&&a.version&&a.headerRead&&a.close&&a.headerCtor&&a.stringAssign&&a.stringDtor&&a.nodeCopy&&a.heapFree,"missing_native_adapter");
        std::wstring target=c.remoteDirectory;target+=L"\\mpckpt01.s14";need(target==c.targetPath,"wrong_private_checkpoint_path");
        need(a.stablePlanning(a.context),"not_stable_planning");auto initial=inspect(c);
        pinned=CreateFileW(c.targetPath,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
        need(pinned!=INVALID_HANDLE_VALUE,"checkpoint_pin_failed");LARGE_INTEGER size{};
        need(GetFileSizeEx(pinned,&size)&&uint64_t(size.QuadPart)==c.expectedSize&&hash(pinned,c.expectedSha256),"checkpoint_hash_or_size");
        auto name=a.slotName(c.slot,0,0);++r.nativeCalls;need(name&&strlen(name)<=15&&strlen(name)>=5,"native_slot_name_invalid");
        std::wstring localSlot=c.remoteDirectory;localSlot+=L"\\";
        for(const char* p=name;*p;++p){need((*p>='a'&&*p<='z')||(*p>='A'&&*p<='Z')||(*p>='0'&&*p<='9')||*p=='.'||*p=='_',"native_slot_name_unsafe");localSlot+=wchar_t(*p);}
        need(strcmp(name,NAME)&&GetFileAttributesW(localSlot.c_str())==INVALID_FILE_ATTRIBUTES&&GetLastError()==ERROR_FILE_NOT_FOUND,"native_slot_file_exists_or_unreadable");
        need(!a.fileExists(a.context,name)&&a.fileExists(a.context,NAME),"native_storage_absence_or_target");r.nativeCalls+=2;
        need(a.stablePlanning(a.context)&&same(initial,inspect(c)),"context_changed_before_intent");
        if(!c.execute){r.status=PCMStatus::Dry;r.reason="dry_guards_passed";CloseHandle(pinned);return r;}
        HANDLE once=CreateFileW(c.oncePath,GENERIC_WRITE,FILE_SHARE_READ,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL|FILE_FLAG_WRITE_THROUGH,nullptr);
        need(once!=INVALID_HANDLE_VALUE,"once_exists_or_unwritable");r.intentCreated=true;
        char digest[65]{};for(unsigned i=0;i<32;++i)sprintf_s(digest+i*2,3,"%02x",c.expectedSha256[i]);
        char body[512];int n=sprintf_s(body,"{\"scope\":\"private-metadata-mpckpt01-v1\",\"slot\":%u,\"filename\":\"mpckpt01.s14\",\"sha256\":\"%s\",\"size\":%llu,\"outcome\":\"unknown_no_auto_retry\",\"submits_load\":false}\n",c.slot,digest,c.expectedSize);DWORD done=0;
        BOOL durable=WriteFile(once,body,DWORD(n),&done,nullptr)&&done==DWORD(n)&&FlushFileBuffers(once);CloseHandle(once);need(durable,"intent_not_durable");
        a.auxCtor(aux);auxLive=true;++r.nativeCalls;a.streamCtor(stream,0);streamLive=true;++r.nativeCalls;
        PCMString filename{};memcpy(filename.data,NAME,13);filename.size=12;filename.capacity=15;
        streamOpen=a.open(stream,&filename,1,0,0,0x7d000,-1);++r.nativeCalls;need(streamOpen,"native_stream_open_failed");
        need(at<uint32_t>(uintptr_t(stream)+0x20)==1&&stream[0x8C]==0&&at<uint32_t>(uintptr_t(stream)+0x50)==0,"unexpected_stream_mode_or_error");
        uint32_t version=0;a.read(stream,&version,4);++r.nativeCalls;need(version==0x5C,"unsupported_file_version");a.version(stream,version);++r.nativeCalls;
        a.headerCtor(&header);headerLive=true;++r.nativeCalls;bool parsed=a.headerRead(&header,stream);++r.nativeCalls;
        need(parsed&&at<uint32_t>(uintptr_t(stream)+0x50)==0,"native_header_parse_failed");
        need(!memcmp(header.bytes,"SN14SVEXVER0000",15)&&header.bytes[15]==0,"header_magic");
        need(at<uint16_t>(uintptr_t(header.bytes)+0xE2)==c.year&&header.bytes[0xE4]==c.month&&header.bytes[0xE5]==c.day,"header_date");
        need(at<uint16_t>(uintptr_t(header.bytes)+0x10)==0x5F20&&at<uint16_t>(uintptr_t(header.bytes)+0x12)==0x9C81&&at<uint16_t>(uintptr_t(header.bytes)+0x14)==0,"header_ruler_name");
        need(!memcmp(&header,c.expectedParsedHeader,sizeof header),"native_header_snapshot_mismatch");r.parsedHeaderSnapshotMatched=true;
        a.close(stream);streamOpen=false;++r.nativeCalls;a.streamDtor(stream);streamLive=false;++r.nativeCalls;a.auxDtor(aux);auxLive=false;++r.nativeCalls;
        a.stringAssign(header.bytes+0x128,NAME,12);++r.nativeCalls;
        need(a.stablePlanning(a.context)&&same(initial,inspect(c))&&hash(pinned,c.expectedSha256),"context_changed_before_node");
        node=a.nodeCopy(reinterpret_cast<void*>(uintptr_t(c.manager)+0x10),reinterpret_cast<void*>(initial.head),reinterpret_cast<void*>(initial.tail),&header);++r.nativeCalls;
        need(node&&span(uintptr_t(node),0x160,true),"node_copy_failed");
        need(at<uintptr_t>(uintptr_t(node))==initial.head&&at<uintptr_t>(uintptr_t(node)+8)==initial.tail,"node_links_incorrect");
        auto copied=reinterpret_cast<const PCMString*>(uintptr_t(node)+0x138);
        need(copied->size==12&&copied->capacity==15&&!memcmp(copied->data,NAME,13),"node_filename_copy_failed");
        a.stringDtor(header.bytes+0x128);headerLive=false;++r.nativeCalls;
        need(a.stablePlanning(a.context)&&same(initial,inspect(c))&&hash(pinned,c.expectedSha256),"context_changed_before_commit");
        // Exactly the native scanner's ownership transfer, followed by its slot
        // registration. Pending remains -1. No load is ever requested here.
        commitStarted=true;auto m=uintptr_t(c.manager),p=uintptr_t(node);
        put(m+0x18,initial.count+1);++r.registrationStores;
        put(initial.head+8,p);++r.registrationStores;
        put(initial.tail,p);++r.registrationStores;
        put(m+0x20+c.slot*8,p+0x10);++r.registrationStores;
        r.nodeGameOwned=true;r.node=p;node=nullptr;
        need(at<int32_t>(m+0x3EC)==-1&&at<uintptr_t>(initial.head+8)==p&&at<uintptr_t>(initial.tail)==p&&at<uintptr_t>(m+0x20+c.slot*8)==p+0x10,"registration_readback");
        r.status=PCMStatus::Registered;r.reason="private_metadata_registered_no_load";
    }catch(const std::exception& e){
        // Stable literals only; preserve the reason after exception destruction.
        static thread_local std::string reason;reason=e.what();r.reason=reason.c_str();r.status=commitStarted?PCMStatus::Uncertain:PCMStatus::Rejected;
    }catch(...){r.status=PCMStatus::Uncertain;r.reason="native_exception_no_retry";}
    try{
        if(node&&!commitStarted){a.stringDtor(reinterpret_cast<void*>(uintptr_t(node)+0x138));a.heapFree(node);r.nativeCalls+=2;}
        if(headerLive){a.stringDtor(header.bytes+0x128);++r.nativeCalls;}
        if(streamOpen){a.close(stream);++r.nativeCalls;}
        if(streamLive){a.streamDtor(stream);++r.nativeCalls;}
        if(auxLive){a.auxDtor(aux);++r.nativeCalls;}
    }catch(...){r.status=PCMStatus::Uncertain;r.reason="native_cleanup_exception_no_retry";}
    if(pinned!=INVALID_HANDLE_VALUE)CloseHandle(pinned);return r;
}

#include "checkpoint_target_metadata_core.h"
#include "checkpoint_target_metadata_profile.inc"
#include <algorithm>
#include <cstring>
#include <cwchar>
#include <cstdio>
#include <vector>

namespace checkpoint_target_metadata { namespace {
struct Failure {const char* reason;bool uncertain=false;};
void need(bool ok,const char* why,bool uncertain=false){if(!ok)throw Failure{why,uncertain};}
template<class T>T at(std::uintptr_t p){T v;std::memcpy(&v,reinterpret_cast<void*>(p),sizeof v);return v;}
template<class T>void put(std::uintptr_t p,T v){std::memcpy(reinterpret_cast<void*>(p),&v,sizeof v);}
bool span(std::uintptr_t p,std::size_t n,bool write=false){
    if(p<0x10000||p+n<p)return false;
    for(auto end=p+n;p<end;){MEMORY_BASIC_INFORMATION m{};
        if(!VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)||m.State!=MEM_COMMIT||(m.Protect&(PAGE_GUARD|PAGE_NOACCESS)))return false;
        unsigned mode=m.Protect&0xff;
        if(write&&mode!=PAGE_READWRITE&&mode!=PAGE_WRITECOPY&&mode!=PAGE_EXECUTE_READWRITE&&mode!=PAGE_EXECUTE_WRITECOPY)return false;
        auto next=std::uintptr_t(m.BaseAddress)+m.RegionSize;if(next<=p)return false;p=next;
    }return true;
}
bool sameInfo(const BY_HANDLE_FILE_INFORMATION&a,const BY_HANDLE_FILE_INFORMATION&b){
    return a.dwVolumeSerialNumber==b.dwVolumeSerialNumber&&a.nFileIndexHigh==b.nFileIndexHigh&&a.nFileIndexLow==b.nFileIndexLow&&
        a.nFileSizeHigh==b.nFileSizeHigh&&a.nFileSizeLow==b.nFileSizeLow&&
        a.ftLastWriteTime.dwHighDateTime==b.ftLastWriteTime.dwHighDateTime&&a.ftLastWriteTime.dwLowDateTime==b.ftLastWriteTime.dwLowDateTime;
}
bool sameBoundary(const Boundary&a,const Boundary&b){return a.manager==b.manager&&a.thread==b.thread&&a.attachment==b.attachment&&a.attempt==b.attempt&&a.cacheGeneration==b.cacheGeneration&&a.fence==b.fence;}
bool sameAdapter(const Adapter&a,const Adapter&b){return a.context==b.context&&a.boundary==b.boundary&&a.nativePresence==b.nativePresence&&a.slotName==b.slotName&&a.parseVerifiedBytes==b.parseVerifiedBytes&&a.copyNode==b.copyNode&&a.ownsNode==b.ownsNode&&a.releaseNode==b.releaseNode;}
bool overlap(std::uintptr_t a,std::size_t an,std::uintptr_t b,std::size_t bn){return a<b+bn&&b<a+an;}
void guard(const Config&c,const Adapter&a){
    const auto&b=c.binding;
    need(b.manager&&b.thread&&b.attachment&&b.attempt&&b.cacheGeneration&&b.fence,"missing_boundary_binding");
    need(GetCurrentThreadId()==b.thread,"wrong_boundary_thread");
    need(a.boundary&&a.boundary(a.context,b),"native_serial_boundary_not_proven");
}
struct Graph {std::uintptr_t head=0,tail=0;std::uint64_t count=0;std::vector<std::uintptr_t> nodes,heads;std::array<unsigned char,32> digest{};};
Graph inspect(const Config&c,bool targetAllowed=false){
    auto m=std::uintptr_t(c.binding.manager);need(span(m,0x440,true),"manager_memory");
    need(at<unsigned>(m+8)==0,"native_mode0_required");
    need(at<int>(m+0x3ec)==-1&&at<int>(m+0x3f0)==0,"pending_or_secondary_not_idle");
    if(!targetAllowed)need(!at<std::uintptr_t>(m+0x20+c.slot*8),"slot_occupied");
    Graph g;g.head=at<std::uintptr_t>(m+0x10);g.count=at<std::uint64_t>(m+0x18);
    std::vector<unsigned char> raw(reinterpret_cast<unsigned char*>(m),reinterpret_cast<unsigned char*>(m)+0x440);
    auto append=[&](std::uintptr_t p,std::size_t n){auto first=reinterpret_cast<unsigned char*>(p);raw.insert(raw.end(),first,first+n);};
    // Validate all owner heads before walking, so no later head can alias an
    // earlier data node. Nodes need not be indexed: native table clearing can
    // leave category nodes alive until that category is rescanned.
    for(unsigned owner=0;owner<5;++owner){auto offset=owner?0x400+(owner-1)*0x10:0x10;auto head=at<std::uintptr_t>(m+offset);
        need(span(head,16,true)&&std::find(g.heads.begin(),g.heads.end(),head)==g.heads.end(),"invalid_or_shared_list_head");
        need(!overlap(head,16,m,0x440),"head_aliases_manager");
        for(auto old:g.heads)need(!overlap(head,16,old,16),"overlapping_list_heads");g.heads.push_back(head);}
    for(unsigned owner=0;owner<5;++owner){auto offset=owner?0x400+(owner-1)*0x10:0x10;
        auto head=g.heads[owner],count=at<std::uint64_t>(m+offset+8);
        // Bounded supported shape, not a general native maximum proof.
        need(count<=120&&(owner||targetAllowed||count<120),"unsupported_owned_list_shape");
        auto tail=at<std::uintptr_t>(head+8);if(!owner)g.tail=tail;
        append(head,16);auto previous=head,node=at<std::uintptr_t>(head);
        for(std::uint64_t i=0;i<count;++i){
        need(std::find(g.heads.begin(),g.heads.end(),node)==g.heads.end()&&std::find(g.nodes.begin(),g.nodes.end(),node)==g.nodes.end(),"duplicate_head_or_cross_owned_node");
        need(span(node,0x160,true)&&at<std::uintptr_t>(node+8)==previous,"list_link_or_memory");
        need(!overlap(node,0x160,m,0x440),"node_aliases_manager");
        for(auto h:g.heads)need(!overlap(node,0x160,h,16),"head_overlaps_data_node");
        for(auto old:g.nodes)need(!overlap(node,0x160,old,0x160),"overlapping_data_nodes");
        g.nodes.push_back(node);append(node,0x160);
        auto s=node+0x138;auto len=at<std::uint64_t>(s+16),cap=at<std::uint64_t>(s+24);
        need(len<=512&&len<=cap,"metadata_string_bounds");auto data=cap>=16?at<std::uintptr_t>(s):s;
        need(span(data,std::size_t(len)+1)&&at<unsigned char>(data+len)==0,"metadata_string_memory");
        if(cap>=16)append(data,std::size_t(len)+1);
        if(!targetAllowed)need(len!=12||std::memcmp(reinterpret_cast<void*>(data),TargetName,12),"target_already_registered");
        previous=node;node=at<std::uintptr_t>(node);
        }
        need(node==head&&previous==tail,"list_tail_or_count");
    }
    std::vector<std::uintptr_t> indexed;
    for(unsigned i=0;i<120;++i){auto p=at<std::uintptr_t>(m+0x20+i*8);
        if(p){need(p>=16&&std::find(g.nodes.begin(),g.nodes.end(),p-16)!=g.nodes.end(),"table_owner_not_in_five_native_lists");
            need(std::find(indexed.begin(),indexed.end(),p)==indexed.end(),"duplicate_table_alias_unsupported");indexed.push_back(p);}
    }
    need(native_storage_read::Sha256(raw.data(),raw.size(),g.digest.data()),"graph_hash");return g;
}
std::wstring parent(const std::wstring&p){auto n=p.find_last_of(L'\\');need(n!=std::wstring::npos,"target_path_not_absolute");return p.substr(0,n);}
void physical(const Config&c,const Adapter&a,const VerifiedTarget&t){
    guard(c,a);char name[16]{};need(a.slotName(a.context,c.slot,name)&&name[15]==0,"slot_formatter_failed");
    char expected[16]{};sprintf_s(expected,"svdexCC%02u.s14",c.slot-60);need(!std::strcmp(name,expected),"slot_formatter_unexpected");
    auto path=parent(t.Path())+L"\\";for(const char*p=name;*p;++p)path+=wchar_t(*p);
    SetLastError(0);auto attributes=GetFileAttributesW(path.c_str());auto error=GetLastError();
    need(attributes==INVALID_FILE_ATTRIBUTES&&error==ERROR_FILE_NOT_FOUND,"local_slot_not_proven_absent");
    guard(c,a);need(a.nativePresence(a.context,name)==Presence::Absent,"native_slot_not_proven_absent");
    guard(c,a);need(a.nativePresence(a.context,TargetName)==Presence::Present,"native_target_not_present");
}
void durableIntent(const Config&c){
    need(c.intentPath&&*c.intentPath,"missing_intent_path");auto leaf=std::wcsrchr(c.intentPath,L'\\');leaf=leaf?leaf+1:c.intentPath;
    need(!std::wcscmp(leaf,L"checkpoint_target_metadata_mppush01.intent"),"wrong_new_intent_scope");
    HANDLE f=CreateFileW(c.intentPath,GENERIC_WRITE,FILE_SHARE_READ,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL|FILE_FLAG_WRITE_THROUGH,nullptr);
    need(f!=INVALID_HANDLE_VALUE,"intent_exists_or_unwritable");
    char body[1024];int n=sprintf_s(body,"{\"schema\":\"san14.checkpoint-target-metadata.intent.v1\",\"target\":\"mppush01.s14\",\"size\":274880,\"sha256\":\"88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c\",\"slot\":%u,\"attachment\":%llu,\"attempt\":%llu,\"cache_generation\":%llu,\"fence\":%llu,\"manager\":%llu,\"outcome\":\"unknown_no_auto_retry\",\"load_authorized\":false}\n",c.slot,c.binding.attachment,c.binding.attempt,c.binding.cacheGeneration,c.binding.fence,std::uint64_t(c.binding.manager));
    DWORD written=0;bool ok=n>0&&WriteFile(f,body,DWORD(n),&written,nullptr)&&written==DWORD(n)&&FlushFileBuffers(f);bool closed=CloseHandle(f)!=0;
    need(ok&&closed,"intent_not_durable",true);
}
bool nonalias(const OwnedNode&n,const Config&c,const Graph&g){auto p=std::uintptr_t(n.pointer);
    if(!p||!n.allocation||!span(p,0x160,true)||overlap(p,0x160,std::uintptr_t(c.binding.manager),0x440))return false;
    for(auto h:g.heads)if(overlap(p,0x160,h,16))return false;
    for(auto old:g.nodes)if(overlap(p,0x160,old,0x160))return false;return true;
}
#ifdef CHECKPOINT_TARGET_METADATA_FIXTURE
void fixtureCommitFault(const Config&c,const Report&r){
    if(c.fixtureFailAfterStore==int(r.registrationStores))
        RaiseException(0xE14C0000u+r.registrationStores,0,0,nullptr);
}
#endif
} // anonymous

bool VerifiedTarget::Acquire(const wchar_t*path,const native_storage_read::Api&a) noexcept {
    if(attempted_)return false;attempted_=true;
    try{if(!path)return false;wchar_t full[32768];DWORD n=GetFullPathNameW(path,32768,full,nullptr);if(!n||n>=32768)return false;path_=full;
        native_storage_read::Input in{path_.c_str(),TargetName,TargetSize,{}};std::memcpy(in.expectedSha256,TargetSha256,32);
        if(!native_storage_read::Verify(in,a,lease_,evidence_))return false;
        verified_=GetFileInformationByHandle(lease_.file,&identity_)!=0;return verified_&&Intact();
    }catch(...){return false;}
}
bool VerifiedTarget::Intact() const noexcept {
    try{if(!verified_||!evidence_.matched||lease_.file==INVALID_HANDLE_VALUE||lease_.bytes.size()!=TargetSize)return false;
        BY_HANDLE_FILE_INFORMATION current{};unsigned char hash[32];
        return GetFileInformationByHandle(lease_.file,&current)&&sameInfo(identity_,current)&&native_storage_read::Sha256(lease_.bytes.data(),lease_.bytes.size(),hash)&&!std::memcmp(hash,TargetSha256,32);
    }catch(...){return false;}
}
Report Registration::Register(const Config&c,const Adapter&a,VerifiedTarget&t) noexcept {
    if(attempted_){auto duplicate=report_;duplicate.status=Status::Rejected;duplicate.reason="registration_attempt_already_used";return duplicate;}attempted_=true;
    OwnedNode allocation{};bool commitStarted=false,knownPrivate=false;Graph initial{};
    try{
        need(c.slot>=63&&c.slot<=109,"slot_outside_reserved_positive_CC_range");
        need(a.boundary&&a.nativePresence&&a.slotName&&a.parseVerifiedBytes&&a.copyNode&&a.ownsNode&&a.releaseNode,"missing_adapter");
        need(t.Intact(),"verified_full_native_bytes_lease_required");report_.leaseHeld=true;guard(c,a);initial=inspect(c);physical(c,a,t);
        guard(c,a);need(initial.digest==inspect(c).digest,"cache_drift_before_intent");durableIntent(c);report_.intentDurable=true;
        guard(c,a);need(t.Intact()&&initial.digest==inspect(c).digest,"cache_or_file_drift_before_parser");
        Header header{};ParseReceipt parsed{};++report_.parserCalls;
        need(a.parseVerifiedBytes(a.context,t.Bytes(),t.Size(),header,parsed),"buffer_parser_failed");
        need(parsed.source==t.Bytes()&&parsed.length==t.Size()&&parsed.consumed==294&&!parsed.nativeFileOpens&&!parsed.streamError,"parser_not_bound_to_verified_buffer");
        need(!std::memcmp(&header,&ExpectedParsedHeader,sizeof header),"fixed_target_header_mismatch");report_.headerMatched=true;
        need(t.Intact(),"leased_bytes_changed_by_parser");
        std::memcpy(header.bytes+0x128,TargetName,13);put(std::uintptr_t(header.bytes)+0x138,std::uint64_t(12));put(std::uintptr_t(header.bytes)+0x140,std::uint64_t(15));
        guard(c,a);need(initial.digest==inspect(c).digest,"cache_drift_before_allocation");++report_.allocationCalls;
        bool made=a.copyNode(a.context,reinterpret_cast<void*>(initial.head),reinterpret_cast<void*>(initial.tail),header,allocation);
        knownPrivate=nonalias(allocation,c,initial)&&a.ownsNode(a.context,allocation);
        need(knownPrivate,"allocation_ownership_unproven",true);need(made,"node_copy_failed");auto p=std::uintptr_t(allocation.pointer);
        report_.node=p;report_.allocationTicket=allocation.allocation;
        need(at<std::uintptr_t>(p)==initial.head&&at<std::uintptr_t>(p+8)==initial.tail&&!std::memcmp(reinterpret_cast<void*>(p+0x10),&header,sizeof header),"node_copy_content_or_links");
        guard(c,a);physical(c,a,t);need(t.Intact()&&initial.digest==inspect(c).digest,"cache_or_file_drift_before_commit");
        // Non-atomic four-store native ownership transfer. A real adapter MUST
        // supply a proven exclusive serial boundary; polling guards do not.
        commitStarted=true;report_.commitEntered=true;auto m=std::uintptr_t(c.binding.manager);
#ifdef CHECKPOINT_TARGET_METADATA_FIXTURE
        fixtureCommitFault(c,report_);
#endif
        report_.storeAttempt=1;put(m+0x18,initial.count+1);++report_.registrationStores;
#ifdef CHECKPOINT_TARGET_METADATA_FIXTURE
        fixtureCommitFault(c,report_);
#endif
        report_.storeAttempt=2;put(initial.head+8,p);++report_.registrationStores;
#ifdef CHECKPOINT_TARGET_METADATA_FIXTURE
        fixtureCommitFault(c,report_);
#endif
        report_.storeAttempt=3;put(initial.tail,p);++report_.registrationStores;
#ifdef CHECKPOINT_TARGET_METADATA_FIXTURE
        fixtureCommitFault(c,report_);
#endif
        report_.storeAttempt=4;put(m+0x20+c.slot*8,p+0x10);++report_.registrationStores;
        report_.nodeTransferred=true;
#ifdef CHECKPOINT_TARGET_METADATA_FIXTURE
        fixtureCommitFault(c,report_);
#endif
        allocation={};knownPrivate=false;
        guard(c,a);auto completed=inspect(c,true);
        need(completed.count==initial.count+1&&completed.tail==p&&at<std::uintptr_t>(m+0x20+c.slot*8)==p+0x10,"registration_readback",true);
        binding_=c.binding;slot_=c.slot;head_=completed.head;node_=p;graphDigest_=completed.digest;target_=&t;adapter_=a;
        report_.status=Status::Registered;report_.reason="metadata_registered_only_no_load";
    }catch(const Failure&e){report_.status=(commitStarted||e.uncertain)?Status::Uncertain:Status::Rejected;report_.reason=e.reason;}
    catch(...){report_.status=Status::Uncertain;report_.reason="adapter_or_memory_exception_no_retry";}
    if(allocation.pointer&&!commitStarted){
        try{knownPrivate=nonalias(allocation,c,initial)&&a.ownsNode&&a.ownsNode(a.context,allocation);
            if(knownPrivate&&a.releaseNode(a.context,allocation)&&!allocation.pointer)report_.privateNodeReleased=true;
            else{report_.status=Status::Uncertain;report_.reason="private_allocation_cleanup_unproven";}
        }catch(...){report_.status=Status::Uncertain;report_.reason="private_allocation_cleanup_exception";}
    }
    return report_;
}
Report Registration::Validate(const Config&c,const Adapter&a,VerifiedTarget&t) noexcept {
    if(report_.status!=Status::Registered)return report_;
    try{
        need(&t==target_&&sameBoundary(c.binding,binding_)&&c.slot==slot_&&sameAdapter(a,adapter_),"stale_registration_binding");
        guard(c,a);need(t.Intact(),"registration_lease_invalidated");auto g=inspect(c,true);
        need(g.head==head_&&g.digest==graphDigest_&&at<std::uintptr_t>(std::uintptr_t(c.binding.manager)+0x20+slot_*8)==node_+0x10,"native_metadata_invalidated");
        physical(c,a,t);guard(c,a);need(g.digest==inspect(c,true).digest,"metadata_changed_during_validation");
        report_.reason="registration_still_present_not_load_authority";
    }catch(const Failure&e){report_.status=Status::Invalidated;report_.reason=e.reason;}
    catch(...){report_.status=Status::Invalidated;report_.reason="registration_validation_exception";}
    return report_;
}
}

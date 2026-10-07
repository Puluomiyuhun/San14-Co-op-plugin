#include "human_ai_runtime_subject.h"
#include "human_economy_runtime_profile.h"
#include "human_economy_policy.h"
#include <cstring>

// This DLL is loaded in the diagnostic Python process, never in SAN14.
// All target access goes through its caller's read-only copy callback.
using ReadCallback = bool(*)(void*,std::uint64_t,void*,std::size_t) noexcept;
extern "C" __declspec(dllexport) unsigned HumanRulesProbeVersion() noexcept {return 1;}
extern "C" __declspec(dllexport) bool HumanRulesProbeProfile(ReadCallback read,void* context,std::uint64_t image) noexcept {
    san14_ai_runtime::Reader r{context,read};
    if(!read||!san14_ai_runtime::ValidateOuterEntries(r,image))return false;
    unsigned char raw[128]{};
    for(const auto& anchor:san14_economy_runtime::NativeAnchors){
        if(anchor.size>sizeof raw||!read(context,image+anchor.rva,raw,anchor.size)||std::memcmp(raw,anchor.bytes,anchor.size))return false;
    }
    for(const auto& site:san14_economy_runtime::Callsites)
        if(!read(context,image+site.call_rva,raw,5)||std::memcmp(raw,site.original,5))return false;
    return true;
}
extern "C" __declspec(dllexport) bool HumanRulesProbeSubject(ReadCallback read,void* context,
    std::uint64_t image,std::uint64_t root,std::uint64_t mask,std::uint64_t object,unsigned route,
    std::uint64_t* output,std::size_t count) noexcept {
    if(!read||!output||count!=65||route>3)return false;
    std::memset(output,0,count*sizeof(*output));
    const auto s=san14_ai_runtime::ResolveSubject({context,read},
        {image,root,object,mask,static_cast<san14_ai_runtime::Route>(route)});
    output[0]=static_cast<unsigned>(s.fault);output[1]=static_cast<unsigned>(s.group_fault);
    output[2]=static_cast<unsigned>(s.decision);output[3]=s.identity.force;output[4]=s.identity.district;
    output[5]=s.identity.identity_verified;output[6]=s.viewer;output[7]=s.option;
    output[8]=s.repeated_reads_equal;output[9]=s.distinct_reads;
    for(unsigned f=0;f<52;++f)output[10+f]=s.humans.main_district[f];
    // Expose group membership for bounded selection of active groups, without
    // treating an empty/unresolved group as a native AI dispatch.
    if(route==3&&s.fault==san14_ai_runtime::Fault::None){
        const auto group=san14_group_resolver::Resolve({context,read},{image,root,object,s.humans});
        output[62]=static_cast<unsigned>(group.error);output[63]=group.members;output[64]=group.first_army_id;
    }
    return true;
}

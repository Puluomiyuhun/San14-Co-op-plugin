#include "a_save_runtime_publish_evidence.h"
static bool cacheSawLease=false;static unsigned cacheChecks=0;
static void verifyPublishCache(dh::Host&host){
 dh::Report h{};need(host.Snapshot(h),"actual host-thread snapshot");
 a_save_runtime_wire::Counter c[7]{};std::uint32_t valid=0,lease=0,frame=0,state=0;std::uint64_t sequence=0;
 need(ASaveRuntimePublishEvidence(c,&valid,&lease,&frame,&state,&sequence),"quiet real bridge counters and FINALLY cache");
 need(valid&&sequence&&!(sequence&1)&&lease==unsigned(h.lease)&&frame==unsigned(h.frame)&&state==unsigned(h.state),"FINALLY cache matches actual Host state");
 a_save_runtime_wire::HostCache direct{};const auto address=ASaveRuntimePublishHostCacheAddress();need(address!=0,"actual cache address");memcpy(&direct,reinterpret_cast<void*>(address),sizeof direct);
 need(direct.sequence==sequence&&direct.valid==valid&&direct.lease==lease&&direct.frame==frame&&direct.state==state,"external cache wire layout matches real object");
 for(const auto&v:c)need(v.startedAddress&&v.activeAddress&&!v.active&&*reinterpret_cast<const volatile std::uint64_t*>(v.startedAddress)==v.started&&!*reinterpret_cast<const volatile std::uint64_t*>(v.activeAddress),"actual seven bridge bank addresses");
 if(lease)cacheSawLease=true;++cacheChecks;
}

#include "checkpoint_fresh_save_packet.h"
#include <cstring>

namespace checkpoint_fresh_save_packet {
namespace fs=checkpoint_fresh_save;
namespace {
void number(std::vector<unsigned char>&v,std::uint64_t n,unsigned width){
 for(unsigned i=0;i<width;++i){v.push_back(static_cast<unsigned char>(n&255));n>>=8;}
}
bool requestOK(const fs::Request&q)noexcept{
 unsigned any=0;for(auto c:q.room_id)any|=c;
 if(!q.generation||!q.room_epoch||!q.period||!any||!q.year||q.year>9999||
    q.month<1||q.month>12||(q.day!=1&&q.day!=11&&q.day!=21)||
    q.force<1||q.force>51||q.ruler>=1000||q.reserved)return false;
 if(q.filename[0]!='m'||q.filename[1]!='p'||std::memcmp(q.filename+10,".s14\0\0",6))return false;
 for(unsigned i=2;i<10;++i)if(!((q.filename[i]>='0'&&q.filename[i]<='9')||
                             (q.filename[i]>='a'&&q.filename[i]<='f')))return false;
 return true;
}
bool reportOK(const fs::Report&r,const fs::Request&q)noexcept{
 return r.status==fs::Status::Complete&&!r.error&&r.generation==q.generation&&
  !r.active&&!r.abnormal&&r.entries>=7&&r.entries==r.exits&&
  r.original_returned>=7&&r.original_returned<=r.entries&&r.first_call&&r.last_call>r.first_call&&r.save_state&&
  r.intents==1&&r.flushed==1&&r.binds==1&&r.queues==1&&r.phase_mask==31&&
  r.worker_started==1&&r.worker_joined==1&&r.native_success==1&&r.finalizer_returned==1&&
  r.return_matched==1&&r.stop_after_commit<=1&&r.executor_thread&&
  r.completed_requests>=1&&r.completed_requests<=2&&
  !r.full_world&&!r.room_ready&&r.file_bytes_verified;
}
}
Error Encode(const fs::Artifact&a,std::vector<unsigned char>&out)noexcept{
 out.clear();
 if(!requestOK(a.request))return Error::Request;
 if(!reportOK(a.report,a.request))return Error::Report;
 unsigned char hash[32]{};
 if(a.bytes.empty()||a.bytes.size()>MaxBytes||
    !native_storage_read::Sha256(a.bytes.data(),a.bytes.size(),hash)||
    std::memcmp(hash,a.sha256,32))return Error::Bytes;
 try {
  std::vector<unsigned char>v;v.reserve(HeaderBytes+a.bytes.size());
  const unsigned char magic[8]={'S','1','4','F','S','V','0','1'};
  v.insert(v.end(),magic,magic+8);number(v,1,4);number(v,HeaderBytes,4);number(v,a.bytes.size(),8);
  const auto&q=a.request;const auto&r=a.report;
  for(auto n:{q.generation,q.room_epoch,q.period,q.cut})number(v,n,8);
  v.insert(v.end(),q.room_id,q.room_id+32);
  number(v,q.year,2);number(v,q.ruler,2);
  for(auto n:{q.month,q.day,q.force,q.reserved})number(v,n,1);
  v.insert(v.end(),q.filename,q.filename+16);
  number(v,static_cast<unsigned>(r.status),4);number(v,r.error,4);
  for(auto n:{r.generation,r.active,r.entries,r.exits,r.abnormal,r.first_call,r.last_call,r.save_state})number(v,n,8);
  for(auto n:{r.intents,r.flushed,r.binds,r.queues,r.phase_mask,r.worker_started,r.worker_joined,
       r.native_success,r.finalizer_returned,r.return_matched,r.original_returned,r.stop_after_commit,
       static_cast<unsigned>(r.executor_thread),r.completed_requests})number(v,n,4);
  number(v,r.full_world?1:0,4);number(v,r.room_ready?1:0,4);number(v,r.file_bytes_verified?1:0,4);
  v.insert(v.end(),hash,hash+32);
  if(v.size()!=HeaderBytes)return Error::Bytes;
  v.insert(v.end(),a.bytes.begin(),a.bytes.end());out.swap(v);return Error::None;
 }catch(...){out.clear();return Error::Allocation;}
}
}

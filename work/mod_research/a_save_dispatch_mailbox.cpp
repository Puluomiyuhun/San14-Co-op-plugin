#include "a_save_dispatch_mailbox.h"
#include <cstring>
#include <utility>
namespace a_save_dispatch_mailbox {
namespace {
struct Guard {SRWLOCK&l;explicit Guard(SRWLOCK&v):l(v){AcquireSRWLockExclusive(&l);}~Guard(){ReleaseSRWLockExclusive(&l);}};
bool same(const fs::Request&a,const fs::Request&b)noexcept {
 return a.generation==b.generation&&a.room_epoch==b.room_epoch&&a.period==b.period&&a.cut==b.cut&&
 !memcmp(a.room_id,b.room_id,32)&&a.year==b.year&&a.ruler==b.ruler&&a.month==b.month&&
 a.day==b.day&&a.force==b.force&&a.reserved==b.reserved&&!memcmp(a.filename,b.filename,16);
}
bool nonzero(const unsigned char*p)noexcept {unsigned n=0;for(unsigned i=0;i<32;++i)n|=p[i];return n!=0;}
bool valid(const fs::Request&q)noexcept {
 if(!q.generation||!q.room_epoch||!nonzero(q.room_id)||q.reserved||q.filename[0]!='m'||q.filename[1]!='p')return false;
 for(unsigned i=2;i<10;++i)if(!((q.filename[i]>='0'&&q.filename[i]<='9')||(q.filename[i]>='a'&&q.filename[i]<='f')))return false;
 return !memcmp(q.filename+10,".s14\0\0",6);
}
}
bool Mailbox::Initialize()noexcept {Guard g(lock_);if(report_.initialized||report_.stopped)return false;report_.initialized=true;report_.host=GetCurrentThreadId();return true;}
bool Mailbox::Enqueue(const fs::Request&q,const unsigned char binding[32])noexcept {
 Guard g(lock_);if(!report_.initialized||report_.stopped||report_.count==2||!binding||!nonzero(binding)||!valid(q))return false;
 for(unsigned i=0;i<report_.count;++i){const auto&r=report_.records[i];
  if(q.generation<=r.message.request.generation||!memcmp(binding,r.message.binding,32)||
     q.room_epoch!=r.message.request.room_epoch||q.period<r.message.request.period||memcmp(q.room_id,r.message.request.room_id,32)||
     r.state!=State::Delivered)return false;
 }
 auto&r=report_.records[report_.count];r.message.ticket=report_.count+1;r.message.request=q;memcpy(r.message.binding,binding,32);r.state=State::Queued;++report_.count;return true;
}
bool Mailbox::Take(Envelope&out)noexcept {
 Guard g(lock_);if(!report_.initialized||report_.stopped||GetCurrentThreadId()!=report_.host)return false;
 for(unsigned i=0;i<report_.count;++i){auto&r=report_.records[i];if(r.state==State::Queued){r.state=State::Claimed;out=r.message;return true;}}return false;
}
bool Mailbox::Accept(const Envelope&e)noexcept {
 Guard g(lock_);const auto i=claimed(e);if(i<0||report_.records[i].state!=State::Claimed)return false;
 report_.records[i].state=State::Accepted;WakeAllConditionVariable(&changed_);return true;
}
bool Mailbox::WaitAccepted(std::uint64_t generation,DWORD timeoutMs)noexcept {
 Guard g(lock_);if(!timeoutMs||timeoutMs>60000||GetCurrentThreadId()==report_.host)return false;
 int index=-1;for(unsigned i=0;i<report_.count;++i)if(report_.records[i].message.request.generation==generation)index=int(i);
 if(index<0)return false;const auto until=GetTickCount64()+timeoutMs;
 while(!report_.stopped){const auto state=report_.records[index].state;
  if(state==State::Accepted||state==State::Complete||state==State::Delivered)return true;
  const auto now=GetTickCount64();if(now>=until)break;
  if(!SleepConditionVariableSRW(&changed_,&lock_,DWORD(until-now),0)&&GetLastError()!=ERROR_TIMEOUT)break;
 }
 stopLocked();return false;
}
int Mailbox::claimed(const Envelope&e)const noexcept {
 if(!report_.initialized||report_.stopped||GetCurrentThreadId()!=report_.host)return -1;
 for(unsigned i=0;i<report_.count;++i){const auto&r=report_.records[i];if((r.state==State::Claimed||r.state==State::Accepted)&&r.message.ticket==e.ticket&&same(r.message.request,e.request)&&!memcmp(r.message.binding,e.binding,32))return int(i);}return -1;
}
bool Mailbox::Complete(const Envelope&e,const fs::Artifact&a)noexcept {
 Guard g(lock_);const auto index=claimed(e);if(index<0||report_.records[index].state!=State::Accepted)return false;
 if(!same(e.request,a.request)||a.report.generation!=e.request.generation||a.report.status!=fs::Status::Complete||
    a.report.error||!a.report.file_bytes_verified||a.bytes.empty()||a.bytes.size()>64u*1024u*1024u||!nonzero(a.sha256)){
  stopLocked();return false;
 }
 try {fs::Artifact copy=a;artifacts_[index]=std::move(copy);}catch(...){stopLocked();return false;}
 auto&r=report_.records[index];r.state=State::Complete;r.publisher=GetCurrentThreadId();WakeAllConditionVariable(&changed_);return true;
}
bool Mailbox::Unknown(const Envelope&e)noexcept {Guard g(lock_);if(claimed(e)<0)return false;stopLocked();return true;}
bool Mailbox::Copy(std::uint64_t generation,fs::Artifact&out)noexcept {
 Guard g(lock_);if(!report_.initialized||report_.stopped)return false;
 for(unsigned i=0;i<report_.count;++i){auto&r=report_.records[i];if(r.message.request.generation!=generation||r.state!=State::Complete)continue;
  try {fs::Artifact copy=artifacts_[i];out=std::move(copy);}catch(...){return false;}
  r.state=State::Delivered;return true;
 }return false;
}
void Mailbox::stopLocked()noexcept {report_.stopped=true;for(unsigned i=0;i<report_.count;++i){auto&r=report_.records[i];if(r.state==State::Queued)r.state=State::Cancelled;else if(r.state==State::Claimed||r.state==State::Accepted)r.state=State::Unknown;}WakeAllConditionVariable(&changed_);}
void Mailbox::Stop()noexcept {Guard g(lock_);stopLocked();}
void Mailbox::Snapshot(Report&out)noexcept {Guard g(lock_);out=report_;}
bool Adapter::SubmitPort(void*p,const fs::Request&q,const unsigned char b[32])noexcept {
 if(!p)return false;auto&a=*static_cast<Adapter*>(p);if(!a.mailbox||!a.timeoutMs||a.timeoutMs>60000)return false;
 Report r{};a.mailbox->Snapshot(r);if(GetCurrentThreadId()==r.host)return false;
 return a.mailbox->Enqueue(q,b)&&a.mailbox->WaitAccepted(q.generation,a.timeoutMs);
}
bool Adapter::CopyPort(void*p,std::uint64_t generation,fs::Artifact&a)noexcept {
 return p&&static_cast<Adapter*>(p)->mailbox&&static_cast<Adapter*>(p)->mailbox->Copy(generation,a);
}
}

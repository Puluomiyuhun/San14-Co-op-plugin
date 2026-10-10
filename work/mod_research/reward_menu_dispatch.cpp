#include "reward_menu_dispatch.h"
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
namespace reward_menu_dispatch {
bool Guard::scope()const noexcept{return report_.active&&GetCurrentThreadId()==thread_;}
bool Guard::reject(unsigned e)noexcept{if(!report_.error)report_.error=e;report_.rejected=true;return false;}
bool Guard::Enter(uint64_t b,uint64_t m,reward_menu_lifecycle::Owner&l)noexcept{
 if(report_.entered||!b||m!=b+0x19E7310||l.Snapshot().phase!=reward_menu_lifecycle::Phase::Queued)return reject(1);
 base_=b;manager_=m;thread_=GetCurrentThreadId();life_=&l;report_.entered=1;report_.active=true;return true;
}
bool Guard::Select(uint64_t m,uint64_t menu,uint64_t request,uint64_t end)noexcept{
 if(!scope()||report_.rejected||m!=manager_||copied_||!request||end<request)return reject(2);
 copied_=request;++report_.selected;return life_->BeforeConsume(m,menu,request,end)||reject(3);
}
bool Guard::Finalized(uint64_t m,uint64_t menu)noexcept{return scope()&&!report_.rejected&&m==manager_&&life_->AfterFinalize(m,menu)||reject(4);}
bool Guard::Freed(uint64_t m,uint64_t menu)noexcept{return scope()&&!report_.rejected&&m==manager_&&life_->AfterAllocator(m,menu)||reject(5);}
bool Guard::CopiedStorageReleased(uint64_t storage)noexcept{
 if(!scope()||!copied_||storage!=copied_||report_.storageReleased)return reject(6);
 ++report_.storageReleased;return true;
}
bool Guard::AfterCleanup()noexcept{
 if(!scope()||!copied_||report_.storageReleased!=1||report_.boundaries)return reject(7);
 ++report_.boundaries;return !report_.rejected;
}
bool Guard::Returned()noexcept{
 if(!scope()||report_.boundaries!=1||report_.storageReleased!=1)return reject(8);
 ++report_.returned;report_.active=false;
 if(!report_.rejected&&life_->Snapshot().phase!=reward_menu_lifecycle::Phase::Closed)return reject(9);
 return !report_.rejected;
}
}

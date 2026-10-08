#include "a_save_dispatch_mailbox.h"
#include "a_save_held_ipc.h"
#include <atomic>
#include <cstdio>
#include <cstring>
#include <thread>
#include <type_traits>
#include <vector>
namespace m=a_save_dispatch_mailbox;
static_assert(std::is_same_v<decltype(a_save_held_ipc::Config::submit),decltype(&m::Adapter::SubmitPort)>);
static_assert(std::is_same_v<decltype(a_save_held_ipc::Config::copy),decltype(&m::Adapter::CopyPort)>);
static void check(bool ok,const char*why){if(!ok){printf("FAIL %s\n",why);fflush(stdout);ExitProcess(3);}}
static m::fs::Request request(unsigned generation=1){m::fs::Request q{};q.generation=generation;q.room_epoch=9;q.period=generation;q.cut=13;q.room_id[0]=1;q.year=203;q.month=8;q.day=static_cast<unsigned char>(generation==1?11:21);q.force=3;q.ruler=44;memcpy(q.filename,"mp0123abcd.s14",14);return q;}
static m::fs::Artifact artifact(const m::Envelope&e){m::fs::Artifact a{};a.request=e.request;a.report.generation=e.request.generation;a.report.status=m::fs::Status::Complete;a.report.file_bytes_verified=true;a.sha256[0]=7;a.bytes={1,2,3};return a;}
static m::Report snapshot(m::Mailbox&b){m::Report r{};b.Snapshot(r);return r;}
static void queued(m::Mailbox&b){auto until=GetTickCount64()+5000;while(!snapshot(b).count&&GetTickCount64()<until)Sleep(1);check(snapshot(b).count==1,"producer actually enqueued");}
static void twoGenerations(){m::Mailbox box;check(box.Initialize(),"host init");m::Adapter port{&box,5000};a_save_held_ipc::Config transport{};transport.executionContext=&port;transport.submit=m::Adapter::SubmitPort;transport.copy=m::Adapter::CopyPort;
 for(unsigned i=1;i<=2;++i){auto q=request(i);unsigned char binding[32]{};binding[0]=static_cast<unsigned char>(i);std::atomic<bool>returned=false;bool accepted=false;
  std::thread pipe([&]{accepted=transport.submit(transport.executionContext,q,binding);returned=true;});
  auto until=GetTickCount64()+5000;while(snapshot(box).count!=i&&GetTickCount64()<until)Sleep(1);check(snapshot(box).count==i,"next request posted");
  check(!returned,"queued is not submit success");m::Envelope e{};check(box.Take(e),"host claims copied request");check(!returned,"claimed is not submit success");
  m::Envelope duplicate{};check(!box.Take(duplicate),"claim is one-shot");bool wrongTake=true,wrongAccept=true,wrongComplete=true,wrongUnknown=true;
  auto a=artifact(e);std::thread wrongThread([&]{wrongTake=box.Take(duplicate);wrongAccept=box.Accept(e);wrongComplete=box.Complete(e,a);wrongUnknown=box.Unknown(e);});wrongThread.join();
  check(!wrongTake&&!wrongAccept&&!wrongComplete&&!wrongUnknown,"wrong thread cannot invoke host state transitions");
  auto stale=e;stale.ticket+=10;check(!box.Accept(stale),"wrong ticket rejected");stale=e;stale.binding[3]^=1;check(!box.Accept(stale),"wrong binding rejected");
  check(!box.Complete(e,a),"completion cannot precede accepted host operation");check(box.Accept(e),"named host submit double accepted");pipe.join();check(accepted&&returned,"bounded port success after host acceptance");
  q.year=999;binding[0]=99;check(e.request.year==203&&e.binding[0]==i,"input copied");
  check(box.Complete(e,a),"host copies artifact");a.bytes[0]=99;a.request.year=999;check(!box.Complete(e,a),"completion one-shot");
  if(i==1){unsigned char next[32]{2};check(!box.Enqueue(request(2),next),"next request waits for artifact delivery");}
  m::fs::Artifact copied;bool got=false;std::thread read([&]{got=transport.copy(transport.executionContext,i,copied);});read.join();check(got&&copied.bytes[0]==1&&copied.request.year==203,"artifact deep copy to pipe");
  copied.bytes[1]=99;m::fs::Artifact twice;check(!box.Copy(i,twice),"copy delivery is one-shot");
  if(i==1){unsigned char next[32]{2},old[32]{1};auto wrong=request(2);wrong.room_epoch--;check(!box.Enqueue(wrong,next),"native room epoch cannot regress");wrong=request(2);wrong.period=0;check(!box.Enqueue(wrong,next),"period cannot regress");wrong=request(2);wrong.room_id[1]=1;check(!box.Enqueue(wrong,next),"room identity cannot migrate");check(!box.Enqueue(request(1),next)&&!box.Enqueue(request(2),old),"generation and binding cannot replay");}
 }
 auto q=request(3);unsigned char b[32]{3};check(!box.Enqueue(q,b),"capacity bounded without clearing histories");check(snapshot(box).records[0].state==m::State::Delivered&&snapshot(box).records[1].state==m::State::Delivered,"both histories preserved");
}
static void concurrent(){m::Mailbox box;check(box.Initialize(),"init");auto q=request();unsigned char b[32]{1};std::atomic<unsigned>accepted=0;std::vector<std::thread>threads;
 for(unsigned i=0;i<16;++i)threads.emplace_back([&]{if(box.Enqueue(q,b))++accepted;});for(auto&t:threads)t.join();check(accepted==1,"16 producers only enqueue once");m::Envelope e;check(box.Take(e)&&box.Accept(e)&&box.Complete(e,artifact(e)),"one host operation");
 threads.clear();accepted=0;for(unsigned i=0;i<16;++i)threads.emplace_back([&]{m::fs::Artifact a;if(box.Copy(1,a))++accepted;});for(auto&t:threads)t.join();check(accepted==1,"16 consumers only deliver once");}
static void timeout(bool claimed){m::Mailbox box;check(box.Initialize(),"init");m::Adapter port{&box,200};auto q=request();unsigned char b[32]{1};bool result=true;std::thread pipe([&]{result=m::Adapter::SubmitPort(&port,q,b);});queued(box);m::Envelope e;if(claimed)check(box.Take(e),"claim before timeout");pipe.join();auto r=snapshot(box);check(!result&&r.stopped&&r.records[0].state==(claimed?m::State::Unknown:m::State::Cancelled),"timeout preserves not-started versus uncertain");check(!box.Take(e)&&!box.Enqueue(q,b)&&!box.Initialize(),"no retry or reset");if(claimed)check(!box.Accept(e)&&!box.Complete(e,artifact(e)),"late host success cannot resurrect timeout");}
static void stop(){m::Mailbox box;check(box.Initialize(),"init");m::Adapter port{&box,5000};auto q=request();unsigned char b[32]{1};bool result=true;std::thread pipe([&]{result=m::Adapter::SubmitPort(&port,q,b);});queued(box);m::Envelope e;check(box.Take(e),"claim");std::thread shutdown([&]{port.Stop();});shutdown.join();pipe.join();check(!result&&snapshot(box).records[0].state==m::State::Unknown,"stop wakes waiting pipe before join");check(!box.Accept(e),"stop cannot turn into accepted");}
static void unknown(bool malformed){m::Mailbox box;check(box.Initialize(),"init");auto q=request();unsigned char b[32]{1};check(box.Enqueue(q,b),"enqueue");m::Envelope e;check(box.Take(e),"claim");if(malformed){check(box.Accept(e),"accept");auto a=artifact(e);a.request.cut++;check(!box.Complete(e,a),"mismatched artifact stops");}else check(box.Unknown(e),"explicit uncertain host outcome");check(snapshot(box).stopped&&snapshot(box).records[0].state==m::State::Unknown,"unknown terminal");check(!box.Enqueue(request(2),b)&&!box.Take(e),"unknown never replayed");}
int main(int argc,char**argv){if(argc!=2)return 2;const char*c=argv[1];if(!strcmp(c,"two-generations"))twoGenerations();else if(!strcmp(c,"concurrent"))concurrent();else if(!strcmp(c,"queued-timeout"))timeout(false);else if(!strcmp(c,"claimed-timeout"))timeout(true);else if(!strcmp(c,"stop"))stop();else if(!strcmp(c,"unknown"))unknown(false);else if(!strcmp(c,"artifact-mismatch"))unknown(true);else return 2;printf("{\"case\":\"%s\",\"passed\":true,\"native_save\":false,\"game_access\":false}\n",c);return 0;}

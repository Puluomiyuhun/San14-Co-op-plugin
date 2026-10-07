// Reuse the frozen OWNED game-business doubles. Never call its old main;
// requests now arrive one at a time from a real local pipe after Room reserve.
#define main PreviousOwnerFixtureMain
#include "a_save_user_owner_fixture.cpp"
#undef main
#include "a_save_ipc.h"
#include <fcntl.h>
#include <io.h>
#include <thread>

#pragma pack(push,1)
struct Bootstrap {unsigned char secret[32],room_id[32];std::uint64_t epoch;unsigned char nonce[16];};
#pragma pack(pop)
static_assert(sizeof(Bootstrap)==88);
static bool admission(void*stopDuringPermit,const fs::Request&q,const unsigned char*)noexcept{
 // Controlled fixture schedule, NOT production input exclusion.
 if(stopDuringPermit)SetEvent(static_cast<HANDLE>(stopDuringPermit));
 return q.generation>=1&&q.generation<=2&&q.period==q.generation&&q.year==203&&q.month==8&&
  q.day==(q.generation==1?11:21)&&q.force==12&&q.ruler==666;
}
int main(int argc,char**argv){
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);
 if(argc!=4&&(argc!=5||strcmp(argv[4],"permit-stop")))return 2;_setmode(_fileno(stdin),_O_BINARY);mode="success";
 printf("{\"schema\":\"san14.a-save-ipc-fixture.v1\",\"event\":\"PREPARED\",\"pid\":%lu,\"birth\":\"%llu\",\"game_access\":false}\n",GetCurrentProcessId(),birth());fflush(stdout);
 Bootstrap init{};if(fread(&init,1,sizeof init,stdin)!=sizeof init)return 3;
 setup();cfg.base=b;cfg.binder=std::uintptr_t(&binder);cfg.queue=std::uintptr_t(&queue);cfg.caller=std::uintptr_t(&FreshDispatchReturn);
 cfg.room_epoch=init.epoch;memcpy(cfg.room_id,init.room_id,32);
 cfg.input_binding.attempt[0]=4;cfg.input_binding.attachment[0]=5;cfg.input_binding.owner_generation=77;cfg.sample_input=inputSample;
 MultiByteToWideChar(CP_UTF8,0,argv[1],-1,cfg.save_directory,512);wcscpy_s(cfg.intent_directory,cfg.save_directory);storageSetup(argv[2]);
 if(!session->Initialize(cfg)||!session->Arm()||failed)return 4;
 wchar_t name[180]=L"\\\\.\\pipe\\san14-a-save-";const auto prefix=wcslen(name);
 for(unsigned i=0;i<16;++i)swprintf_s(name+prefix+i*2,_countof(name)-prefix-i*2,L"%02x",init.nonce[i]);
 a_save_ipc::Config c{};c.owner=session;c.pipeName=name;c.clientPid=strtoul(argv[3],nullptr,10);
 HANDLE end=CreateEventW(nullptr,TRUE,FALSE,nullptr);if(!end)return 6;
 c.room_epoch=init.epoch;memcpy(c.room_id,init.room_id,32);memcpy(c.secret,init.secret,32);c.permit=admission;
 c.permitContext=argc==5?end:nullptr;
 a_save_ipc::Server server;if(!server.Open(c))return 5;SecureZeroMemory(&init,sizeof init);SecureZeroMemory(c.secret,32);
 std::thread service([&]{server.Run(end);});
 // All pipe name characters after its fixed prefix are hex; emit JSON escaping.
 printf("{\"schema\":\"san14.a-save-ipc-fixture.v1\",\"event\":\"READY\",\"pid\":%lu,\"birth\":\"%llu\",\"source_kind\":\"FIXTURE_ONLY\",\"capabilities\":0,\"pipe_name\":\"",GetCurrentProcessId(),birth());
 for(const wchar_t*p=name;*p;++p){if(*p==L'\\')putchar('\\');putchar(char(*p));}printf("\"}\n");fflush(stdout);
 const auto deadline=GetTickCount64()+90000;
 while(GetTickCount64()<deadline){
  a_save_ipc::Diagnostics d{};server.Inspect(d);if(d.closed)break;
  auto r=saveReport();if(r.status==fs::Status::Armed){
   // Simulate the test world's next settled date on the owned engine thread.
   // This is not an IPC command which advances or changes a real game.
   put<unsigned char>(world+0x37,r.generation==1?11:21);run();
  }
  Sleep(1);
 }
 SetEvent(end);service.join();CloseHandle(end);
 a_save_ipc::Diagnostics d{};server.Inspect(d);ss::Report r{};session->Snapshot(r);
 printf("{\"event\":\"FINAL\",\"result\":\"%s\",\"game_access\":false,\"submits\":%llu,\"copies\":%llu,\"completed\":%u,\"owner_stopped\":%u,\"ipc_closed\":%s,\"active\":%llu,\"checks_failed\":%u}\n",
  !failed&&!r.active_scopes&&d.closed?"PASS":"FAIL",d.submits,d.copies,r.save.completed_requests,r.stopped,d.closed?"true":"false",r.active_scopes,failed);fflush(stdout);
 return failed?7:0;
}

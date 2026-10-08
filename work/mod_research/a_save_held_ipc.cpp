#include "a_save_held_ipc.h"
#include <sddl.h>
#include <cstring>
#include <cwchar>
#pragma comment(lib,"advapi32.lib")

namespace a_save_held_ipc {
namespace fs=checkpoint_fresh_save;
namespace {
bool nonzero(const void*v,size_t n){const auto*p=static_cast<const unsigned char*>(v);unsigned x=0;for(size_t i=0;i<n;++i)x|=p[i];return x!=0;}
bool equal(const void*a,const void*b,size_t n){const auto*x=static_cast<const unsigned char*>(a),*y=static_cast<const unsigned char*>(b);volatile unsigned d=0;for(size_t i=0;i<n;++i)d|=x[i]^y[i];return !d;}
bool validName(const wchar_t*n,wchar_t(&out)[180]){
 constexpr wchar_t prefix[]=L"\\\\.\\pipe\\san14-a-save-";
 if(!n||wcsncmp(n,prefix,_countof(prefix)-1))return false;
 const auto size=_countof(prefix)-1;for(size_t i=0;i<32;++i)if(!((n[size+i]>=L'0'&&n[size+i]<=L'9')||(n[size+i]>=L'a'&&n[size+i]<=L'f')))return false;
 return !n[size+32]&&wcscpy_s(out,n)==0;
}
PSECURITY_DESCRIPTOR descriptor(){
 HANDLE t=nullptr;DWORD size=0;if(!OpenProcessToken(GetCurrentProcess(),TOKEN_QUERY,&t))return nullptr;
 GetTokenInformation(t,TokenUser,nullptr,0,&size);if(!size||size>65536){CloseHandle(t);return nullptr;}
 auto*data=HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,size);LPWSTR sid=nullptr;PSECURITY_DESCRIPTOR sd=nullptr;
 if(data&&GetTokenInformation(t,TokenUser,data,size,&size)&&ConvertSidToStringSidW(static_cast<TOKEN_USER*>(data)->User.Sid,&sid)){
  wchar_t text[512]{};if(swprintf_s(text,L"D:P(A;;GA;;;%s)",sid)>0)ConvertStringSecurityDescriptorToSecurityDescriptorW(text,SDDL_REVISION_1,&sd,nullptr);
 }
 if(sid)LocalFree(sid);if(data)HeapFree(GetProcessHeap(),0,data);CloseHandle(t);return sd;
}
fs::Request decode(const WireSave&w){
 fs::Request q{};q.generation=w.generation;q.room_epoch=w.room_epoch;q.period=w.period;q.cut=w.cut;
 memcpy(q.room_id,w.room_id,32);q.year=w.year;q.ruler=w.ruler;q.month=w.month;q.day=w.day;q.force=w.force;q.reserved=w.reserved;memcpy(q.filename,w.filename,16);return q;
}
}
Server::~Server(){stop();if(pipe_!=INVALID_HANDLE_VALUE)CloseHandle(pipe_);if(event_)CloseHandle(event_);if(client_)CloseHandle(client_);SecureZeroMemory(c_.secret,32);}
void Server::Inspect(Diagnostics&out)noexcept{AcquireSRWLockShared(&lock_);out=d_;ReleaseSRWLockShared(&lock_);}
void Server::stop(DWORD error)noexcept{
 if(!terminal_)terminalUntil_=GetTickCount64()+c_.idleTimeoutMs;
 terminal_=true;if(c_.owner)c_.owner->Stop();AcquireSRWLockExclusive(&lock_);d_.stopped=true;if(error)d_.osError=error;ReleaseSRWLockExclusive(&lock_);
}
Snapshot Server::snapshot()noexcept{
 a_save_user_owner::Report r{};c_.owner->Snapshot(r);
 return {unsigned(r.error),r.initialized,r.armed,r.stopped,unsigned(r.save.status),r.save.error,
  r.save.completed_requests,r.save.binds,r.save.queues,r.user_subset_held?1u:0u,r.save.generation,r.active_scopes,0};
}
bool Server::Open(const Config&c)noexcept{
 if(InterlockedCompareExchange(&opened_,1,0))return false;
 __try {
  if(!c.owner||!c.permit||!c.submit||!c.copy||!c.clientPid||!c.room_epoch||!nonzero(c.room_id,32)||!nonzero(c.secret,32)||
     c.idleTimeoutMs<100||c.idleTimeoutMs>60000||!validName(c.pipeName,name_))return false;
  c_=c;c_.pipeName=name_;const auto s=snapshot();
  if(s.owner_error||!s.initialized||!s.armed||s.stopped||s.save_status!=unsigned(fs::Status::Idle)||s.generation||s.active_scopes)return false;
  client_=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION|SYNCHRONIZE,FALSE,c.clientPid);
  if(!client_||WaitForSingleObject(client_,0)!=WAIT_TIMEOUT)return false;
  auto sd=descriptor();if(!sd)return false;SECURITY_ATTRIBUTES sa{sizeof sa,sd,FALSE};
  pipe_=CreateNamedPipeW(name_,PIPE_ACCESS_DUPLEX|FILE_FLAG_OVERLAPPED|FILE_FLAG_FIRST_PIPE_INSTANCE,
   PIPE_TYPE_BYTE|PIPE_READMODE_BYTE|PIPE_WAIT|PIPE_REJECT_REMOTE_CLIENTS,1,65536,sizeof(Request),0,&sa);
  LocalFree(sd);if(pipe_==INVALID_HANDLE_VALUE)return false;
  event_=CreateEventW(nullptr,TRUE,FALSE,nullptr);if(!event_)return false;
  AcquireSRWLockExclusive(&lock_);d_.opened=true;ReleaseSRWLockExclusive(&lock_);InterlockedExchange(&opened_,2);return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
bool Server::clientAlive()noexcept{ULONG pid=0;return GetNamedPipeClientProcessId(pipe_,&pid)&&pid==c_.clientPid&&WaitForSingleObject(client_,0)==WAIT_TIMEOUT;}
bool Server::available(HANDLE shutdown)noexcept{
 if(WaitForSingleObject(shutdown,0)==WAIT_TIMEOUT&&clientAlive())return true;
 stop(ERROR_OPERATION_ABORTED);return false;
}
bool Server::complete(OVERLAPPED&o,DWORD&n,HANDLE shutdown,ULONGLONG until)noexcept{
 const auto now=GetTickCount64();HANDLE handles[]={event_,shutdown,client_};
 auto result=WaitForMultipleObjects(3,handles,FALSE,now<until?DWORD(until-now):0);
 if(result==WAIT_OBJECT_0&&WaitForSingleObject(shutdown,0)==WAIT_TIMEOUT&&
    WaitForSingleObject(client_,0)==WAIT_TIMEOUT&&GetOverlappedResult(pipe_,&o,&n,FALSE))return true;
 DWORD error=result==WAIT_TIMEOUT?ERROR_TIMEOUT:result==WAIT_OBJECT_0+2?ERROR_PROCESS_ABORTED:ERROR_OPERATION_ABORTED;
 CancelIoEx(pipe_,&o);DWORD ignored=0;GetOverlappedResult(pipe_,&o,&ignored,TRUE);stop(error);return false;
}
bool Server::connected(HANDLE shutdown)noexcept{
 OVERLAPPED o{};ResetEvent(event_);o.hEvent=event_;DWORD n=0;
 if(ConnectNamedPipe(pipe_,&o))return true;const auto error=GetLastError();
 if(error==ERROR_PIPE_CONNECTED)return true;
 if(error==ERROR_IO_PENDING)return complete(o,n,shutdown,GetTickCount64()+c_.idleTimeoutMs);
 stop(error);return false;
}
bool Server::io(bool write,void*data,DWORD size,HANDLE shutdown)noexcept{
 auto*bytes=static_cast<unsigned char*>(data);DWORD offset=0;auto until=GetTickCount64()+c_.idleTimeoutMs;
 if(terminal_&&terminalUntil_<until)until=terminalUntil_;
 while(offset<size){
  if(WaitForSingleObject(shutdown,0)!=WAIT_TIMEOUT||!clientAlive()||GetTickCount64()>=until){stop(ERROR_OPERATION_ABORTED);return false;}
  OVERLAPPED o{};o.hEvent=event_;ResetEvent(event_);DWORD n=0;
  BOOL ok=write?WriteFile(pipe_,bytes+offset,size-offset,&n,&o):ReadFile(pipe_,bytes+offset,size-offset,&n,&o);
  if(!ok){const auto e=GetLastError();if(e!=ERROR_IO_PENDING){stop(e);return false;}if(!complete(o,n,shutdown,until))return false;}
  if(!n){stop(ERROR_BROKEN_PIPE);return false;}offset+=n;
 }return true;
}
Status Server::process(const Request&w,std::vector<unsigned char>&packet,Snapshot&s,HANDLE shutdown)noexcept{
 packet.clear();s=snapshot();
 if(!available(shutdown)){s=snapshot();return Status::Stopped;}
 if(w.magic!=Magic||w.version!=Version)return Status::BadRequest;
 if(!equal(w.secret,c_.secret,32))return Status::Unauthorized;
 if(!w.sequence||w.sequence!=sequence_+1)return Status::Sequence;
 sequence_=w.sequence;AcquireSRWLockExclusive(&lock_);++d_.requests;d_.lastSequence=sequence_;ReleaseSRWLockExclusive(&lock_);
 if(sequence_>4096)return Status::Consumed;
 const auto op=Op(w.opcode);
 if(op==Op::Snapshot||op==Op::Stop){
  if(nonzero(w.binding,32)||nonzero(&w.save,sizeof w.save))return Status::BadRequest;
  if(op==Op::Stop)stop();s=snapshot();return Status::Ok;
 }
 if(terminal_||s.stopped||s.owner_error||s.save_error)return Status::Stopped;
 if(!s.initialized||!s.armed)return Status::OperationFailed;
 if(op==Op::Submit){
  if(count_>=2)return Status::Consumed;
  if(!nonzero(w.binding,32)||w.save.room_epoch!=c_.room_epoch||!equal(w.save.room_id,c_.room_id,32))return Status::Binding;
  for(unsigned i=0;i<count_;++i)if(w.save.generation<=records_[i].request.generation||equal(w.binding,records_[i].binding,32))return Status::Consumed;
  auto q=decode(w.save);
  if(!c_.permit(c_.permitContext,q,w.binding))return Status::OperationFailed;
  // The callback may outlive the peer or a stop request. Recheck after it,
  // before consuming and dispatching the native operation.
  if(!available(shutdown)){s=snapshot();return Status::Stopped;}
  auto&record=records_[count_++];record.request=w.save;memcpy(record.binding,w.binding,32);
  // Consume before dispatch. No connection retry or sequence replay can make
  // an uncertain command become a second native Submit.
  const bool accepted=c_.submit(c_.executionContext,q,w.binding);s=snapshot();
  if(!accepted)return Status::OperationFailed;
  AcquireSRWLockExclusive(&lock_);++d_.submits;ReleaseSRWLockExclusive(&lock_);return Status::Ok;
 }
 if(op==Op::Copy){
  auto rest=w.save;rest.generation=0;if(!w.save.generation||nonzero(&rest,sizeof rest))return Status::BadRequest;
  Record*record=nullptr;for(unsigned i=0;i<count_;++i)if(records_[i].request.generation==w.save.generation)record=&records_[i];
  if(!record||!equal(w.binding,record->binding,32))return Status::Binding;
  fs::Artifact a;if(!c_.copy(c_.executionContext,w.save.generation,a)){s=snapshot();return s.stopped||s.owner_error||s.save_error?Status::Stopped:Status::NotReady;}
  const auto q=decode(record->request);
  if(a.request.generation!=q.generation||a.request.period!=q.period||a.request.room_epoch!=q.room_epoch||a.request.cut!=q.cut||
    !equal(a.request.room_id,q.room_id,32)||a.request.year!=q.year||a.request.month!=q.month||a.request.day!=q.day||
    a.request.force!=q.force||a.request.ruler!=q.ruler||a.request.reserved||!equal(a.request.filename,q.filename,16))return Status::Binding;
  if(checkpoint_fresh_save_packet::Encode(a,packet)!=checkpoint_fresh_save_packet::Error::None)return Status::OperationFailed;
  s=snapshot();if(s.stopped||s.owner_error||s.save_error){packet.clear();return Status::Stopped;}
  AcquireSRWLockExclusive(&lock_);++d_.copies;ReleaseSRWLockExclusive(&lock_);return Status::Ok;
 }
 return Status::BadRequest;
}
bool Server::Run(HANDLE shutdown)noexcept{
 if(InterlockedCompareExchange(&opened_,0,0)!=2||!shutdown||shutdown==INVALID_HANDLE_VALUE||InterlockedCompareExchange(&run_,1,0))return false;
 AcquireSRWLockExclusive(&lock_);d_.running=true;ReleaseSRWLockExclusive(&lock_);
 bool ok=false;
 try {
  if(connected(shutdown)&&clientAlive())while(true){
   Request w{};if(!io(false,&w,sizeof w,shutdown)){SecureZeroMemory(&w,sizeof w);break;}
   if(!available(shutdown)){SecureZeroMemory(&w,sizeof w);break;}
   std::vector<unsigned char>packet;Snapshot s{};const auto result=process(w,packet,s,shutdown);
   if(result!=Status::Ok&&result!=Status::NotReady){stop();s=snapshot();packet.clear();}
   Header h{Magic,Version,w.opcode,w.sequence,unsigned(result),DWORD(sizeof s+packet.size()),{}};memcpy(h.binding,w.binding,32);SecureZeroMemory(&w,sizeof w);
   if(!io(true,&h,sizeof h,shutdown)||!io(true,&s,sizeof s,shutdown)||(!packet.empty()&&!io(true,packet.data(),DWORD(packet.size()),shutdown)))break;
   // WriteFile completion only means the reply reached the pipe buffer.
   // Keep the stopped connection observable until EOF or its fixed deadline;
   // an immediate DisconnectNamedPipe would discard the unread Stop reply.
   if(terminal_)ok=true;
  }
 }catch(...){stop(ERROR_UNHANDLED_EXCEPTION);}
 stop();DisconnectNamedPipe(pipe_);AcquireSRWLockExclusive(&lock_);d_.running=false;d_.closed=true;ReleaseSRWLockExclusive(&lock_);InterlockedExchange(&run_,2);return ok;
}
}

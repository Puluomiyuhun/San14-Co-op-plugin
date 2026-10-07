#include "checkpoint_session_ipc.h"
#include <sddl.h>
#include <cstring>
#include <cwchar>
#include <limits>
#pragma comment(lib,"advapi32.lib")
namespace checkpoint_session_ipc {
#define IPC_LOCK(code) do{AcquireSRWLockExclusive(&lock_);__try{code;}__finally{ReleaseSRWLockExclusive(&lock_);}}while(0)
static bool nonzero(const unsigned char*p,size_t n){unsigned char v=0;for(size_t i=0;i<n;++i)v|=p[i];return v!=0;}
static bool equal(const unsigned char*a,const unsigned char*b,size_t n){volatile unsigned char difference=0;for(size_t i=0;i<n;++i)difference=static_cast<unsigned char>(difference|static_cast<unsigned char>(a[i]^b[i]));return difference==0;}
static bool safeName(const wchar_t*n,wchar_t*out,size_t capacity){
    constexpr wchar_t prefix[]=L"\\\\.\\pipe\\";if(!n||wcsncmp(n,prefix,9))return false;
    size_t i=0;for(;i<capacity;++i){auto c=n[i];out[i]=c;if(!c)break;if(i>=9&&!((c>=L'a'&&c<=L'z')||(c>=L'A'&&c<=L'Z')||(c>=L'0'&&c<=L'9')||c==L'-'||c==L'_'))return false;}
    return i>=25&&i<capacity;
}
static PSECURITY_DESCRIPTOR userDescriptor(){
    HANDLE token=nullptr;DWORD amount=0;if(!OpenProcessToken(GetCurrentProcess(),TOKEN_QUERY,&token))return nullptr;
    GetTokenInformation(token,TokenUser,nullptr,0,&amount);
    if(!amount||amount>65536){CloseHandle(token);return nullptr;}
    auto memory=static_cast<unsigned char*>(HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,amount));
    if(!memory){CloseHandle(token);return nullptr;}
    LPWSTR sid=nullptr;PSECURITY_DESCRIPTOR result=nullptr;
    if(GetTokenInformation(token,TokenUser,memory,amount,&amount)&&ConvertSidToStringSidW(reinterpret_cast<TOKEN_USER*>(memory)->User.Sid,&sid)){
        wchar_t sddl[512]{};
        if(swprintf_s(sddl,L"D:P(A;;GA;;;%s)",sid)>0)ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl,SDDL_REVISION_1,&result,nullptr);
    }
    if(sid)LocalFree(sid);HeapFree(GetProcessHeap(),0,memory);CloseHandle(token);return result;
}
Server::~Server(){
    // Caller joins Run before destruction. Session/hook modules outlive Server.
    if(config_.session)config_.session->Stop();
    if(pipe_!=INVALID_HANDLE_VALUE)CloseHandle(pipe_);if(ioEvent_)CloseHandle(ioEvent_);if(client_)CloseHandle(client_);
    SecureZeroMemory(config_.secret,sizeof config_.secret);
}
bool Server::Open(const Config&c) noexcept {
    if(InterlockedCompareExchange(&opened_,1,0))return false;
    __try {
        if(!c.session||!c.nativeAttempt||!c.expectedClientPid||c.idleTimeoutMs<100||c.idleTimeoutMs>60000||
           !nonzero(c.secret,32)||!nonzero(c.attempt,16)||!nonzero(c.expectedIntent,16)||!safeName(c.pipeName,pipeName_,_countof(pipeName_)))return false;
        checkpoint_guest_native_session::Report r{};c.session->Snapshot(r);
        if(!r.initialized||r.attempt!=c.nativeAttempt||r.armed||r.stopRequested||r.mayHavePublished||r.error)return false;
        config_=c;config_.pipeName=pipeName_;
        // Pin the explicitly supplied client process object. PID reuse cannot
        // pass after this object exits; no process enumeration or game lookup.
        client_=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION|SYNCHRONIZE,FALSE,c.expectedClientPid);
        if(!client_||WaitForSingleObject(client_,0)!=WAIT_TIMEOUT)return false;
        auto sd=userDescriptor();if(!sd)return false;SECURITY_ATTRIBUTES sa{sizeof sa,sd,FALSE};
        pipe_=CreateNamedPipeW(pipeName_,PIPE_ACCESS_DUPLEX|FILE_FLAG_OVERLAPPED|FILE_FLAG_FIRST_PIPE_INSTANCE,
            PIPE_TYPE_BYTE|PIPE_READMODE_BYTE|PIPE_WAIT|PIPE_REJECT_REMOTE_CLIENTS,1,sizeof(Response),sizeof(Request),0,&sa);
        const DWORD error=pipe_==INVALID_HANDLE_VALUE?GetLastError():0;LocalFree(sd);
        if(error){IPC_LOCK(diagnostics_.lastWin32Error=error);return false;}
        ioEvent_=CreateEventW(nullptr,TRUE,FALSE,nullptr);if(!ioEvent_)return false;
        IPC_LOCK(diagnostics_.opened=true);InterlockedExchange(&opened_,2);return true;
    }__except(EXCEPTION_EXECUTE_HANDLER){IPC_LOCK(diagnostics_.lastWin32Error=ERROR_INVALID_ACCESS);return false;}
}
void Server::SnapshotDiagnostics(Diagnostics&out) noexcept {AcquireSRWLockShared(&lock_);out=diagnostics_;ReleaseSRWLockShared(&lock_);}
void Server::stopForLoss(DWORD error) noexcept {
    consumed_=true;if(config_.session)config_.session->Stop();
    IPC_LOCK(diagnostics_.armConsumed=true;++diagnostics_.losses;diagnostics_.lastWin32Error=error);
}
Server::Io Server::complete(OVERLAPPED&o,DWORD&transferred,HANDLE shutdown,ULONGLONG deadline) noexcept {
    auto now=GetTickCount64();DWORD remaining=now<deadline?DWORD(deadline-now):0;HANDLE waits[]={ioEvent_,shutdown,client_};
    DWORD outcome=WaitForMultipleObjects(3,waits,FALSE,remaining);
    if(outcome==WAIT_OBJECT_0){if(GetOverlappedResult(pipe_,&o,&transferred,FALSE))return Io::Ok;IPC_LOCK(diagnostics_.lastWin32Error=GetLastError());return Io::Loss;}
    DWORD error=outcome==WAIT_TIMEOUT?ERROR_TIMEOUT:outcome==WAIT_OBJECT_0+2?ERROR_PROCESS_ABORTED:outcome==WAIT_OBJECT_0+1?ERROR_OPERATION_ABORTED:GetLastError();
    CancelIoEx(pipe_,&o);
    // Complete cancellation before stack OVERLAPPED/event can be reused. A
    // synchronous wait here is only on our own canceled named-pipe operation.
    DWORD ignored=0;GetOverlappedResult(pipe_,&o,&ignored,TRUE);
    IPC_LOCK(diagnostics_.lastWin32Error=error);return outcome==WAIT_OBJECT_0+1?Io::Shutdown:Io::Loss;
}
Server::Io Server::connect(HANDLE shutdown) noexcept {
    OVERLAPPED o{};ResetEvent(ioEvent_);o.hEvent=ioEvent_;DWORD ignored=0;
    if(ConnectNamedPipe(pipe_,&o))return Io::Ok;
    auto error=GetLastError();if(error==ERROR_PIPE_CONNECTED)return Io::Ok;
    if(error!=ERROR_IO_PENDING){IPC_LOCK(diagnostics_.lastWin32Error=error);return Io::Loss;}
    return complete(o,ignored,shutdown,GetTickCount64()+config_.idleTimeoutMs);
}
Server::Io Server::transfer(bool write,void*buffer,DWORD length,HANDLE shutdown) noexcept {
    auto bytes=static_cast<unsigned char*>(buffer);DWORD offset=0;const auto deadline=GetTickCount64()+config_.idleTimeoutMs;
    while(offset<length){
        if(WaitForSingleObject(shutdown,0)==WAIT_OBJECT_0)return Io::Shutdown;
        if(WaitForSingleObject(client_,0)!=WAIT_TIMEOUT){IPC_LOCK(diagnostics_.lastWin32Error=ERROR_PROCESS_ABORTED);return Io::Loss;}
        if(GetTickCount64()>=deadline){IPC_LOCK(diagnostics_.lastWin32Error=ERROR_TIMEOUT);return Io::Loss;}
        OVERLAPPED o{};ResetEvent(ioEvent_);o.hEvent=ioEvent_;DWORD n=0;
        BOOL ok=write?WriteFile(pipe_,bytes+offset,length-offset,&n,&o):ReadFile(pipe_,bytes+offset,length-offset,&n,&o);
        if(!ok){auto error=GetLastError();if(error!=ERROR_IO_PENDING){IPC_LOCK(diagnostics_.lastWin32Error=error);return Io::Loss;}auto result=complete(o,n,shutdown,deadline);if(result!=Io::Ok)return result;}
        if(!n){IPC_LOCK(diagnostics_.lastWin32Error=ERROR_BROKEN_PIPE);return Io::Loss;}
        offset+=n;
    }return Io::Ok;
}
bool Server::clientAllowed() noexcept {ULONG pid=0;return GetNamedPipeClientProcessId(pipe_,&pid)&&pid==config_.expectedClientPid&&WaitForSingleObject(client_,0)==WAIT_TIMEOUT;}
void Server::fill(Response&response,Status status) noexcept {
    checkpoint_guest_native_session::Report r{};config_.session->Snapshot(r);response.status=unsigned(status);
    response.state=unsigned(r.state);response.error=r.error;response.exceptionCode=r.exceptionCode;response.armed=r.armed;response.menuBound=r.menuBound;
    response.requestInFlight=r.requestInFlight;response.casPublished=r.casPublished;response.mayHavePublished=r.mayHavePublished||r.casPublished;
    response.stopRequested=r.stopRequested;response.hooksRestored=r.hooksRestored;response.bytesReady=r.bytes.observedWorkerAndBytes;
    response.lifecycleReady=r.lifecycle.receiptReady;response.identityReady=r.identity.receiptReady;
    const auto active=std::uint64_t(r.activeDispatch)+r.activeWorker+r.activeRead;response.activeCallbacks=active>MAXDWORD?MAXDWORD:DWORD(active);
    response.capabilities=0; // No supported input/full-world/planning/presentation claim.
}
void Server::process(const Request&request,Response&response) noexcept {
    response={};response.magic=Magic;response.version=Version;response.opcode=request.opcode;response.sequence=request.sequence;memcpy(response.attempt,config_.attempt,16);
    Status result=Status::Ok;
    if(request.magic!=Magic||request.version!=Version)result=Status::BadRequest;
    else if(!equal(request.secret,config_.secret,32))result=Status::Unauthorized;
    else if(!equal(request.attempt,config_.attempt,16)||!equal(request.intent,config_.expectedIntent,16))result=Status::Binding;
    else if(!request.sequence||request.sequence<=lastSequence_)result=Status::Sequence;
    else {
        lastSequence_=request.sequence;IPC_LOCK(diagnostics_.lastSequence=lastSequence_);
        if(request.opcode==unsigned(Opcode::Snapshot)){}
        else if(request.opcode==unsigned(Opcode::StopKeepObserving)){consumed_=true;config_.session->Stop();}
        else if(request.opcode==unsigned(Opcode::ArmOnce)){
            if(consumed_)result=Status::Consumed;
            else {consumed_=true;if(!config_.session->ArmHooks())result=Status::OperationFailed;}
        }else result=Status::BadRequest;
    }
    IPC_LOCK(++diagnostics_.requests;diagnostics_.armConsumed=consumed_;if(result!=Status::Ok)++diagnostics_.rejected);
    fill(response,result);
}
bool Server::Run(HANDLE shutdown) noexcept {
    if(InterlockedCompareExchange(&opened_,0,0)!=2||!shutdown||shutdown==INVALID_HANDLE_VALUE||InterlockedCompareExchange(&running_,1,0))return false;
    IPC_LOCK(diagnostics_.running=true);
    bool normal=true;
    __try {__try {
        while(WaitForSingleObject(shutdown,0)!=WAIT_OBJECT_0){
            auto state=connect(shutdown);
            if(state!=Io::Ok){DWORD error=0;IPC_LOCK(error=diagnostics_.lastWin32Error);stopForLoss(error);DisconnectNamedPipe(pipe_);if(state==Io::Shutdown)break;if(WaitForSingleObject(client_,0)!=WAIT_TIMEOUT)break;continue;}
            IPC_LOCK(++diagnostics_.connections);
            if(!clientAllowed()){stopForLoss(ERROR_ACCESS_DENIED);DisconnectNamedPipe(pipe_);continue;}
            while(true){
                Request request{};Response response{};
                state=transfer(false,&request,sizeof request,shutdown);
                if(state!=Io::Ok){SecureZeroMemory(&request,sizeof request);break;}
                process(request,response);SecureZeroMemory(&request,sizeof request);
                state=transfer(true,&response,sizeof response,shutdown);if(state!=Io::Ok)break;
            }
            DWORD error=0;IPC_LOCK(error=diagnostics_.lastWin32Error);stopForLoss(error);DisconnectNamedPipe(pipe_);if(state==Io::Shutdown)break;
            if(WaitForSingleObject(client_,0)!=WAIT_TIMEOUT)break;
        }
    }__except(EXCEPTION_EXECUTE_HANDLER){stopForLoss(ERROR_UNHANDLED_EXCEPTION);normal=false;}}
    __finally {config_.session->Stop();consumed_=true;IPC_LOCK(diagnostics_.running=false;diagnostics_.closed=true;diagnostics_.armConsumed=true);InterlockedExchange(&running_,2);}
    return normal;
}
}

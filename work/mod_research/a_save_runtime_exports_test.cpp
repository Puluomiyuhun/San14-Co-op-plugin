#include "a_save_runtime_exports.h"
#include <cstdio>
#include <cstring>
#include <cstdlib>
namespace w=a_save_runtime_wire;
using Fn=DWORD(WINAPI*)(void*);
void need(bool b,const char*m){if(!b){fprintf(stderr,"FAIL %s\n",m);exit(2);}}
template<class T>void header(T&v,w::Op op){v.header={w::Magic,w::Version,sizeof(T),unsigned(op),0};memset(v.nonce,0x37,32);}
int wmain(int argc,wchar_t**argv){need(argc==2,"DLL argument");const auto dll=LoadLibraryExW(argv[1],nullptr,LOAD_WITH_ALTERED_SEARCH_PATH);need(dll!=nullptr,"production DLL load");
 const char*names[]={"ASaveRuntimePrepare","ASaveRuntimePlans","ASaveRuntimeArmOwner","ASaveRuntimeArmPublishedSources","ASaveRuntimeSnapshot","ASaveRuntimeStop","ASaveRuntimeStartServer","ASaveRuntimeServerStatus"};Fn fn[8]{};
 for(unsigned i=0;i<8;++i){fn[i]=reinterpret_cast<Fn>(GetProcAddress(dll,names[i]));need(fn[i]!=nullptr,"export exists");need(fn[i](nullptr)==unsigned(w::Result::BadEnvelope),"null envelope rejected");}
 w::Prepare p{};header(p,w::Op::Prepare);p.header.version++;need(fn[0](&p)==unsigned(w::Result::BadEnvelope),"version reject before once");
 header(p,w::Op::Prepare);p.header.size--;need(fn[0](&p)==unsigned(w::Result::BadEnvelope),"size reject before once");
 header(p,w::Op::Snapshot);need(fn[0](&p)==unsigned(w::Result::BadEnvelope),"opcode reject before once");
 w::Snapshot s{};header(s,w::Op::Snapshot);need(fn[4](&s)==unsigned(w::Result::NotPrepared),"snapshot before Prepare");
 header(p,w::Op::Prepare);need(fn[0](&p)==unsigned(w::Result::Rejected)&&p.header.result==unsigned(w::Result::Rejected),"actual Runtime rejects missing native config");
 header(s,w::Op::Snapshot);s.restoreReady=1;s.hostCacheValid=1;need(fn[4](&s)==0&&s.error==2&&!s.prepared&&!s.ownerArmed&&!s.restoreReady&&!s.hostCacheValid,"real Config failure snapshot overwrites untrusted output");
 header(p,w::Op::Prepare);need(fn[0](&p)==unsigned(w::Result::Used),"invalid native Prepare consumes once");
 w::StartServer start{};header(start,w::Op::StartServer);start.clientPid=GetCurrentProcessId();memset(start.secret,1,32);wcscpy_s(start.pipeName,L"\\\\.\\pipe\\san14-a-save-00112233445566778899aabbccddeeff");start.idleTimeoutMs=1000;
 need(fn[6](&start)==unsigned(w::Result::NotReady),"server cannot start before actual parent");
 w::Command c{};header(c,w::Op::Stop);c.nonce[0]^=1;need(fn[5](&c)==unsigned(w::Result::NotPrepared),"nonce mismatch cannot stop");
 header(c,w::Op::Stop);need(fn[5](&c)==0,"real Stop");header(s,w::Op::Snapshot);need(fn[4](&s)==0&&s.stopped&&!s.restoreReady,"stopped not restore authority");
 w::ServerStatus st{};header(st,w::Op::ServerStatus);need(fn[7](&st)==0&&!st.started&&!st.opened,"server remained unopened");
 puts("PASS 8 real exports; envelope/nonce/once/actual Runtime Config rejection/Stop/server-notready. No native game layout, hooks, or Save executed.");return 0;
}

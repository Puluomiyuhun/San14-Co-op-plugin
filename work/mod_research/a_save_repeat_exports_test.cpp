#include "a_save_repeat_exports.h"
#include <cstdio>
#include <cstring>
#include <cstdlib>
namespace w=a_save_runtime_wire;
namespace rw=a_save_repeat_wire;
using Fn=DWORD(WINAPI*)(void*);
void need(bool b,const char*m){if(!b){fprintf(stderr,"FAIL %s\n",m);exit(2);}}
template<class T>void header(T&v,w::Op op){v.header={w::Magic,w::Version,sizeof(T),unsigned(op),0};memset(v.nonce,0x37,32);}
int wmain(int argc,wchar_t**argv){
 need(argc==2,"DLL argument");auto dll=LoadLibraryExW(argv[1],nullptr,LOAD_WITH_ALTERED_SEARCH_PATH);need(dll!=nullptr,"production DLL load");
 auto prepare=reinterpret_cast<Fn>(GetProcAddress(dll,"ASaveRuntimePrepare"));
 auto stop=reinterpret_cast<Fn>(GetProcAddress(dll,"ASaveRuntimeStop"));
 auto next=reinterpret_cast<Fn>(GetProcAddress(dll,"ASaveRuntimeRequestNext"));
 auto snapshot=reinterpret_cast<Fn>(GetProcAddress(dll,"ASaveRuntimeRepeatSnapshot"));
 need(prepare&&stop&&next&&snapshot,"old and new exports exist");
 need(next(nullptr)==unsigned(w::Result::BadEnvelope)&&snapshot(nullptr)==unsigned(w::Result::BadEnvelope),"null rejected");
 rw::Next n{};header(n,rw::NextOp);n.header.size--;need(next(&n)==unsigned(w::Result::BadEnvelope),"short rejected");
 header(n,rw::NextOp);n.header.version++;need(next(&n)==unsigned(w::Result::BadEnvelope),"version rejected");
 header(n,rw::SnapshotOp);need(next(&n)==unsigned(w::Result::BadEnvelope),"wrong op rejected");
 header(n,rw::NextOp);n.header.result=1;need(next(&n)==unsigned(w::Result::BadEnvelope),"nonrequest rejected");
 header(n,rw::NextOp);need(next(&n)==unsigned(w::Result::NotPrepared),"next before prepare rejected");
 rw::Snapshot s{};header(s,rw::SnapshotOp);need(snapshot(&s)==unsigned(w::Result::NotPrepared),"snapshot before prepare rejected");
 w::Prepare p{};header(p,w::Op::Prepare);need(prepare(&p)==unsigned(w::Result::Rejected),"actual Runtime config rejected");
 header(n,rw::NextOp);n.nonce[0]^=1;need(next(&n)==unsigned(w::Result::NotPrepared),"next foreign nonce rejected");
 header(s,rw::SnapshotOp);s.nonce[0]^=1;need(snapshot(&s)==unsigned(w::Result::NotPrepared),"snapshot foreign nonce rejected");
 header(n,rw::NextOp);n.request.previousGeneration=1;n.request.generation=2;n.request.period=1;n.request.epoch=1;
 memset(n.request.previousSha256,1,32);memset(n.request.inputDigest,2,32);n.request.day=10;
 need(next(&n)==unsigned(w::Result::Rejected),"failed Prepare cannot queue repeat");
 memset(&s,0xA5,sizeof s);header(s,rw::SnapshotOp);need(snapshot(&s)==0,"actual repeat snapshot");
 rw::NextData zero{};need(!s.state&&!s.error&&!s.requested&&!s.stopped&&s.activeGeneration==1&&!s.retiredCount&&!s.retiredSerial&&!s.hostThread,"idle state overwrites caller values");
 need(!memcmp(&s.request,&zero,sizeof zero)&&!s.previousArtifactMatched&&!s.nativeDateMatched&&!s.bLoadedProven&&!s.simulationEnabled,"no fabricated date/B/advance readiness");
 need(!s.lease&&!s.frame&&!s.drainPending,"cleanup fields overwrite caller values");
 w::Command c{};header(c,w::Op::Stop);need(stop(&c)==0,"actual stop");
 header(n,rw::NextOp);need(next(&n)==unsigned(w::Result::Stopped),"next after stop rejected");
 header(s,rw::SnapshotOp);need(snapshot(&s)==0&&s.stopped&&!s.requested&&!s.bLoadedProven&&!s.simulationEnabled,"stopped repeat status");
 puts("PASS additive operations 9/10 against production DLL; validation, nonce, actual rejected Prepare and Stop. No game, native layout, save or date advance executed.");return 0;
}

#include "checkpoint_fresh_save_packet.h"
#include <cstdio>
#include <cstring>
#include <string>

namespace fs=checkpoint_fresh_save;
namespace packet=checkpoint_fresh_save_packet;
static unsigned checks=0,failures=0;
static void check(bool b,const char*name){++checks;if(!b){++failures;std::fprintf(stderr,"FAIL %s\n",name);}}
int main(int argc,char**argv){
 if(argc!=2)return 2;
 fs::Artifact good{};auto&q=good.request;auto&r=good.report;
 q.generation=1;q.room_epoch=7;q.period=1;q.cut=9;q.room_id[0]=1;
 q.year=203;q.month=8;q.day=11;q.force=12;q.ruler=666;strcpy_s(q.filename,"mp00000001.s14");
 r.status=fs::Status::Complete;r.generation=1;r.entries=r.exits=9;r.original_returned=7;
 r.first_call=1;r.last_call=10;r.save_state=12345;
 r.intents=r.flushed=r.binds=r.queues=r.worker_started=r.worker_joined=r.native_success=
  r.finalizer_returned=r.return_matched=1;
 r.phase_mask=31;r.executor_thread=GetCurrentThreadId();r.completed_requests=1;r.file_bytes_verified=true;
 // A codec fixture, not a native Save observation or SAN14 file.
 good.bytes.assign(65539,0x63);good.bytes[0]=11;
 check(native_storage_read::Sha256(good.bytes.data(),good.bytes.size(),good.sha256),"fixture digest");
 std::vector<unsigned char>encoded;
 check(packet::Encode(good,encoded)==packet::Error::None&&encoded.size()==packet::HeaderBytes+good.bytes.size(),"valid codec export");
 FILE*f=nullptr;fopen_s(&f,argv[1],"wbx");
 if(f){check(std::fwrite(encoded.data(),1,encoded.size(),f)==encoded.size(),"fixture packet bytes");check(std::fclose(f)==0,"close fixture packet");}
 else check(false,"create new fixture packet");
 auto rejected=[&](const fs::Artifact&a,packet::Error e,const char*label){
  encoded.assign(7,0xAA);check(packet::Encode(a,encoded)==e&&encoded.empty(),label);
 };
 auto bad=good;bad.request.filename[15]='x';rejected(bad,packet::Error::Request,"nonzero trailing filename");
 bad=good;bad.request.room_epoch=0;rejected(bad,packet::Error::Request,"unbound room");
 bad=good;bad.request.reserved=1;rejected(bad,packet::Error::Request,"reserved byte");
 bad=good;bad.report.status=fs::Status::Returned;rejected(bad,packet::Error::Report,"before FINALLY");
 bad=good;bad.report.active=1;rejected(bad,packet::Error::Report,"active native scope");
 bad=good;bad.report.original_returned=1;rejected(bad,packet::Error::Report,"missing returns");
 bad=good;bad.report.phase_mask=15;rejected(bad,packet::Error::Report,"missing native phase");
 bad=good;bad.report.full_world=true;rejected(bad,packet::Error::Report,"unsupported full world claim");
 bad=good;bad.report.room_ready=true;rejected(bad,packet::Error::Report,"unsupported ready claim");
 bad=good;bad.report.file_bytes_verified=false;rejected(bad,packet::Error::Report,"unverified file");
 bad=good;bad.bytes[1]^=1;rejected(bad,packet::Error::Bytes,"hash mismatch");
 bad=good;bad.bytes.clear();rejected(bad,packet::Error::Bytes,"empty artifact");
 bad=good;bad.report.stop_after_commit=1;
 check(packet::Encode(bad,encoded)==packet::Error::None,"stopped after save remains observable, not publish permission");
 std::printf("{\"result\":\"%s\",\"checks\":%u,\"failures\":%u,\"game_access\":false}\n",failures?"FAIL":"PASS",checks,failures);
 return failures?1:0;
}

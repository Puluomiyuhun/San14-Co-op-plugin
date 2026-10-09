#include "b_warm_refresh_owner.h"
#include <cstdio>
#include <cstddef>
int main(){
 using namespace b_warm_refresh;
 std::printf("{\"Config\":%zu,\"Report\":%zu,\"Description\":%zu,\"Identity\":%zu,\"offsets\":{",sizeof(Config),sizeof(Report),sizeof(Description),sizeof(b_warm_storage_refresh::Identity));
 std::printf("\"warm\":%zu,\"write\":%zu,\"previousSize\":%zu,\"previousSha256\":%zu,\"sourceIdentity\":%zu,\"previousTargetIdentity\":%zu,\"targetPath\":%zu,\"backupPath\":%zu,\"refreshIntent\":%zu},",offsetof(Config,warm),offsetof(Config,write),offsetof(Config,previousSize),offsetof(Config,previousSha256),offsetof(Config,sourceIdentity),offsetof(Config,previousTargetIdentity),offsetof(Config,targetPath),offsetof(Config,backupPath),offsetof(Config,refreshIntent));
 std::printf("\"report_offsets\":{\"stage\":%zu,\"firstFailure\":%zu,\"attempt\":%zu,\"epoch\":%zu,\"generation\":%zu}}\n",offsetof(Report,stage),offsetof(Report,firstFailure),offsetof(Report,attempt),offsetof(Report,epoch),offsetof(Report,generation));return 0;
}

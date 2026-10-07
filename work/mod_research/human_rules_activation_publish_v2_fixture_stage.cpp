// Test-only compilation shim around independent activation_v2.cpp.
// Its fixture guard accepts MEM_PRIVATE. This test requires actual MEM_IMAGE;
// only this local preparer's type query is translated after verifying the owned
// image base. External debugger publisher always uses the real OS query.
#include <windows.h>
static SIZE_T ownFixtureQuery(const void*p,MEMORY_BASIC_INFORMATION*out,SIZE_T n){
 auto result=VirtualQuery(p,out,n);
 if(result==sizeof(*out)&&out->Type==MEM_IMAGE&&out->AllocationBase==reinterpret_cast<void*>(0x10000000))out->Type=MEM_PRIVATE;
 return result;
}
#define HUMAN_RULES_ACTIVATION_FIXTURE
#define VirtualQuery ownFixtureQuery
#include "human_rules_activation_v2.cpp"

#include "checkpoint_load_hook_set.h"
#include <cstdio>
#include <cstring>
using namespace checkpoint_load_hook_set;
static unsigned checks=0,failures=0;
static void check(bool value){++checks;if(!value)++failures;}
static int original(){return 1;} static int hook(){return 2;} static int foreign(){return 3;}
static DWORD protection(void* p){MEMORY_BASIC_INFORMATION m{};VirtualQuery(p,&m,sizeof m);return m.Protect;}
int main(int argc,char**argv){
    if(argc!=2)return 2;const char* mode=argv[1];
    auto page=static_cast<void**>(VirtualAlloc(nullptr,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));if(!page)return 3;
    Binding bindings[6];for(unsigned i=0;i<6;++i){page[i]=reinterpret_cast<void*>(&original);bindings[i]={page+i,page[i],reinterpret_cast<void*>(&hook)};}
    DWORD old=0;VirtualProtect(page,4096,PAGE_READONLY,&old);
    Set set;
    if(!strcmp(mode,"duplicate")){bindings[5]=bindings[0];check(!set.Initialize(bindings,6));}
    else if(!strcmp(mode,"unaligned")){bindings[0].slot=reinterpret_cast<void*volatile*>(reinterpret_cast<char*>(page)+1);check(!set.Initialize(bindings,6));}
    else if(!strcmp(mode,"inaccessible")){VirtualProtect(page,4096,PAGE_NOACCESS,&old);check(!set.Initialize(bindings,6));VirtualProtect(page,4096,PAGE_READONLY,&old);}
    else if(!strcmp(mode,"wrong-original")){bindings[0].original=reinterpret_cast<void*>(&foreign);check(!set.Initialize(bindings,6));}
    else {
        check(set.Initialize(bindings,6));check(!set.Initialize(bindings,6));check(!set.Publish(6));
        if(!strcmp(mode,"protection-drift")){VirtualProtect(page,4096,PAGE_READWRITE,&old);check(!set.Publish(0));check(page[0]==reinterpret_cast<void*>(&original));VirtualProtect(page,4096,PAGE_READONLY,&old);}
        else {
            for(unsigned i=0;i<6;++i){check(set.Publish(i));check(protection(page)==PAGE_READONLY);check(page[i]==reinterpret_cast<void*>(&hook));check(!set.Publish(i));}
            if(!strcmp(mode,"foreign-overwrite")){
                VirtualProtect(page,4096,PAGE_READWRITE,&old);page[2]=reinterpret_cast<void*>(&foreign);VirtualProtect(page,4096,PAGE_READONLY,&old);
                check(!set.RestoreAll());check(page[2]==reinterpret_cast<void*>(&foreign));check(protection(page)==PAGE_READONLY);
                for(unsigned i=0;i<6;++i)if(i!=2)check(page[i]==reinterpret_cast<void*>(&original));
            }else {check(set.RestoreAll());check(set.RestoreAll());for(unsigned i=0;i<6;++i){check(page[i]==reinterpret_cast<void*>(&original));check(!set.Publish(i));}check(protection(page)==PAGE_READONLY);}
        }
    }
    Report report{};set.Snapshot(report);
    VirtualFree(page,0,MEM_RELEASE);
    std::printf("{\"case\":\"%s\",\"passed\":%s,\"checks\":%u,\"failures\":%u,\"game_access\":false}\n",mode,failures?"false":"true",checks,failures);
    return failures?1:0;
}

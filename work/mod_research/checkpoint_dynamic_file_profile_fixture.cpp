#include "checkpoint_dynamic_file_profile.h"
#include <cstdio>
#include <cstring>
namespace p=checkpoint_dynamic_file_profile;
int main(){
    unsigned n=0,bad=0;auto check=[&](bool value){++n;if(!value)++bad;};
    p::Profile a{};strcpy_s(a.name,p::SupportedName);a.slot=63;a.size=257;a.sha256[0]=1;
    check(p::Validate(a));p::Profile out{};check(p::Capture(&a,out));check(p::Equal(a,out));
    auto b=a;b.size=65537;b.sha256[0]=2;check(p::Validate(b));check(!p::Equal(a,b));
    b=a;b.slot=64;check(!p::Validate(b));b=a;b.name[0]='x';check(!p::Validate(b));
    b=a;b.name[31]=1;check(!p::Validate(b));b=a;b.size=0;check(!p::Validate(b));
    b=a;b.size=0x80000000u;check(!p::Validate(b));b=a;memset(b.sha256,0,32);check(!p::Validate(b));
    b=a;b.size=p::MaximumSize;check(p::Validate(b));++b.size;check(!p::Validate(b));
    check(!p::Capture(nullptr,out));check(!p::Capture(reinterpret_cast<p::Profile*>(0x1234),out));
    check(p::Equal(a,out)); // failed capture never replaces previously valid copy
    std::printf("{\"case\":\"profile_contract\",\"passed\":%s,\"checks\":%u,\"failures\":%u,\"game_access\":false}\n",bad?"false":"true",n,bad);
    return bad?1:0;
}

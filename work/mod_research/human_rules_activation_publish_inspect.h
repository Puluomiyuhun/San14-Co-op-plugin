#pragma once
#include "human_rules_activation.h"
#include "human_rules_activation_profile.h"
#include <cstring>
#include <initializer_list>
// Every read is external RPM. No target function, code or thread is called.
struct ActivationInspection {
 using A=std::uint64_t;HANDLE process;A module,stateRva,bindingRva;human_rules_activation::Config binding;
 bool take(A address,void*out,SIZE_T n)const{SIZE_T done=0;return ReadProcessMemory(process,reinterpret_cast<void*>(address),out,n,&done)&&done==n;}
 template<class T>bool eq(A address,T expected)const{T v{};return take(address,&v,sizeof v)&&v==expected;}
 bool bytes(A address,const void*expected,SIZE_T n)const{unsigned char out[256]{};return n<=sizeof out&&take(address,out,n)&&!memcmp(out,expected,n);}
 bool current()const{
 LONG guard=0;unsigned option=0;return eq<LONG>(module+stateRva,human_rules_activation::Sealed)&&
 eq(binding.image+0x1FCA1E0,binding.root)&&eq(binding.root+0x85130,binding.world)&&take(binding.image+0x1FD0C5C,&guard,4)&&guard!=0&&guard!=-1&&
 eq<unsigned>(binding.image+0x18EB628,binding.income_key5)&&take(binding.world+0x16A8,&option,4)&&((option>>8)&1)==binding.world_option8;
 }
 bool date(bool restoring)const{
 WORD year=0;BYTE month=0,day=0;
 return take(binding.world+0x34,&year,2)&&take(binding.world+0x36,&month,1)&&take(binding.world+0x37,&day,1)&&year&&month>=1&&month<=12&&(day==1||day==11||day==21)&&
 (restoring||(year==binding.year&&month==binding.month&&day==binding.day));
 }
 static bool reader(void*c,A p,void*out,std::size_t n)noexcept{return static_cast<ActivationInspection*>(c)->take(p,out,n);}
 bool humans(){
 auto mask=(A(1)<<binding.force[0])|(A(1)<<binding.force[1]);for(unsigned i=0;i<2;++i){A force=0;
 if(!take(binding.root+0xDCA0+binding.force[i]*8,&force,8))return false;
 const auto result=san14_ai_runtime::ResolveSubject({this,reader},{binding.image,binding.root,force,mask,san14_ai_runtime::Route::Force});
 if(result.fault!=san14_ai_runtime::Fault::None||!result.repeated_reads_equal||result.decision!=san14_ai_runtime::Decision::BypassHumanDecision||result.humans.main_district[binding.force[i]]!=binding.main_district[i])return false;
 }return true;
 }
bool idle(bool restoring){
 auto b=binding.image,m=b+0x19E7310;std::uint64_t stack=0,cache=0;
 if(!current()||!eq<std::uint64_t>(m+0x10,5)||!eq<std::uint64_t>(m+0x30,0)||!take(m+0x20,&stack,8))return false;
 const char*names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};
 const std::uint64_t vt[]={0,0x12F22D8,0x12CC9B8,0x12CD400,0x12CC4A8};std::uint64_t states[5]{};
 for(unsigned i=0;i<5;++i){auto&s=states[i];if(!take(stack+i*8,&s,8)||!s||!bytes(s+0x70,names[i],strlen(names[i])+1)||!eq<DWORD>(s+0x68,0)||(i&&!eq(s,b+vt[i]))||(i!=4&&!eq<std::uint64_t>(s+0x50,0)))return false;for(unsigned j=0;j<i;++j)if(s==states[j])return false;}
 // m+48 is a transient dispatcher field, NOT persistent User identity. The
 // formal stack supplies User; idle UI requests are checked independently.
 auto user=states[4];std::uint64_t toolbar=0,panel=0,special=0,control=0,capacity=0,data=0;
 if(!take(user+0x478,&toolbar,8)||!toolbar||!take(states[2]+0x480,&panel,8)||!panel||
 !eq<LONG>(toolbar+0x88,-1)||!eq<DWORD>(states[2]+0x47C,0)||!eq<DWORD>(panel+0x1B0,0)||
 !take(user+0x618,&control,8)||!control)return false;
 for(auto offset:{0x4A8,0x4B0,0x4B8})if(!eq<std::uint64_t>(user+offset,0))return false;
 if(!take(b+0x201EC70,&special,8)||(special&&!eq<DWORD>(special,0))||!eq<DWORD>(b+0x1A38EC8+0x28,0)||!eq<DWORD>(b+0x19E7510+0x13C,1))return false;
 if(!take(m+0x38,&capacity,8)||!take(m+0x40,&data,8)||capacity>4096||((capacity==0)!=(data==0))||(data&&(data<0x10000||data>0x7FFFFFFFFFFFULL-capacity*16)))return false;
 return eq(binding.root,b+0x12AA6B0)&&eq(binding.world,b+0x12AA638)&&eq<DWORD>(states[4]+0x470,2)&&date(restoring)&&eq<BYTE>(binding.world+0x3A,BYTE(binding.viewer))&&eq<BYTE>(binding.world+0x165D,1)&&eq<DWORD>(binding.world+0x40,1)&&
 take(b+0x2025318,&cache,8)&&cache&&eq<LONG>(cache+0x3EC,-1)&&eq<DWORD>(cache+0x3F0,0)&&eq<DWORD>(cache+8,0);
}
 bool check(bool restoring){
 if(binding.version!=1||binding.size!=sizeof binding||!binding.image||!binding.root||!binding.world||binding.force[0]<1||binding.force[0]>51||binding.force[1]<1||binding.force[1]>51||binding.force[0]==binding.force[1]||binding.income_key5>3||binding.world_option8>1||(binding.viewer!=binding.force[0]&&binding.viewer!=binding.force[1]))return false;
 human_rules_activation::Config a{},b{};LONG before=0,after=0;
 if(!take(module+stateRva,&before,4)||before!=human_rules_activation::Sealed||!take(module+bindingRva,&a,sizeof a)||memcmp(&binding,&a,sizeof a))return false;
 for(const auto&anchor:human_rules_activation_profile::SettingsAnchors)if(!bytes(binding.image+anchor.rva,anchor.bytes,anchor.size))return false;
 return idle(restoring)&&humans()&&current()&&take(module+bindingRva,&b,sizeof b)&&!memcmp(&a,&b,sizeof a)&&take(module+stateRva,&after,4)&&after==before;
 }
};

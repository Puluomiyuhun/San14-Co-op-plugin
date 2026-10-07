#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "human_ai_runtime_subject.h"
#include "human_ai_runtime_profile.h"
#include <map>
#include <set>
#include <vector>
#include <cstring>
namespace san14_ai_runtime {namespace {
struct Failed{Fault fault;};
void require(bool b,Fault f){if(!b)throw Failed{f};}
bool pointer(Address p){return p>=0x10000&&p<0x7fffffffffffULL&&!(p&7);}
struct Sample {
 const Reader&r;std::map<std::pair<Address,std::size_t>,std::vector<unsigned char>> reads;
 void read(Address p,void*out,std::size_t n){
  require(n&&n<0x100000&&p>=0x10000&&p+n>p&&p+n<0x7fffffffffffULL,Fault::Pointer);
  const auto key=std::make_pair(p,n);auto it=reads.find(key);
  if(it==reads.end()){require(reads.size()<32768,Fault::Read);std::vector<unsigned char> b(n);require(r.read(r.context,p,b.data(),n),Fault::Read);it=reads.emplace(key,std::move(b)).first;}
  std::memcpy(out,it->second.data(),n);
 }
 template<class T>T get(Address p){T v{};read(p,&v,sizeof v);return v;}
 Address ptr(Address p,bool nullable=false){auto v=get<Address>(p);require((nullable&&!v)||pointer(v),Fault::Pointer);return v;}
 void type(Address p,Address vt){require(pointer(p)&&get<Address>(p)==vt,Fault::Table);}
 void anchor(Address image,const Anchor&a){std::vector<unsigned char>b(a.size);read(image+a.rva,b.data(),b.size());require(!std::memcmp(b.data(),a.bytes,b.size()),Fault::Profile);}
 void verify(){for(const auto&e:reads){std::vector<unsigned char>b(e.first.second);require(r.read(r.context,e.first.first,b.data(),b.size()),Fault::Read);require(b==e.second,Fault::Unstable);}}
 static bool callback(void*c,Address p,void*out,std::size_t n)noexcept{try{static_cast<Sample*>(c)->read(p,out,n);return true;}catch(...){return false;}}
};
struct Decoder {
 Sample&s;const Request&q;Address force0=0,district0=0,person0=0,army0=0,world=0;
 struct District {unsigned id=0,force=0,kind=0,leader=0;bool valid=false;};
 void init(){
  for(const auto&a:QueryAnchors)s.anchor(q.image,a);
  for(const auto&a:san14_group_resolver::Anchors)s.anchor(q.image,a);
  for(const auto p:{std::pair<Address,Address>{0x129FEB8,0x20B610},{0x129FB78,0x2F6330},{0x129FEE0,0x211610},{0x12A00E8,0x2119F0}})require(s.get<Address>(q.image+p.first)==q.image+p.second,Fault::Profile);
  require(s.ptr(q.image+0x1FCA1E0)==q.root,Fault::Table);
  force0=s.ptr(q.root+0xDCA0);district0=s.ptr(q.root+0xDE40);person0=s.ptr(q.root+0x737C0);army0=s.ptr(q.root+0x7DF60);world=s.ptr(q.root+0x85130);
  require(s.ptr(q.root+0x148)==person0,Fault::Table);
 }
 unsigned force(Address p){require(p>=force0&&(p-force0)%0x1D0==0&&(p-force0)/0x1D0<=51,Fault::Table);auto id=unsigned((p-force0)/0x1D0);require(s.ptr(q.root+0xDCA0+id*8)==p,Fault::Table);s.type(p,q.image+0x129FE58);return id;}
 District district(Address p){require(p>=district0&&(p-district0)%0x28==0&&(p-district0)/0x28<=51,Fault::Table);District d{};d.id=unsigned((p-district0)/0x28);require(s.ptr(q.root+0xDE40+d.id*8)==p,Fault::Table);s.type(p,q.image+0x129FEC8);d.force=s.get<std::uint8_t>(p+0x10);d.kind=s.get<std::uint8_t>(p+0x11);d.leader=s.get<std::uint16_t>(p+0x12);d.valid=d.id&&d.force&&d.kind&&d.leader;return d;}
 unsigned personDistrict(unsigned leader,bool&valid){
  auto p=leader<=6000?s.ptr(q.root+0x148+leader*8):person0;require(p>=person0&&(p-person0)%0x200==0&&((p==person0)==(leader==0||leader>6000)),Fault::Table);s.type(p,q.image+0x12A00D0);
  const auto id=s.get<std::uint16_t>(p+0x10);const auto rank=s.get<std::uint8_t>(p+0x11E);valid=p!=person0&&((id>=5001&&id<=5100)||rank);return valid?s.get<std::uint8_t>(p+0x118):0;
 }
 std::vector<District> ordered(){
  s.type(q.root+0xC8,q.image+0x123F3F8);auto handle=s.ptr(q.root+0xD0,true);if(!handle)return{};
  require(s.get<Address>(q.image+0x201D3A8)!=0&&s.get<std::uint32_t>(q.image+0x201D3E0)==0x14000,Fault::List);auto slot=s.get<std::uint32_t>(handle);require(slot<0x14000,Fault::List);
  auto heads=s.ptr(q.image+0x201D3B0),tails=s.ptr(q.image+0x201D3B8),counts=s.ptr(q.image+0x201D3C8);auto count=s.get<Address>(counts+slot*8);require(count<=51,Fault::List);
  auto node=s.ptr(heads+slot*8,true);Address previous=0;std::set<Address> seen,objects;std::vector<District> out;
  while(node){require(out.size()<count&&seen.insert(node).second,Fault::List);auto p=s.ptr(node);require(objects.insert(p).second&&s.get<Address>(node+16)==previous,Fault::List);out.push_back(district(p));previous=node;node=s.ptr(node+8,true);}
  require(out.size()==count&&s.get<Address>(tails+slot*8)==previous,Fault::List);return out;
 }
 Subject resolve(){
  init();Subject out{};out.humans.force_mask=q.human_mask;out.viewer=s.get<std::uint8_t>(world+0x3A);out.option=(s.get<std::uint32_t>(world+0x16A8)&0x100)!=0;
  require(out.viewer>=1&&out.viewer<=51&&(q.human_mask&(Address(1)<<out.viewer)),Fault::HumanBinding);
  const auto districts=ordered();unsigned main_mask_count=0;std::set<unsigned> mains;
  for(unsigned f=1;f<=51;++f)if(q.human_mask&(Address(1)<<f)){
   auto fp=s.ptr(q.root+0xDCA0+f*8);require(force(fp)==f,Fault::HumanBinding);const auto ruler=s.get<std::uint16_t>(fp+0x10);bool valid=false;personDistrict(ruler,valid);require(valid,Fault::HumanBinding);
   for(const auto&d:districts)if(d.force==f&&(d.leader==ruler||d.kind==1)){require(d.valid&&mains.insert(d.id).second,Fault::HumanBinding);out.humans.main_district[f]=d.id;++main_mask_count;break;}
  }
  require(main_mask_count==2,Fault::HumanBinding);
  if(q.route==Route::Force){const auto f=force(q.object);out.identity={f,0,f>=1&&f<=51};}
  else if(q.route==Route::District){const auto d=district(q.object);out.identity={d.force,d.id,d.valid&&d.force<=51};}
  else if(q.route==Route::Army){
   require(q.object>=army0&&(q.object-army0)%0x200==0&&(q.object-army0)/0x200<=500,Fault::Table);auto id=unsigned((q.object-army0)/0x200);require(s.ptr(q.root+0x7DF60+id*8)==q.object,Fault::Table);s.type(q.object,q.image+0x123E288);
   bool valid=false;auto did=personDistrict(s.get<std::uint16_t>(q.object+0x12),valid);if(valid&&did>=1&&did<=51){auto d=district(s.ptr(q.root+0xDE40+did*8));out.identity={d.force,d.id,d.valid&&d.force<=51};}
  }else{
   const auto group=san14_group_resolver::Resolve({&s,Sample::callback},{q.image,q.root,q.object,out.humans});out.group_fault=group.error;require(group.error==san14_group_resolver::Error::None,Fault::Group);out.identity=group.subject;
  }
  out.decision=san14_link::decide_ai(out.humans,q.route,out.identity,out.option);s.verify();out.repeated_reads_equal=true;out.distinct_reads=s.reads.size();return out;
 }
};
}
Subject ResolveSubject(const Reader&r,const Request&q)noexcept{
 try{constexpr Address valid=((Address(1)<<52)-1)&~Address(1);auto bits=q.human_mask;unsigned count=0;for(;bits;bits&=bits-1)++count;require(r.read&&pointer(q.image)&&pointer(q.root)&&pointer(q.object)&&q.image<0x7fffffffffffULL-0x2200000&&!(q.human_mask&~valid)&&count==2&&unsigned(q.route)<4,Fault::Configuration);Sample s{r,{}};Decoder d{s,q};return d.resolve();}
 catch(const Failed&e){Subject out{};out.fault=e.fault;return out;}catch(...){Subject out{};out.fault=Fault::Allocation;return out;}
}
bool ValidateOuterEntries(const Reader&r,Address image)noexcept{try{require(r.read&&pointer(image)&&image<0x7fffffffffffULL-0x2200000,Fault::Configuration);Sample s{r,{}};for(const auto&site:HookSites)s.anchor(image,site.original);s.verify();return true;}catch(...){return false;}}
bool ReadLocal(void*,Address p,void*out,std::size_t n)noexcept{if(!out||!n||n>=0x100000||p<0x10000||p+n<=p||p+n>=0x7fffffffffffULL)return false;__try{std::memcpy(out,reinterpret_cast<const void*>(p),n);return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
}

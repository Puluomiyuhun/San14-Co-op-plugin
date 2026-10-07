#include "human_ai_group_resolver.h"
#include "human_ai_group_resolver_profile.h"
#include <array>
#include <cstring>
#include <map>
#include <set>
#include <vector>
#include <utility>
#include <stdexcept>
namespace san14_group_resolver {
namespace {
struct Failure {Error error;};
void need(bool ok,Error e){if(!ok)throw Failure{e};}
bool pointer(Address p){return p>=0x10000&&p<0x7fffffffffffULL&&!(p&7);}
struct Snapshot {
 const Reader&r;std::map<std::pair<Address,std::size_t>,std::vector<unsigned char>> reads;
 void bytes(Address p,void*out,std::size_t n){
  need(n&&p>=0x10000&&p<0x7fffffffffffULL&&n<0x100000&&p+n>p&&p+n<=0x7fffffffffffULL,Error::Pointer);
  auto key=std::make_pair(p,n);auto found=reads.find(key);
  if(found==reads.end()){need(reads.size()<32768,Error::Read);std::vector<unsigned char> value(n);need(r.read(r.context,p,value.data(),n),Error::Read);found=reads.emplace(key,std::move(value)).first;}
  std::memcpy(out,found->second.data(),n);
 }
 template<class T>T get(Address p){T v{};bytes(p,&v,sizeof v);return v;}
 Address ptr(Address p,bool nullable=false){auto v=get<Address>(p);need((nullable&&!v)||pointer(v),Error::Pointer);return v;}
 void type(Address p,Address expected){need(pointer(p)&&get<Address>(p)==expected,Error::Table);}
 void verify(){for(const auto& e:reads){std::vector<unsigned char> fresh(e.first.second);need(r.read(r.context,e.first.first,fresh.data(),fresh.size()),Error::Read);need(fresh==e.second,Error::Unstable);}}
};
struct Army {unsigned id,flag,leader,group;Address address;};
struct Owner {unsigned district=0,force=0;};
struct Model {
 Snapshot&s;const Request&q;Address army0=0,group0=0,person0=0,district0=0;
 std::map<unsigned,Army> armies;std::map<unsigned,Owner> people;
 std::vector<std::array<Address,3>> list(Address object,Address vt,Address pool,unsigned capacity,unsigned max,bool relation){
  s.type(object,q.image+vt);auto h=s.ptr(object+8,true);if(!h)return{};
  need(s.get<Address>(q.image+pool+8)!=0&&s.get<std::uint32_t>(q.image+pool+0x40)==capacity,Error::List);
  auto slot=s.get<std::uint32_t>(h);need(slot<capacity,Error::List);
  auto heads=s.ptr(q.image+pool+0x10),tails=s.ptr(q.image+pool+0x18),counts=s.ptr(q.image+pool+0x28);
  auto count=s.get<Address>(counts+8*slot);need(count<=max,Error::List);
  auto node=s.ptr(heads+8*slot,true);Address last=0;std::set<Address> seen;std::vector<std::array<Address,3>> rows;
  while(node){
   need(seen.insert(node).second&&rows.size()<count,Error::List);std::array<Address,8> raw{};
   s.bytes(node,raw.data(),relation?64:24);need(raw[relation?7:2]==last,Error::List);
   rows.push_back({raw[0],relation?raw[1]:0,relation?raw[2]:0});last=node;node=raw[relation?6:1];need(!node||pointer(node),Error::Pointer);
  }
  need(rows.size()==count&&s.get<Address>(tails+8*slot)==last,Error::List);return rows;
 }
 const Army& army(Address p){
  need(pointer(p)&&p>=army0&&(p-army0)%0x200==0&&(p-army0)/0x200<=500,Error::Table);const unsigned id=unsigned((p-army0)/0x200);
  auto found=armies.find(id);if(found!=armies.end())return found->second;
  need(s.ptr(q.root+0x7DF60+id*8)==p,Error::Table);s.type(p,q.image+0x123E288);
  return armies.emplace(id,Army{id,s.get<std::uint8_t>(p+0x10),s.get<std::uint16_t>(p+0x12),s.get<std::uint16_t>(p+0x58),p}).first->second;
 }
 bool valid(Address p){if(!p)return false;auto a=army(p);return a.id&&a.flag&&a.leader;}
 Owner owner(const Army&a){
  const unsigned id=a.leader<=6000?a.leader:0;auto found=people.find(id);if(found!=people.end())return found->second;
  auto p=id?s.ptr(q.root+0x148+id*8):person0;
  need(p>=person0&&(p-person0)%0x200==0&&((p==person0)==(id==0)),Error::Table);s.type(p,q.image+0x12A00D0);
  Owner o{};const auto personId=s.get<std::uint16_t>(p+0x10);const auto rank=s.get<std::uint8_t>(p+0x11E);
  if(p!=person0&&((personId>=5001&&personId<=5100)||rank)){
   o.district=s.get<std::uint8_t>(p+0x118);const unsigned d=o.district<=51?o.district:0;
   auto address=s.ptr(q.root+0xDE40+d*8);need(address==district0+d*0x28,Error::Table);s.type(address,q.image+0x129FEC8);
   const auto force=s.get<std::uint8_t>(address+0x10),kind=s.get<std::uint8_t>(address+0x11);const auto leader=s.get<std::uint16_t>(address+0x12);
   if(d&&force&&kind&&leader)o.force=force;
  }
  people.emplace(id,o);return o;
 }
 void profile(){
  for(const auto&a:Anchors){std::vector<unsigned char> bytes(a.size);s.bytes(q.image+a.rva,bytes.data(),bytes.size());need(!std::memcmp(bytes.data(),a.bytes,a.size),Error::Profile);}
  for(const auto pair:{std::pair<Address,Address>{0x129FC08,0x2F63E0},{0x123E2A0,0x211420},{0x12A00E8,0x2119F0},{0x129FEE0,0x211610}})
   need(s.get<Address>(q.image+pair.first)==q.image+pair.second,Error::Profile);
  need(s.ptr(q.image+0x1FCA1E0)==q.root,Error::Table);
  army0=s.ptr(q.root+0x7DF60);group0=s.ptr(q.root+0x7F000);person0=s.ptr(q.root+0x737C0);district0=s.ptr(q.root+0xDE40);
  need(s.ptr(q.root+0x148)==person0,Error::Table);
 }
 Result resolve(){
  Result out{};profile();need(q.group>=group0&&(q.group-group0)%0x40==0&&(q.group-group0)/0x40<=500,Error::Table);
  out.group_id=unsigned((q.group-group0)/0x40);need(s.ptr(q.root+0x7F000+out.group_id*8)==q.group,Error::Table);s.type(q.group,q.image+0x129FF30);
  const auto order=list(q.root+0x58,0x123E200,0x201D3A0,0x14000,501,false);
  const auto explicitRows=list(q.root+0x68,0x123E200,0x201D3A0,0x14000,501,false);
  const auto relations=list(q.root+0x138,0x12AA618,0x1FC9760,64,500,true);
  std::set<Address> excluded,ordered;
  for(const auto&row:explicitRows){army(row[0]);need(excluded.insert(row[0]).second,Error::List);}
  for(const auto&row:relations){
   for(auto p:row)if(p)army(p);
   if(valid(row[1])&&valid(row[2])){const auto f=owner(army(row[2])).force;if(f!=51&&!(46<=f&&f<=50))excluded.insert(row[2]);}
   if(valid(row[0]))excluded.insert(row[0]);
  }
  for(const auto&row:order){
   const auto&a=army(row[0]);need(ordered.insert(a.address).second,Error::List);
   // Native membership deliberately DOES NOT test Army::valid, and does not
   // search a later leader when the first surviving member is invalid.
   if(out.group_id&&a.group==out.group_id&&!excluded.count(a.address)){
    ++out.members;if(!out.first_army){out.first_army=a.address;out.first_army_id=a.id;const auto o=owner(a);out.native_district=o.district;out.force=o.force;}
   }
  }
  auto world=s.ptr(q.root+0x85130);const bool option=(s.get<std::uint32_t>(world+0x16A8)&0x100)!=0;
  out.subject={out.force,out.native_district,out.force>=1&&out.force<=51&&out.native_district>=1&&out.native_district<=51};
  out.decision=san14_link::decide_ai(q.humans,san14_link::AiRoute::ArmyGroup,out.subject,option);
  s.verify();out.repeated_reads_equal=true;out.distinct_reads=s.reads.size();return out;
 }
};
}
Result Resolve(const Reader&r,const Request&q) noexcept {
 try{need(r.read&&pointer(q.image)&&pointer(q.root)&&pointer(q.group)&&q.image<0x7fffffffffffULL-0x2200000,Error::Config);Snapshot s{r,{}};Model m{s,q};return m.resolve();}
 catch(const Failure&f){Result out{};out.error=f.error;return out;}
 catch(...){Result out{};out.error=Error::Allocation;return out;}
}
}

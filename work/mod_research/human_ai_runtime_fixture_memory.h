// Additive own-process data memory helper copied from frozen group fixture.
#pragma once
#include "human_ai_group_resolver.h"
#include "human_ai_group_resolver_profile.h"
#include <map>
#include <vector>
#include <fstream>
#include <cstring>
#include <stdexcept>
#include <cstdio>
namespace gr=san14_group_resolver;
using A=gr::Address;
constexpr A image=0x10000000,root=0x20000000,army=0x30000000,person=0x40000000,group=0x50000000,district=0x60000000,aux=0x70000000,world=0x71000000;
void check(bool v,const char*why){if(!v)throw std::runtime_error(why);}
struct Memory {
 std::map<A,std::vector<unsigned char>> regions;
 A fail=0,unstable=0;unsigned seen=0;
 Memory(){for(const auto p:{std::pair<A,std::size_t>{image,0x2200000},{root,0x86000},{army,501*0x200},{person,6001*0x200},{group,501*0x40},{district,52*0x28},{aux,0x20000},{world,0x2000}})regions.emplace(p.first,std::vector<unsigned char>(p.second));}
 void* at(A p,std::size_t n){auto it=regions.upper_bound(p);if(it==regions.begin())return nullptr;--it;const auto offset=p-it->first;if(offset>it->second.size()||n>it->second.size()-offset)return nullptr;return it->second.data()+offset;}
 template<class T>void put(A p,T v){auto*out=at(p,sizeof v);check(out!=nullptr,"fixture write bounds");std::memcpy(out,&v,sizeof v);}
 static bool read(void*c,A p,void*out,std::size_t n)noexcept{auto&m=*static_cast<Memory*>(c);if(m.fail&&p<=m.fail&&m.fail-p<n)return false;auto*src=m.at(p,n);if(!src)return false;std::memcpy(out,src,n);if(p==m.unstable&&++m.seen>1)static_cast<unsigned char*>(out)[0]^=1;return true;}
 gr::Result resolve(unsigned id=1){gr::Request q{};q.image=image;q.root=root;q.group=group+id*0x40;q.humans.force_mask=(A(1)<<2)|(A(1)<<12);q.humans.main_district[2]=2;q.humans.main_district[12]=11;return gr::Resolve({this,read},q);}
 void fixed(){
  for(const auto&a:gr::Anchors)std::memcpy(at(image+a.rva,a.size),a.bytes,a.size);
  for(const auto p:{std::pair<A,A>{0x129FC08,0x2F63E0},{0x123E2A0,0x211420},{0x12A00E8,0x2119F0},{0x129FEE0,0x211610}})put(image+p.first,image+p.second);
  put(image+0x1FCA1E0,root);put(root+0x737C0,person);put(root+0x85130,world);
  for(unsigned i=0;i<=6000;++i){put(root+0x148+i*8,person+i*0x200);put(person+i*0x200,image+0x12A00D0);}
  for(unsigned i=0;i<=500;++i){put(root+0x7DF60+i*8,army+i*0x200);put(root+0x7F000+i*8,group+i*0x40);put(army+i*0x200,image+0x123E288);put(group+i*0x40,image+0x129FF30);}
  for(unsigned i=0;i<52;++i){put(root+0xDE40+i*8,district+i*0x28);put(district+i*0x28,image+0x129FEC8);}
  put(image+0x201D3A8,A(1));put(image+0x201D3E0,std::uint32_t(0x14000));put(image+0x201D3B0,aux+0x100);put(image+0x201D3B8,aux+0x120);put(image+0x201D3C8,aux+0x140);
  put(image+0x1FC9768,A(1));put(image+0x1FC97A0,std::uint32_t(64));put(image+0x1FC9770,aux+0x200);put(image+0x1FC9778,aux+0x220);put(image+0x1FC9788,aux+0x240);
  for(unsigned j=0;j<3;++j){put(root+(j==0?0x58:j==1?0x68:0x138),image+(j<2?0x123E200:0x12AA618));put(root+(j==0?0x60:j==1?0x70:0x140),aux+j*8);put(aux+j*8,std::uint32_t(j==1?1:0));}
 }
 void list(unsigned j,const std::vector<std::vector<int>>&rows){
  const A nodes=aux+0x1000+j*0x5000,stride=j==2?64:24;const A heads=aux+(j==2?0x200:0x100),tails=aux+(j==2?0x220:0x120),counts=aux+(j==2?0x240:0x140);const A slot=j==1?8:0;
  put(heads+slot,rows.empty()?A(0):nodes);put(tails+slot,rows.empty()?A(0):nodes+(rows.size()-1)*stride);put(counts+slot,A(rows.size()));
  for(std::size_t i=0;i<rows.size();++i){auto n=nodes+i*stride;for(std::size_t k=0;k<rows[i].size();++k)put(n+k*8,rows[i][k]<0?A(0):army+unsigned(rows[i][k])*0x200);put(n+(j==2?0x30:8),i+1<rows.size()?n+stride:A(0));put(n+(j==2?0x38:16),i?n-stride:A(0));}
 }
};

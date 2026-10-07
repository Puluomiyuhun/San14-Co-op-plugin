// Own-process data population copied additively from frozen AI runtime fixture.
#pragma once
#include "human_ai_runtime_fixture_memory.h"
namespace rt=san14_ai_runtime;
constexpr A forces=0x72000000;
void populate(Memory&m){
 m.fixed();m.regions.emplace(forces,std::vector<unsigned char>(52*0x1D0));
 for(const auto&a:rt::QueryAnchors)std::memcpy(m.at(image+a.rva,a.size),a.bytes,a.size);
 for(const auto&s:rt::HookSites)std::memcpy(m.at(image+s.original.rva,s.original.size),s.original.bytes,s.original.size);
 m.put(image+0x129FEB8,image+0x20B610);m.put(image+0x129FB78,image+0x2F6330);
 for(unsigned i=0;i<52;++i){m.put(root+0xDCA0+i*8,forces+i*0x1D0);m.put(forces+i*0x1D0,image+0x129FE58);m.put(forces+i*0x1D0+0x10,std::uint16_t(i));}
 m.put(world+0x3A,std::uint8_t(12));
 const unsigned ds[]={2,11,20,21,3},fs[]={2,12,2,12,3},leaders[]={2,12,20,21,3};
 for(unsigned i=0;i<5;++i){
  m.put(district+ds[i]*0x28+0x10,std::uint8_t(fs[i]));m.put(district+ds[i]*0x28+0x11,std::uint8_t(i==2||i==3?2:1));m.put(district+ds[i]*0x28+0x12,std::uint16_t(leaders[i]));
  m.put(person+leaders[i]*0x200+0x10,std::uint16_t(leaders[i]));m.put(person+leaders[i]*0x200+0x118,std::uint8_t(ds[i]));m.put(person+leaders[i]*0x200+0x11E,std::uint8_t(1));
  m.put(army+(i+1)*0x200+0x10,std::uint8_t(1));m.put(army+(i+1)*0x200+0x12,std::uint16_t(leaders[i]));m.put(army+(i+1)*0x200+0x58,std::uint16_t(i+1));
 }
 m.list(0,{{1},{2},{3},{4},{5}});m.list(1,{});m.list(2,{});
 m.put(root+0xC8,image+0x123F3F8);m.put(root+0xD0,aux+24);m.put(aux+24,std::uint32_t(2));m.put(aux+0x110,aux+0x18000);m.put(aux+0x130,aux+0x18000+4*24);m.put(aux+0x150,A(5));
 for(unsigned i=0;i<5;++i){const A n=aux+0x18000+i*24;m.put(n,district+ds[i]*0x28);m.put(n+8,i<4?n+24:A(0));m.put(n+16,i?n-24:A(0));}
}

#pragma once
// Exact original x64 unwind metadata, archived image/pdata. No game access.
namespace human_rules_hook {
inline constexpr unsigned char Unwind0[]={1,10,4,0,10,52,6,0,10,50,6,112};
inline constexpr unsigned char Unwind1[]={1,15,6,0,15,100,7,0,15,52,6,0,15,50,11,112};
inline constexpr unsigned char Unwind2[]={1,15,6,0,15,100,7,0,15,52,6,0,15,50,11,112};
inline constexpr unsigned char Unwind3[]={1,15,6,0,15,100,7,0,15,52,6,0,15,50,11,112};
struct UnwindProfile {unsigned start,end,rva;const unsigned char*bytes;unsigned size;};
inline constexpr UnwindProfile Unwinds[]={{0xc6660,0xc669c,0x17ab260,Unwind0,sizeof Unwind0},{0xc65f0,0xc6653,0x1778018,Unwind1,sizeof Unwind1},{0xc6580,0xc65e3,0x1778018,Unwind2,sizeof Unwind2},{0xc66a0,0xc6703,0x1778018,Unwind3,sizeof Unwind3}};
}

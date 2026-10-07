#pragma once
#include "human_ai_runtime_profile.h"
namespace san14_economy_runtime {
inline constexpr unsigned char BytesPredicate[]={72,137,92,36,8,87,72,131,236,32,72,139,5,31,145,219,1,72,139,217,72,139,136,48,81,8,0,232,16,17,14,0,72,139,200,72,139,16,255,82,96,139,248,133,192,116,29,72,139,19,72,139,203,255,82,96,59,248,117,16,184,1,0,0,0,72,139,92,36,48,72,131,196,32,95,195,51,192,72,139,92,36,48,72,131,196,32,95,195};
inline constexpr unsigned char BytesPlayerForce[]={15,182,65,58,131,248,51,119,18,139,200,72,139,5,238,127,205,1,72,139,132,200,160,220,0,0,195,72,139,5,222,127,205,1,72,139,128,160,220,0,0,195};
inline constexpr san14_ai_runtime::Anchor NativeAnchors[]={{0x2110b0,BytesPredicate,sizeof BytesPredicate},{0x2f21e0,BytesPlayerForce,sizeof BytesPlayerForce}};
struct Callsite {unsigned call_rva,return_rva;unsigned char original[5];};
inline constexpr Callsite Callsites[]={{0x28de71,0x28de76,{232,58,50,248,255}},{0x28daa5,0x28daaa,{232,6,54,248,255}}};
}

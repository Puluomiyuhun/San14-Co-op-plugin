#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <thread>
#include <mutex>
#include <vector>
#include <atomic>
#include <climits>
#include "native_rng_fixture_code.h"

static void check(bool v,const char* text){if(!v)throw std::runtime_error(text);}
class NativeRng {
    unsigned char* code=nullptr;
    std::vector<unsigned char> rootData,worldData;
public:
    explicit NativeRng(uint32_t state){
        code=(unsigned char*)VirtualAlloc(nullptr,8192,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);
        check(code!=nullptr,"private allocation");std::memcpy(code,nativeRngCode,4096);
        DWORD old;check(VirtualProtect(code,4096,PAGE_EXECUTE_READ,&old)!=0,"code protection");
        check(FlushInstructionCache(GetCurrentProcess(),code,4096)!=0,"instruction cache");set(state);
    }
    NativeRng(const NativeRng&)=delete;NativeRng& operator=(const NativeRng&)=delete;
    ~NativeRng(){if(code)VirtualFree(code,0,MEM_RELEASE);}
    uintptr_t fixtureAddress(unsigned offset){return reinterpret_cast<uintptr_t>(code+offset);}
    uint32_t get(){return reinterpret_cast<uint32_t(*)()>(code)();}
    void set(uint32_t n){reinterpret_cast<void(*)(uint32_t)>(code+0x40)(n);}
    int unbounded(){return reinterpret_cast<int(*)()>(code+0x80)();}
    int percentage(int n){return reinterpret_cast<int(*)(int)>(code+0x100)(n);}
    int range(int n){return reinterpret_cast<int(*)(int)>(code+0x200)(n);}
    int derivedPercentage(int threshold,int salt,uint32_t worldValue){
        if(rootData.empty()){rootData.resize(0x85138);worldData.resize(0x458);}
        auto rootPtr=rootData.data();auto worldPtr=worldData.data();
        std::memcpy(code+0x1010,&rootPtr,8);std::memcpy(rootPtr+0x85130,&worldPtr,8);
        std::memcpy(worldPtr+0x454,&worldValue,4);
        return reinterpret_cast<int(*)(int,int)>(code+0x300)(threshold,salt);
    }
};

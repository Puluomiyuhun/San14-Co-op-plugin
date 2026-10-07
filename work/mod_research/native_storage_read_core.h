#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include <vector>

namespace native_storage_read {
// These are the observed Win64 v014 method ABIs. The caller must obtain and
// validate the interface from the game's supported ContextInit token. This
// core never discovers a process, imports Steam, installs a hook, or loads.
using FileExists = bool(__fastcall*)(void*, const char*);        // vtable+0x68
using GetFileSize = std::int32_t(__fastcall*)(void*, const char*);// vtable+0x78
using FileRead = std::int32_t(__fastcall*)(void*, const char*, void*, std::int32_t);// +0x08
using ValidateContext = bool(*)(void*);
struct Api {
    void* storage = nullptr;
    FileExists exists = nullptr;
    GetFileSize size = nullptr;
    FileRead read = nullptr;
    ValidateContext validate = nullptr;
    void* validationContext = nullptr;
};
// Input strings/API bindings remain valid and immutable for Verify's duration.
// validate must not throw C++ exceptions, and must revalidate the native
// interface, method addresses and permitted caller boundary before each call.
struct Input {
    const wchar_t* localPath = nullptr;
    const char* basename = nullptr;
    std::uint32_t expectedSize = 0;
    unsigned char expectedSha256[32]{};
};
struct Evidence {
    bool matched = false;
    const char* stage = "new";
    DWORD osError = 0, exceptionCode = 0;
    unsigned existsCalls = 0, sizeCalls = 0, readCalls = 0;
    std::int32_t sizes[3]{}, readReturns[2]{};
    unsigned char localSha256[32]{}, nativeSha256[2][32]{};
};
struct Lease {
    HANDLE file = INVALID_HANDLE_VALUE;
    std::vector<unsigned char> bytes;
    Lease() = default;
    Lease(const Lease&) = delete;
    Lease& operator=(const Lease&) = delete;
    ~Lease() { if (file != INVALID_HANDLE_VALUE) CloseHandle(file); }
};
// No file writing, deletion or directory creation. Success retains the local
// read-only handle without FILE_SHARE_WRITE/DELETE until Lease destruction.
// This proves two observed native reads matched pinned local bytes, not that
// any later Steam read is atomic or that a future world load used these bytes.
bool Verify(const Input&, const Api&, Lease&, Evidence&) noexcept;
bool Sha256(const void*, std::size_t, unsigned char out[32]) noexcept;
}

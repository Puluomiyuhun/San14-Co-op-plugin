#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

// Explicit-HWND read-only capture capability. No enumeration, discovery,
// activation, input injection, hooks, ReadProcessMemory, or video-mode changes.
namespace checkpoint_map_cover {
struct Binding {
    HWND window=nullptr;
    DWORD pid=0;
    std::uint64_t processBirth=0;
    std::wstring windowClass;
};
struct Observation {
    Binding identity;
    DWORD windowThread=0;
    RECT clientScreen{},windowScreen{},compositorFrameScreen{};
    UINT dpi=0;
    LONG_PTR style=0,extendedStyle=0;
    bool visible=false,minimized=false,cloaked=false;
};
struct Frame {
    unsigned width=0,height=0;
    std::uint64_t serial=0;
    std::int64_t systemRelativeTime=0;
    // Packed BGRA8 from the WGC/D3D11 texture, not a WM_PRINT rerender.
    std::vector<unsigned char> bgra;
};
bool InspectExplicitWindow(const Binding&,Observation&,HRESULT&) noexcept;
class Capture {
public:
    Capture();~Capture();Capture(const Capture&)=delete;Capture& operator=(const Capture&)=delete;
    // Caller separately authorizes this exact window. This does not establish
    // game attachment/world/view or input protection. Call from a separate UI/
    // capture helper, never inline on the game's load/update callback. Caller
    // initializes its WinRT apartment and serializes all methods on that thread.
    // Same geometry/DPI required
    // for the session; changes fail closed and require explicit fresh binding.
    bool Start(const Binding&,HRESULT&) noexcept;
    // Frame queues may contain older frames. A fresh transition observation must
    // supply its own QPC/100ns cutoff, then additionally verify world/view binding.
    bool Next(Frame&,DWORD timeoutMs,HRESULT&,std::int64_t notBefore=-1) noexcept;
    void Stop() noexcept;
    const Observation& InitialObservation() const noexcept;
    const char* LastStage() const noexcept;
private:
    struct Impl;std::unique_ptr<Impl> impl_;
};
}

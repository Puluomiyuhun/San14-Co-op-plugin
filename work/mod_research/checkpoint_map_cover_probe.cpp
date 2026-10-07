// Prepared read-only helper. No invocation against the game is part of this task.
#define UNICODE
#define _UNICODE
#include "checkpoint_map_cover_capture.h"
#include "native_storage_read_core.h"
#include <winrt/base.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <cerrno>
#include <cstring>
namespace c=checkpoint_map_cover;
namespace fs=std::filesystem;
std::uint64_t number(const wchar_t*text){wchar_t*end=nullptr;errno=0;auto result=std::wcstoull(text,&end,0);if(errno||!text[0]||*end||text[0]==L'-')throw std::runtime_error("invalid numeric binding");return result;}
void rect(std::ostream&out,const RECT&r){out<<'['<<r.left<<','<<r.top<<','<<r.right<<','<<r.bottom<<']';}
int wmain(int argc,wchar_t**argv){try{
    if(argc!=7||((std::wcscmp(argv[1],L"--inspect"))&&(std::wcscmp(argv[1],L"--capture")))){std::cout<<"Usage (explicitly authorized window only): --inspect|--capture HWND PID PROCESS_BIRTH WINDOW_CLASS OUTPUT_DIRECTORY\nNo window discovery, activation, input, or default capture.\n";return 2;}
    auto rawPid=number(argv[3]);if(!rawPid||rawPid>MAXDWORD)throw std::runtime_error("invalid PID");
    c::Binding bind{reinterpret_cast<HWND>(number(argv[2])),DWORD(rawPid),number(argv[4]),argv[5]};
    fs::path directory=fs::absolute(argv[6]);if(fs::exists(directory/L"result.json")||fs::exists(directory/L"capture.bmp"))throw std::runtime_error("fresh output directory required");fs::create_directories(directory);
    SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);winrt::init_apartment(winrt::apartment_type::multi_threaded);
    c::Observation observed{};HRESULT hr{};bool okay=c::InspectExplicitWindow(bind,observed,hr);c::Frame frame;const bool capture=!std::wcscmp(argv[1],L"--capture");std::string pixelHash;
    if(okay&&capture){c::Capture source;okay=source.Start(bind,hr)&&source.Next(frame,5000,hr);source.Stop();if(okay){
        unsigned char hash[32]{};okay=native_storage_read::Sha256(frame.bgra.data(),frame.bgra.size(),hash);if(!okay)hr=E_FAIL;
        const char digits[]="0123456789abcdef";for(auto b:hash){pixelHash+=digits[b>>4];pixelHash+=digits[b&15];}
        if(okay){BITMAPFILEHEADER head{};head.bfType=0x4D42;head.bfOffBits=sizeof(head)+sizeof(BITMAPINFOHEADER);head.bfSize=DWORD(head.bfOffBits+frame.bgra.size());BITMAPINFOHEADER info{};info.biSize=sizeof info;info.biWidth=frame.width;info.biHeight=-LONG(frame.height);info.biPlanes=1;info.biBitCount=32;info.biCompression=BI_RGB;
            std::ofstream image(directory/L"capture.bmp",std::ios::binary);image.write(reinterpret_cast<char*>(&head),sizeof head);image.write(reinterpret_cast<char*>(&info),sizeof info);image.write(reinterpret_cast<const char*>(frame.bgra.data()),frame.bgra.size());okay=bool(image);if(!okay)hr=E_FAIL;}
    }}
    std::ofstream out(directory/L"result.json");out<<"{\"schema\":\"san14.explicit-window-readonly-probe.v1\",\"result\":\""<<(okay?"PASS":"FAIL")<<"\",\"capture_requested\":"<<(capture?"true":"false")<<",\"hresult\":"<<unsigned(hr)<<",\"pid\":"<<bind.pid<<",\"process_birth\":"<<bind.processBirth<<",\"hwnd\":"<<std::uintptr_t(bind.window)<<",\"dpi\":"<<observed.dpi<<",\"client_screen\":";rect(out,observed.clientScreen);out<<",\"window_screen\":";rect(out,observed.windowScreen);out<<",\"compositor_frame_screen\":";rect(out,observed.compositorFrameScreen);
    out<<",\"style\":"<<std::uint64_t(observed.style)<<",\"extended_style\":"<<std::uint64_t(observed.extendedStyle)<<",\"capture_width\":"<<frame.width<<",\"capture_height\":"<<frame.height<<",\"capture_system_relative_time\":"<<frame.systemRelativeTime<<",\"pixel_sha256\":\""<<pixelHash<<"\",\"read_only\":true,\"activation\":false,\"input_injected\":false,\"hook_installed\":false,\"native_world_or_input_readiness_proved\":false,\"physical_monitor_unoccluded_proved\":false}\n";
    std::cout<<(okay?"PASS":"FAIL")<<" explicit window read-only probe\n";return okay?0:1;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 2;}catch(...){std::cerr<<"read-only probe exception\n";return 3;}}

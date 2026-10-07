#define UNICODE
#define _UNICODE
#include "checkpoint_map_cover_capture.h"
#include "native_storage_read_core.h"
#include <winrt/base.h>
#include <dwmapi.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <functional>
#include <stdexcept>
#include <cstring>
#pragma comment(lib,"gdi32.lib")
#pragma comment(lib,"user32.lib")
namespace c=checkpoint_map_cover;
constexpr int W=640,H=360,BAND=296;
struct WindowState {bool overlay=false,newWorld=false,failed=false;const c::Frame*frozen=nullptr;unsigned paints=0,activations=0;};
bool fill(HDC dc,RECT rect,COLORREF color){HBRUSH b=CreateSolidBrush(color);if(!b)return false;bool okay=FillRect(dc,&rect,b)!=0;DeleteObject(b);return okay;}
void paint(WindowState&state,HDC dc){
    if(state.overlay&&state.frozen){BITMAPINFO info{};info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);info.bmiHeader.biWidth=W;info.bmiHeader.biHeight=-H;info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32;info.bmiHeader.biCompression=BI_RGB;
        StretchDIBits(dc,0,0,W,H,0,0,W,H,state.frozen->bgra.data(),&info,DIB_RGB_COLORS,SRCCOPY);
        fill(dc,{0,BAND,W,H},state.failed?RGB(102,32,39):RGB(26,33,48));SetTextColor(dc,RGB(245,245,245));SetBkMode(dc,TRANSPARENT);
        const wchar_t*message=state.failed?L"SYNC HELD - old map retained; recovery required":L"SYNCHRONIZING - this is a frozen picture of the old map";
        TextOutW(dc,18,BAND+21,message,lstrlenW(message));
    }else{
        fill(dc,{0,0,W,H},state.newWorld?RGB(26,66,107):RGB(34,86,51));
        for(int x=24;x<W;x+=48)fill(dc,{x,0,x+1,H},RGB(76,112,102));
        for(int y=24;y<H;y+=48)fill(dc,{0,y,W,y+1},RGB(76,112,102));
        fill(dc,{60,80,125,128},RGB(225,194,120));fill(dc,state.newWorld?RECT{438,142,493,190}:RECT{230,184,285,232},RGB(203,107,74));
        SetTextColor(dc,RGB(250,250,250));SetBkMode(dc,TRANSPARENT);
        const wchar_t*text=state.newWorld?L"NEW SYNTHETIC WORLD | own test window | no SAN14 access":L"OLD SYNTHETIC WORLD | own test window | no SAN14 access";
        TextOutW(dc,16,8,text,lstrlenW(text));
    }
    ++state.paints;
}
LRESULT CALLBACK procedure(HWND hwnd,UINT msg,WPARAM wp,LPARAM lp){
    if(msg==WM_NCCREATE){auto*create=reinterpret_cast<CREATESTRUCTW*>(lp);SetWindowLongPtrW(hwnd,GWLP_USERDATA,reinterpret_cast<LONG_PTR>(create->lpCreateParams));return TRUE;}
    auto*state=reinterpret_cast<WindowState*>(GetWindowLongPtrW(hwnd,GWLP_USERDATA));
    if(state&&msg==WM_PAINT){PAINTSTRUCT ps{};auto dc=BeginPaint(hwnd,&ps);paint(*state,dc);EndPaint(hwnd,&ps);return 0;}
    if(state&&msg==WM_ACTIVATE&&LOWORD(wp)!=WA_INACTIVE)++state->activations;
    if(msg==WM_MOUSEACTIVATE)return MA_NOACTIVATE;
    if(msg==WM_ERASEBKGND)return 1;
    return DefWindowProcW(hwnd,msg,wp,lp);
}
void need(bool okay,const char*what){if(!okay)throw std::runtime_error(what);}
std::string hexhr(HRESULT hr){char text[32]{};sprintf_s(text,"0x%08X",unsigned(hr));return text;}
void needHR(bool okay,const HRESULT&hr,const char*what){if(!okay)throw std::runtime_error(std::string(what)+": "+hexhr(hr));}
std::string sha(const std::vector<unsigned char>&bytes){unsigned char hash[32]{};need(native_storage_read::Sha256(bytes.data(),bytes.size(),hash),"hash");std::string out;const char digits[]="0123456789abcdef";for(auto byte:hash){out+=digits[byte>>4];out+=digits[byte&15];}return out;}
std::vector<unsigned char>body(const c::Frame&f){std::vector<unsigned char>out;for(unsigned y=40;y<BAND-4;++y)out.insert(out.end(),f.bgra.begin()+(std::size_t(y)*f.width+4)*4,f.bgra.begin()+(std::size_t(y)*f.width+f.width-4)*4);return out;}
void save(const std::filesystem::path&path,const c::Frame&f){BITMAPFILEHEADER head{};head.bfType=0x4D42;head.bfOffBits=sizeof(head)+sizeof(BITMAPINFOHEADER);head.bfSize=DWORD(head.bfOffBits+f.bgra.size());BITMAPINFOHEADER bitmap{};bitmap.biSize=sizeof(bitmap);bitmap.biWidth=f.width;bitmap.biHeight=-LONG(f.height);bitmap.biPlanes=1;bitmap.biBitCount=32;bitmap.biCompression=BI_RGB;std::ofstream file(path,std::ios::binary);file.write(reinterpret_cast<char*>(&head),sizeof head);file.write(reinterpret_cast<char*>(&bitmap),sizeof bitmap);file.write(reinterpret_cast<const char*>(f.bgra.data()),f.bgra.size());need(bool(file),"save own WGC frame");}
c::Binding binding(HWND hwnd){FILETIME birth{},exit{},kernel{},user{};need(GetProcessTimes(GetCurrentProcess(),&birth,&exit,&kernel,&user)!=FALSE,"fixture birth");return {hwnd,GetCurrentProcessId(),(std::uint64_t(birth.dwHighDateTime)<<32)|birth.dwLowDateTime,L"CheckpointMapCoverOwnWindow"};}
void redraw(HWND hwnd){need(RedrawWindow(hwnd,nullptr,nullptr,RDW_INVALIDATE|RDW_UPDATENOW|RDW_ALLCHILDREN)!=FALSE,"native window paint");need(SUCCEEDED(DwmFlush()),"DWM flush");}
void settleOwnWindows(){auto until=GetTickCount64()+200;while(GetTickCount64()<until){MSG message{};while(PeekMessageW(&message,nullptr,0,0,PM_REMOVE)){TranslateMessage(&message);DispatchMessageW(&message);}Sleep(10);}}
std::int64_t captureTimeNow(){LARGE_INTEGER counter{},frequency{};need(QueryPerformanceCounter(&counter)&&QueryPerformanceFrequency(&frequency)&&frequency.QuadPart>0,"capture clock");return (counter.QuadPart/frequency.QuadPart)*10000000+(counter.QuadPart%frequency.QuadPart)*10000000/frequency.QuadPart;}
c::Frame receive(c::Capture&capture,const std::function<bool(const c::Frame&)>&predicate,std::int64_t cutoff=-1){HRESULT hr{};auto deadline=GetTickCount64()+5000;while(GetTickCount64()<deadline){c::Frame frame;needHR(capture.Next(frame,2000,hr,cutoff),hr,"WGC frame");need(frame.width==W&&frame.height==H,"fixture exact captured dimensions");if(predicate(frame))return frame;}throw std::runtime_error("captured pixels did not reach expected state");}
struct Windows {HWND map=nullptr,cover=nullptr;~Windows(){if(cover)DestroyWindow(cover);if(map)DestroyWindow(map);}};
int wmain(int argc,wchar_t**argv){std::filesystem::path out;try{
    need(argc==2,"fixture output directory required");out=argv[1];std::filesystem::create_directories(out);SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);winrt::init_apartment(winrt::apartment_type::multi_threaded);
    WNDCLASSW type{};type.lpfnWndProc=procedure;type.hInstance=GetModuleHandleW(nullptr);type.lpszClassName=L"CheckpointMapCoverOwnWindow";need(RegisterClassW(&type)!=0,"own fixture class");
    WindowState mapState,coverState;Windows windows;const auto flags=WS_EX_NOACTIVATE|WS_EX_APPWINDOW;
    windows.map=CreateWindowExW(flags,type.lpszClassName,L"Synthetic map fixture - not SAN14",WS_POPUP,80,80,W,H,nullptr,nullptr,type.hInstance,&mapState);need(windows.map!=nullptr,"create own map HWND");
    ShowWindow(windows.map,SW_SHOWNOACTIVATE);redraw(windows.map);settleOwnWindows();
    c::Capture mapCapture;HRESULT hr{};auto mapBinding=binding(windows.map);if(!mapCapture.Start(mapBinding,hr)){std::cerr<<"map capture stage="<<mapCapture.LastStage()<<"\n";needHR(false,hr,"WGC map start");}
    auto old=receive(mapCapture,[](const c::Frame&f){auto at=(std::size_t(45)*f.width+15)*4;return f.bgra[at]==51&&f.bgra[at+1]==86&&f.bgra[at+2]==34;});save(out/L"01-old-map-wgc.bmp",old);
    coverState.overlay=true;coverState.frozen=&old;
    windows.cover=CreateWindowExW(flags,type.lpszClassName,L"Frozen-map wait fixture - not SAN14",WS_POPUP,80,80,W,H,windows.map,nullptr,type.hInstance,&coverState);need(windows.cover!=nullptr,"create own cover HWND");
    need(GetWindow(windows.cover,GW_OWNER)==windows.map,"cover is owned only by our fixture");ShowWindow(windows.cover,SW_SHOWNOACTIVATE);redraw(windows.cover);settleOwnWindows();
    c::Capture coverCapture;auto coverBinding=binding(windows.cover);needHR(coverCapture.Start(coverBinding,hr),hr,"WGC cover start");
    auto waiting=receive(coverCapture,[&](const c::Frame&f){return body(f)==body(old);});save(out/L"02-frozen-cover-wgc.bmp",waiting);
    mapState.newWorld=true;auto backgroundCut=captureTimeNow();redraw(windows.map);
    auto background=receive(mapCapture,[&](const c::Frame&f){auto at=(std::size_t(45)*f.width+15)*4;return f.systemRelativeTime>backgroundCut&&f.bgra[at]==107&&f.bgra[at+1]==66&&f.bgra[at+2]==26;},backgroundCut);save(out/L"03-new-background-covered-wgc.bmp",background);
    auto coverCheckCut=captureTimeNow();redraw(windows.cover);
    auto unchanged=receive(coverCapture,[&](const c::Frame&f){return f.systemRelativeTime>coverCheckCut&&f.systemRelativeTime>background.systemRelativeTime&&f.bgra==waiting.bgra;},coverCheckCut);save(out/L"04-still-frozen-wgc.bmp",unchanged);
    need(body(background)!=body(old)&&unchanged.bgra==waiting.bgra,"background changed while exact cover pixels retained");
    coverState.failed=true;auto failureCut=captureTimeNow();redraw(windows.cover);
    auto failure=receive(coverCapture,[&](const c::Frame&f){return f.systemRelativeTime>failureCut&&body(f)==body(old)&&f.bgra!=waiting.bgra;},failureCut);save(out/L"05-held-cover-wgc.bmp",failure);
    need(IsWindowVisible(windows.cover)!=FALSE,"failure did not automatically uncover");
    // Fixture-only explicit completion: the new backing HWND has already yielded
    // a verified new frame. No game readiness or input grant is manufactured.
    coverCapture.Stop();ShowWindow(windows.cover,SW_HIDE);need(!IsWindowVisible(windows.cover),"cover removed only on explicit completion");auto revealCut=captureTimeNow();redraw(windows.map);
    auto revealed=receive(mapCapture,[&](const c::Frame&f){return f.systemRelativeTime>revealCut&&f.systemRelativeTime>failure.systemRelativeTime&&f.bgra==background.bgra;},revealCut);save(out/L"06-revealed-new-map-wgc.bmp",revealed);
    c::Observation observation{};auto wrong=mapBinding;++wrong.processBirth;need(!c::InspectExplicitWindow(wrong,observation,hr),"old process birth rejected");wrong=mapBinding;++wrong.pid;need(!c::InspectExplicitWindow(wrong,observation,hr),"wrong process rejected");wrong=mapBinding;wrong.windowClass=L"foreign";need(!c::InspectExplicitWindow(wrong,observation,hr),"foreign class rejected");
    need(SetWindowPos(windows.map,nullptr,82,80,0,0,SWP_NOSIZE|SWP_NOZORDER|SWP_NOACTIVATE)!=FALSE,"move only own fixture");c::Frame refused;need(!mapCapture.Next(refused,100,hr),"geometry change invalidates capture binding");
    need(SetWindowPos(windows.map,nullptr,80,80,0,0,SWP_NOSIZE|SWP_NOZORDER|SWP_NOACTIVATE)!=FALSE,"restore only own fixture position");need(!mapCapture.Next(refused,100,hr)&&hr==RO_E_CLOSED,"geometry loss cannot automatically resume");mapCapture.Stop();
    need(mapState.activations==0&&coverState.activations==0,"fixture never activated");
    std::ofstream result(out/L"native-result.json");result<<"{\n\"result\":\"PASS\",\"backend\":\"Visible own HWNDs, native WM_PAINT, Windows Graphics Capture, D3D11 texture CPU readback\",\n"
        <<"\"own_visible_window_created\":true,\"own_compositor_frames_captured\":true,\"physical_monitor_unoccluded_proved\":false,\"window_activated\":false,\"external_window_access\":false,\"game_access\":false,\"game_input_gate\":false,\"input_injected\":false,\"exclusive_fullscreen_supported\":false,\n"
        <<"\"checks\":{\"cover_owner_is_fixture\":true,\"background_changed_under_cover\":true,\"whole_cover_byte_identical_after_background_change\":true,\"failed_map_body_retained\":true,\"failure_did_not_reveal\":true,\"new_background_captured_before_uncover\":true,\"revealed_frame_matches_new_background\":true,\"stale_window_birth_rejected\":true,\"foreign_pid_rejected\":true,\"foreign_class_rejected\":true,\"geometry_drift_rejected\":true},\n"
        <<"\"map_paints\":"<<mapState.paints<<",\"cover_paints\":"<<coverState.paints<<",\"dpi\":"<<mapCapture.InitialObservation().dpi<<",\n"
        <<"\"old_sha256\":\""<<sha(old.bgra)<<"\",\"waiting_sha256\":\""<<sha(waiting.bgra)<<"\",\"waiting_after_change_sha256\":\""<<sha(unchanged.bgra)<<"\",\"background_sha256\":\""<<sha(background.bgra)<<"\",\"revealed_sha256\":\""<<sha(revealed.bgra)<<"\",\n"
        <<"\"capture_times\":{\"old\":"<<old.systemRelativeTime<<",\"waiting\":"<<waiting.systemRelativeTime<<",\"background\":"<<background.systemRelativeTime<<",\"unchanged\":"<<unchanged.systemRelativeTime<<",\"failure\":"<<failure.systemRelativeTime<<",\"revealed\":"<<revealed.systemRelativeTime<<"},\n"
        <<"\"minimum_frame_times\":{\"background\":"<<backgroundCut<<",\"unchanged\":"<<coverCheckCut<<",\"failure\":"<<failureCut<<",\"revealed\":"<<revealCut<<"},\n"
        <<"\"scope\":\"Visible borderless synthetic fixture only; capture is of each own HWND, never desktop or SAN14. WGC frames do not prove final monitor visibility, native input interception, world identity or MapWaitGate readiness.\"\n}\n";
    std::cout<<"PASS own visible WGC windows; no game access\n";return 0;
}catch(const winrt::hresult_error&e){std::cerr<<"WinRT "<<hexhr(e.code())<<"\n";if(!out.empty()){std::ofstream f(out/L"native-result.json");f<<"{\"result\":\"FAIL\",\"hresult\":\""<<hexhr(e.code())<<"\",\"game_access\":false}\n";}return 2;}
catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<"\n";if(!out.empty()){std::ofstream f(out/L"native-result.json");f<<"{\"result\":\"FAIL\",\"game_access\":false}\n";}return 1;}}

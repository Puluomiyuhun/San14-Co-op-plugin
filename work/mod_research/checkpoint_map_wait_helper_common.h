#pragma once
#define UNICODE
#define _UNICODE
#include "checkpoint_map_cover_capture.h"
#include "native_storage_read_core.h"
#include <winrt/Windows.Data.Json.h>
#include <winrt/Windows.Foundation.h>
#include <dwmapi.h>
#include <bcrypt.h>
#include <atomic>
#include <deque>
#include <mutex>
#include <thread>
#include <iostream>
#include <algorithm>
#include <cstring>
#include <cerrno>
#pragma comment(lib,"user32.lib")
#pragma comment(lib,"gdi32.lib")
#pragma comment(lib,"dwmapi.lib")
namespace map_wait {
namespace visual=checkpoint_map_cover;
using winrt::Windows::Data::Json::JsonObject;
using winrt::Windows::Data::Json::JsonValue;
inline void need(bool okay,const char*message){if(!okay)throw std::runtime_error(message);}
inline void string(JsonObject&o,const wchar_t*key,const std::wstring&value){o.SetNamedValue(key,JsonValue::CreateStringValue(value));}
inline void string(JsonObject&o,const wchar_t*key,const std::string&value){o.SetNamedValue(key,JsonValue::CreateStringValue(winrt::to_hstring(value)));}
inline void flag(JsonObject&o,const wchar_t*key,bool value){o.SetNamedValue(key,JsonValue::CreateBooleanValue(value));}
inline void integer(JsonObject&o,const wchar_t*key,std::uint64_t value){string(o,key,std::to_string(value));}
inline void emit(const JsonObject&o){std::cout<<winrt::to_string(o.Stringify())<<'\n'<<std::flush;}
inline std::string str(const JsonObject&o,const wchar_t*key){return winrt::to_string(o.GetNamedString(key));}
inline bool hex32(const std::string&s){return s.size()==32&&std::all_of(s.begin(),s.end(),[](char c){return(c>='0'&&c<='9')||(c>='a'&&c<='f');});}
inline std::uint64_t number(const std::string&s){char*end=nullptr;errno=0;auto n=std::strtoull(s.c_str(),&end,0);need(!s.empty()&&s[0]!='-'&&!errno&&end&&!*end,"bad integer binding");return n;}
inline std::string randomId(){unsigned char bytes[16]{};need(BCryptGenRandom(nullptr,bytes,sizeof bytes,BCRYPT_USE_SYSTEM_PREFERRED_RNG)>=0,"random identifier");std::string out;const char*hex="0123456789abcdef";for(auto byte:bytes){out+=hex[byte>>4];out+=hex[byte&15];}return out;}
inline std::string digest(const std::vector<unsigned char>&bytes){unsigned char hash[32]{};need(native_storage_read::Sha256(bytes.data(),bytes.size(),hash),"pixel digest");std::string out;const char*hex="0123456789abcdef";for(auto byte:hash){out+=hex[byte>>4];out+=hex[byte&15];}return out;}
inline std::uint64_t birth(){FILETIME created{},exit{},kernel{},user{};need(GetProcessTimes(GetCurrentProcess(),&created,&exit,&kernel,&user)!=FALSE,"own process birth");return(std::uint64_t(created.dwHighDateTime)<<32)|created.dwLowDateTime;}
inline std::int64_t clock100ns(){LARGE_INTEGER q{},f{};need(QueryPerformanceCounter(&q)&&QueryPerformanceFrequency(&f)&&f.QuadPart>0,"QPC");return(q.QuadPart/f.QuadPart)*10000000+(q.QuadPart%f.QuadPart)*10000000/f.QuadPart;}
inline bool sameRect(const RECT&a,const RECT&b){return a.left==b.left&&a.top==b.top&&a.right==b.right&&a.bottom==b.bottom;}
inline void pump(){MSG msg{};while(PeekMessageW(&msg,nullptr,0,0,PM_REMOVE)){TranslateMessage(&msg);DispatchMessageW(&msg);}}
struct Reader {
    std::mutex mutex;std::deque<std::string>lines;std::atomic<bool>done{false},stopping{false};std::thread thread;
    Reader():thread([this]{std::string line;char value;DWORD got=0;while(!stopping){if(!ReadFile(GetStdHandle(STD_INPUT_HANDLE),&value,1,&got,nullptr)||!got)break;if(value=='\n'){if(!line.empty()&&line.back()=='\r')line.pop_back();std::lock_guard<std::mutex>lock(mutex);lines.push_back(line);line.clear();}else{line+=value;if(line.size()>65536)break;}}done=true;}){}
    bool next(std::string&line){std::lock_guard<std::mutex>lock(mutex);if(lines.empty())return false;line=std::move(lines.front());lines.pop_front();return true;}
    ~Reader(){stopping=true;CancelSynchronousIo(thread.native_handle());if(thread.joinable())thread.join();}
};
struct Paint {
    const visual::Frame*frame=nullptr;std::wstring message;bool failure=false,destroyed=false;unsigned paints=0,activations=0;
};
inline LRESULT CALLBACK surfaceProc(HWND hwnd,UINT msg,WPARAM wp,LPARAM lp){
    if(msg==WM_NCCREATE){auto*cs=reinterpret_cast<CREATESTRUCTW*>(lp);SetWindowLongPtrW(hwnd,GWLP_USERDATA,reinterpret_cast<LONG_PTR>(cs->lpCreateParams));return TRUE;}
    auto*p=reinterpret_cast<Paint*>(GetWindowLongPtrW(hwnd,GWLP_USERDATA));
    if(p&&msg==WM_PAINT){PAINTSTRUCT ps{};auto dc=BeginPaint(hwnd,&ps);if(p->frame){auto&f=*p->frame;BITMAPINFO bi{};bi.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);bi.bmiHeader.biWidth=f.width;bi.bmiHeader.biHeight=-LONG(f.height);bi.bmiHeader.biPlanes=1;bi.bmiHeader.biBitCount=32;bi.bmiHeader.biCompression=BI_RGB;StretchDIBits(dc,0,0,f.width,f.height,0,0,f.width,f.height,f.bgra.data(),&bi,DIB_RGB_COLORS,SRCCOPY);
        if(!p->message.empty()){RECT band{0,LONG(f.height)-64,LONG(f.width),LONG(f.height)};auto brush=CreateSolidBrush(p->failure?RGB(104,32,40):RGB(26,33,48));FillRect(dc,&band,brush);DeleteObject(brush);SetBkMode(dc,TRANSPARENT);SetTextColor(dc,RGB(245,245,245));band.left=14;band.top+=10;band.right-=14;DrawTextW(dc,p->message.c_str(),int(p->message.size()),&band,DT_LEFT|DT_WORDBREAK|DT_NOPREFIX);}}
        ++p->paints;EndPaint(hwnd,&ps);return 0;}
    if(p&&msg==WM_ACTIVATE&&LOWORD(wp)!=WA_INACTIVE)++p->activations;
    if(p&&msg==WM_DESTROY)p->destroyed=true;
    if(msg==WM_MOUSEACTIVATE)return MA_NOACTIVATE;
    if(msg==WM_ERASEBKGND||msg==WM_CLOSE)return 0;
    return DefWindowProcW(hwnd,msg,wp,lp);
}
inline void redraw(HWND window){need(IsWindow(window)&&RedrawWindow(window,nullptr,nullptr,RDW_INVALIDATE|RDW_UPDATENOW)!=FALSE,"own cover paint failed");need(SUCCEEDED(DwmFlush()),"DWM flush failed");}
inline visual::Frame crop(const visual::Frame&source,const visual::Observation&o){
    auto&r=o.compositorFrameScreen;auto&c=o.clientScreen;need(source.width==unsigned(r.right-r.left)&&source.height==unsigned(r.bottom-r.top),"WGC/DWM bounds mismatch");
    int x=c.left-r.left,y=c.top-r.top,w=c.right-c.left,h=c.bottom-c.top;need(x>=0&&y>=0&&w>=200&&h>=160&&x+w<=int(source.width)&&y+h<=int(source.height),"client bounds unsupported");
    visual::Frame out;out.width=w;out.height=h;out.serial=source.serial;out.systemRelativeTime=source.systemRelativeTime;out.bgra.resize(std::size_t(w)*h*4);
    for(int row=0;row<h;++row)std::memcpy(out.bgra.data()+std::size_t(row)*w*4,source.bgra.data()+(std::size_t(row+y)*source.width+x)*4,std::size_t(w)*4);return out;
}
}

// Isolated hidden HWND and private DIBs only. Never enumerates, captures, hooks,
// reparents or sends messages to any external window/process. This proves native
// GDI drawing to the fixture's own offscreen target, NOT user-visible presentation.
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>

constexpr int W=400, H=240, BAND=196;
struct Canvas {
    HDC dc=nullptr; HBITMAP bmp=nullptr; HGDIOBJ previous=nullptr; uint32_t* pixels=nullptr;
    bool Init() {
        dc=CreateCompatibleDC(nullptr); if(!dc) return false;
        BITMAPINFO bi{}; bi.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);
        bi.bmiHeader.biWidth=W; bi.bmiHeader.biHeight=-H; bi.bmiHeader.biPlanes=1;
        bi.bmiHeader.biBitCount=32; bi.bmiHeader.biCompression=BI_RGB;
        bmp=CreateDIBSection(dc,&bi,DIB_RGB_COLORS,reinterpret_cast<void**>(&pixels),nullptr,0);
        if(!bmp || !pixels) return false;
        previous=SelectObject(dc,bmp); return previous && previous!=HGDI_ERROR;
    }
    ~Canvas(){if(dc && previous && previous!=HGDI_ERROR) SelectObject(dc,previous);
        if(bmp) DeleteObject(bmp); if(dc) DeleteDC(dc);}
    bool CopyFrom(const Canvas& other){return dc && other.dc && BitBlt(dc,0,0,W,H,other.dc,0,0,SRCCOPY);}
    bool Save(const char* path) const {
        BITMAPFILEHEADER fh{}; fh.bfType=0x4d42;
        fh.bfOffBits=sizeof(fh)+sizeof(BITMAPINFOHEADER); fh.bfSize=fh.bfOffBits+W*H*4;
        BITMAPINFOHEADER bi{};bi.biSize=sizeof(bi);bi.biWidth=W;bi.biHeight=-H;
        bi.biPlanes=1;bi.biBitCount=32;bi.biCompression=BI_RGB;bi.biSizeImage=W*H*4;
        std::ofstream f(path,std::ios::binary);f.write(reinterpret_cast<char*>(&fh),sizeof(fh));
        f.write(reinterpret_cast<char*>(&bi),sizeof(bi));
        f.write(reinterpret_cast<const char*>(pixels),W*H*4);return bool(f);
    }
};
bool Fill(HDC dc,RECT r,COLORREF color){HBRUSH b=CreateSolidBrush(color);if(!b)return false;
    bool ok=FillRect(dc,&r,b)!=0;DeleteObject(b);return ok;}
bool World(Canvas& c,bool newer){
    if(!Fill(c.dc,{0,0,W,H},newer?RGB(27,67,105):RGB(35,87,50)))return false;
    for(int x=20;x<W;x+=40) if(!Fill(c.dc,{x,0,x+1,H},RGB(90,116,110)))return false;
    for(int y=20;y<H;y+=40) if(!Fill(c.dc,{0,y,W,y+1},RGB(90,116,110)))return false;
    if(!Fill(c.dc,{45,55,90,92},RGB(207,190,125)))return false;
    if(!Fill(c.dc,newer?RECT{245,80,290,117}:RECT{150,110,195,147},RGB(199,109,77)))return false;
    SetBkMode(c.dc,TRANSPARENT);SetTextColor(c.dc,RGB(255,255,255));
    const wchar_t* label=newer?L"NEW FIXTURE WORLD - not SAN14":L"OLD FIXTURE WORLD - not SAN14";
    return TextOutW(c.dc,14,12,label,lstrlenW(label))!=0;
}
struct Fixture {
    Canvas world,frozen; bool covered=false,inputHeld=false,failed=false;
    int blockedInputs=0,commands=0,recovery=0,paintCount=0;
    bool Draw(HDC target){
        if(!target)return false;
        HDC source=covered?frozen.dc:world.dc;
        if(!source || !BitBlt(target,0,0,W,H,source,0,0,SRCCOPY))return false;
        if(covered){
            if(!Fill(target,{0,BAND,W,H},failed?RGB(94,32,38):RGB(25,30,42)))return false;
            SetTextColor(target,RGB(255,255,255));SetBkMode(target,TRANSPARENT);
            const wchar_t* text=failed?L"SYNC HELD - recovery available":L"SYNC WAIT - input blocked";
            if(!TextOutW(target,12,BAND+12,text,lstrlenW(text)))return false;
        }
        ++paintCount;return true;
    }
};
LRESULT CALLBACK WindowProc(HWND hwnd,UINT msg,WPARAM wp,LPARAM lp){
    auto* f=reinterpret_cast<Fixture*>(GetWindowLongPtrW(hwnd,GWLP_USERDATA));
    if(msg==WM_NCCREATE){auto* cs=reinterpret_cast<CREATESTRUCTW*>(lp);
        SetWindowLongPtrW(hwnd,GWLP_USERDATA,reinterpret_cast<LONG_PTR>(cs->lpCreateParams));return TRUE;}
    if(f && msg==WM_PRINTCLIENT)return f->Draw(reinterpret_cast<HDC>(wp))?1:0;
    if(f && msg==WM_PAINT){PAINTSTRUCT p{};HDC dc=BeginPaint(hwnd,&p);f->Draw(dc);EndPaint(hwnd,&p);return 0;}
    if(f && (msg==WM_LBUTTONDOWN || msg==WM_KEYDOWN)){
        if(f->inputHeld)++f->blockedInputs;else ++f->commands;return 0;}
    if(f && msg==WM_APP+1){if(f->failed && f->inputHeld)++f->recovery;return 0;}
    return DefWindowProcW(hwnd,msg,wp,lp);
}
int main(){
    Fixture f;Canvas old,waiting,changed,failed,revealed;
    bool pass=true;int checks=0;
    auto Check=[&](bool ok,const char* what){++checks;if(!ok){pass=false;std::cerr<<"FAIL "<<what<<"\n";}};
    if(!f.world.Init()||!f.frozen.Init()||!old.Init()||!waiting.Init()||!changed.Init()||!failed.Init()||!revealed.Init()){
        std::cerr<<"DIB initialization failed\n";return 2;}
    HINSTANCE instance=GetModuleHandleW(nullptr);
    WNDCLASSW wc{};wc.hInstance=instance;wc.lpfnWndProc=WindowProc;
    wc.lpszClassName=L"TransitionVisualIsolatedFixture";
    if(!RegisterClassW(&wc))return 3;
    RECT bounds{0,0,W,H};AdjustWindowRect(&bounds,WS_OVERLAPPEDWINDOW,FALSE);
    HWND hwnd=CreateWindowExW(0,wc.lpszClassName,L"Isolated visual fixture - not SAN14",WS_OVERLAPPEDWINDOW,
        0,0,bounds.right-bounds.left,bounds.bottom-bounds.top,nullptr,nullptr,instance,&f);
    if(!hwnd){UnregisterClassW(wc.lpszClassName,instance);return 4;}
    // Deliberately no ShowWindow: WM_PRINTCLIENT paints only our supplied private DC.
    Check(IsWindow(hwnd)&&!IsWindowVisible(hwnd),"own hidden HWND");
    Check(World(f.world,false)&&SendMessageW(hwnd,WM_PRINTCLIENT,reinterpret_cast<WPARAM>(old.dc),0)==1,"old native GDI paint");
    Check(f.frozen.CopyFrom(old),"own pixels copied before transition");
    f.covered=true;f.inputHeld=true;
    Check(SendMessageW(hwnd,WM_PRINTCLIENT,reinterpret_cast<WPARAM>(waiting.dc),0)==1,"frozen cover rendered");
    Check(World(f.world,true)&&SendMessageW(hwnd,WM_PRINTCLIENT,reinterpret_cast<WPARAM>(changed.dc),0)==1,"background replaced while covered");
    Check(std::memcmp(waiting.pixels,changed.pixels,W*H*4)==0,"cover unchanged while background differs");
    Check(std::memcmp(old.pixels,changed.pixels,W*BAND*4)==0,"old map body retained exactly");
    SendMessageW(hwnd,WM_KEYDOWN,'A',0);SendMessageW(hwnd,WM_LBUTTONDOWN,0,0);
    Check(f.commands==0&&f.blockedInputs==2,"own fixture gameplay messages blocked");
    Check(SendMessageW(hwnd,WM_PRINTCLIENT,0,0)==0,"invalid target returns render failure");
    f.failed=true;
    Check(SendMessageW(hwnd,WM_PRINTCLIENT,reinterpret_cast<WPARAM>(failed.dc),0)==1,"failure message drawn");
    SendMessageW(hwnd,WM_APP+1,0,0);SendMessageW(hwnd,WM_KEYDOWN,'B',0);
    Check(f.commands==0&&f.blockedInputs==3&&f.recovery==1&&f.inputHeld,"failure preserves input hold and recovery");
    // Explicit fixture-only recovery authorization; no automatic timeout/retry.
    f.failed=false;f.covered=false;
    Check(SendMessageW(hwnd,WM_PRINTCLIENT,reinterpret_cast<WPARAM>(revealed.dc),0)==1&&
        std::memcmp(revealed.pixels,f.world.pixels,W*H*4)==0,"new native frame rendered before gate release");
    f.inputHeld=false;SendMessageW(hwnd,WM_KEYDOWN,'C',0);
    Check(f.commands==1,"own input resumed after render acknowledgement");
    Check(old.Save("transition_visual_fixture_old.bmp")&&changed.Save("transition_visual_fixture_wait.bmp")&&
        failed.Save("transition_visual_fixture_fail.bmp")&&revealed.Save("transition_visual_fixture_new.bmp"),"write own fixture evidence");
    DestroyWindow(hwnd);UnregisterClassW(wc.lpszClassName,instance);
    std::ofstream result("transition_visual_win32_results.json");
    result<<"{\n  \"passed\": "<<(pass?"true":"false")<<",\n  \"checks\": "<<checks
          <<",\n  \"paint_count\": "<<f.paintCount<<",\n  \"backend\": \"Win32 GDI WM_PRINTCLIENT on own hidden fixture HWND and private DIBs\","
          <<"\n  \"presentation_outcome\": \"RENDERED_OFFSCREEN\",\n  \"visible_presentation_proved\": false,"
          <<"\n  \"external_window_access\": false,\n  \"real_game_access\": false,\n  \"game_input_intercepted\": false,"
          <<"\n  \"exclusive_fullscreen_supported\": false\n}\n";
    std::cout<<"checks="<<checks<<" pass="<<pass<<" offscreen_native_GDI=true visible_presentation_proved=false\n";
    return pass?0:1;
}

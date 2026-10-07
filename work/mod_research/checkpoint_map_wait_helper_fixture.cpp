#include "checkpoint_map_wait_helper_common.h"
using namespace map_wait;
void world(visual::Frame&frame,bool newer){frame.width=640;frame.height=360;frame.bgra.resize(640*360*4);for(unsigned y=0;y<360;++y)for(unsigned x=0;x<640;++x){auto p=frame.bgra.data()+(y*640+x)*4;p[0]=newer?107:51;p[1]=newer?66:86;p[2]=newer?26:34;p[3]=255;if(x%48==24||y%48==24){p[0]=102;p[1]=112;p[2]=76;}bool object=(x>=60&&x<125&&y>=80&&y<128)||(newer?(x>=438&&x<493&&y>=142&&y<190):(x>=230&&x<285&&y>=184&&y<232));if(object){p[0]=74;p[1]=107;p[2]=203;}}}
int main(){HWND window=nullptr;try{
    SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);winrt::init_apartment(winrt::apartment_type::multi_threaded);WNDCLASSW cls{};cls.hInstance=GetModuleHandleW(nullptr);cls.lpfnWndProc=surfaceProc;cls.lpszClassName=L"CheckpointMapWaitHelperFixture";need(RegisterClassW(&cls)!=0,"own target class");visual::Frame frame;world(frame,false);Paint paint;paint.frame=&frame;
    window=CreateWindowExW(WS_EX_NOACTIVATE|WS_EX_APPWINDOW,cls.lpszClassName,L"Own persistent map fixture - not SAN14",WS_POPUP,100,100,640,360,nullptr,nullptr,cls.hInstance,&paint);need(window!=nullptr,"own target window");ShowWindow(window,SW_SHOWNOACTIVATE);redraw(window);Reader reader;
    JsonObject ready;string(ready,L"event",std::string("FIXTURE_READY"));integer(ready,L"hwnd",std::uintptr_t(window));integer(ready,L"pid",GetCurrentProcessId());integer(ready,L"birth",birth());string(ready,L"class",std::wstring(cls.lpszClassName));flag(ready,L"game_access",false);emit(ready);
    bool exit=false,refresh=true;auto lastPaint=GetTickCount64();while(!exit){pump();std::string line;if(reader.next(line)){auto request=JsonObject::Parse(winrt::to_hstring(line));auto op=str(request,L"op");JsonObject reply;string(reply,L"id",str(request,L"id"));flag(reply,L"ok",true);
        if(op=="world"){need(window&&IsWindow(window),"target destroyed");world(frame,request.GetNamedNumber(L"revision")!=0);redraw(window);string(reply,L"pixel_sha256",digest(frame.bgra));}
        else if(op=="move"){need(SetWindowPos(window,nullptr,102,100,0,0,SWP_NOSIZE|SWP_NOZORDER|SWP_NOACTIVATE)!=FALSE,"move own target");}
        else if(op=="destroy"){DestroyWindow(window);window=nullptr;}
        else if(op=="refresh"){refresh=request.GetNamedBoolean(L"enabled");}
        else if(op=="quit")exit=true;
        else throw std::runtime_error("unknown fixture operation");integer(reply,L"activations",paint.activations);emit(reply);
    }
        if(window&&refresh&&GetTickCount64()-lastPaint>=80){redraw(window);lastPaint=GetTickCount64();}if(reader.done)exit=true;Sleep(10);
    }
    if(window)DestroyWindow(window);return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';if(window)DestroyWindow(window);return 1;}catch(...){if(window)DestroyWindow(window);return 2;}}

#include "checkpoint_map_cover_capture.h"
#include <d3d11.h>
#include <dxgi1_2.h>
#include <dwmapi.h>
#include <windows.graphics.capture.interop.h>
#include <windows.graphics.directx.direct3d11.interop.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Graphics.Capture.h>
#include <winrt/Windows.Graphics.DirectX.h>
#include <winrt/Windows.Graphics.DirectX.Direct3D11.h>
#include <cstring>
#include <atomic>
#pragma comment(lib,"d3d11.lib")
#pragma comment(lib,"dxgi.lib")
#pragma comment(lib,"dwmapi.lib")
#pragma comment(lib,"windowsapp.lib")
#pragma comment(lib,"user32.lib")
namespace checkpoint_map_cover {
using namespace winrt::Windows::Graphics::Capture;
using namespace winrt::Windows::Graphics::DirectX;
using winrt::Windows::Graphics::DirectX::Direct3D11::IDirect3DDevice;
static bool sameRect(const RECT&a,const RECT&b){return a.left==b.left&&a.top==b.top&&a.right==b.right&&a.bottom==b.bottom;}
bool InspectExplicitWindow(const Binding&expected,Observation&out,HRESULT&error) noexcept {
    out={};error=E_INVALIDARG;
    if(!expected.window||!expected.pid||!expected.processBirth||expected.windowClass.empty()||expected.windowClass.size()>255||!IsWindow(expected.window))return false;
    DWORD pid=0;auto tid=GetWindowThreadProcessId(expected.window,&pid);wchar_t className[256]{};
    if(!tid||pid!=expected.pid||!GetClassNameW(expected.window,className,256)||expected.windowClass!=className)return false;
    HANDLE process=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION,FALSE,pid);if(!process){error=HRESULT_FROM_WIN32(GetLastError());return false;}
    FILETIME birth{},exit{},kernel{},user{};bool timeOkay=GetProcessTimes(process,&birth,&exit,&kernel,&user)!=FALSE;CloseHandle(process);
    std::uint64_t stamp=(std::uint64_t(birth.dwHighDateTime)<<32)|birth.dwLowDateTime;
    if(!timeOkay||stamp!=expected.processBirth)return false;
    out.identity=expected;out.windowThread=tid;out.dpi=GetDpiForWindow(expected.window);
    out.style=GetWindowLongPtrW(expected.window,GWL_STYLE);out.extendedStyle=GetWindowLongPtrW(expected.window,GWL_EXSTYLE);
    RECT client{};POINT position{};DWORD cloaked=0;
    if(!GetClientRect(expected.window,&client)||!ClientToScreen(expected.window,&position)||!GetWindowRect(expected.window,&out.windowScreen))return false;
    out.clientScreen={position.x,position.y,position.x+client.right,position.y+client.bottom};
    error=DwmGetWindowAttribute(expected.window,DWMWA_CLOAKED,&cloaked,sizeof cloaked);if(FAILED(error))return false;
    error=DwmGetWindowAttribute(expected.window,DWMWA_EXTENDED_FRAME_BOUNDS,&out.compositorFrameScreen,sizeof(RECT));if(FAILED(error))return false;
    out.visible=IsWindowVisible(expected.window)!=FALSE;out.minimized=IsIconic(expected.window)!=FALSE;out.cloaked=cloaked!=0;
    DWORD finalPid=0;auto finalThread=GetWindowThreadProcessId(expected.window,&finalPid);
    if(finalPid!=pid||finalThread!=tid||!out.dpi||!out.visible||out.minimized||out.cloaked){error=E_UNEXPECTED;return false;}
    error=S_OK;return true;
}
struct Capture::Impl {
    Observation initial{};
    winrt::com_ptr<ID3D11Device> device;
    winrt::com_ptr<ID3D11DeviceContext> context;
    GraphicsCaptureItem item{nullptr};
    Direct3D11CaptureFramePool pool{nullptr};
    GraphicsCaptureSession session{nullptr};
    std::uint64_t serial=0;std::int64_t lastTime=-1;
    const char*stage="new";
    std::shared_ptr<std::atomic<bool>> closed=std::make_shared<std::atomic<bool>>(false);
    winrt::event_token closedToken{};bool closedSubscribed=false;
};
Capture::Capture():impl_(std::make_unique<Impl>()){}
Capture::~Capture(){Stop();}
const Observation& Capture::InitialObservation()const noexcept{return impl_->initial;}
const char* Capture::LastStage()const noexcept{return impl_->stage;}
void Capture::Stop()noexcept{try{if(impl_->closedSubscribed&&impl_->item)impl_->item.Closed(impl_->closedToken);}catch(...){}impl_->closedSubscribed=false;impl_->closed->store(true);try{if(impl_->session)impl_->session.Close();}catch(...){}try{if(impl_->pool)impl_->pool.Close();}catch(...){}impl_->session=nullptr;impl_->pool=nullptr;impl_->item=nullptr;impl_->context=nullptr;impl_->device=nullptr;}
bool Capture::Start(const Binding&binding,HRESULT&error)noexcept{
    if(impl_->session){error=E_UNEXPECTED;return false;}
    try{
        impl_->stage="inspect_window";if(!InspectExplicitWindow(binding,impl_->initial,error))return false;
        impl_->stage="wgc_supported";
        if(!GraphicsCaptureSession::IsSupported()){error=E_NOTIMPL;return false;}
        D3D_FEATURE_LEVEL level{};
        impl_->stage="d3d11_create";winrt::check_hresult(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_HARDWARE,nullptr,D3D11_CREATE_DEVICE_BGRA_SUPPORT,nullptr,0,D3D11_SDK_VERSION,impl_->device.put(),&level,impl_->context.put()));
        auto dxgi=impl_->device.as<IDXGIDevice>();winrt::com_ptr<::IInspectable> inspectable;
        impl_->stage="winrt_device";winrt::check_hresult(CreateDirect3D11DeviceFromDXGIDevice(dxgi.get(),inspectable.put()));auto device=inspectable.as<IDirect3DDevice>();
        auto interop=winrt::get_activation_factory<GraphicsCaptureItem,IGraphicsCaptureItemInterop>();
        impl_->stage="capture_for_window";winrt::check_hresult(interop->CreateForWindow(binding.window,winrt::guid_of<GraphicsCaptureItem>(),winrt::put_abi(impl_->item)));
        impl_->closed=std::make_shared<std::atomic<bool>>(false);auto closed=impl_->closed;
        impl_->closedToken=impl_->item.Closed([closed](auto const&,auto const&){closed->store(true);});impl_->closedSubscribed=true;
        auto size=impl_->item.Size();if(size.Width<1||size.Height<1||size.Width>8192||size.Height>8192){error=E_INVALIDARG;Stop();return false;}
        impl_->stage="capture_frame_pool";impl_->pool=Direct3D11CaptureFramePool::CreateFreeThreaded(device,DirectXPixelFormat::B8G8R8A8UIntNormalized,2,size);
        impl_->stage="capture_session";impl_->session=impl_->pool.CreateCaptureSession(impl_->item);impl_->session.IsCursorCaptureEnabled(false);
        impl_->stage="start_capture";impl_->session.StartCapture();impl_->stage="capturing";error=S_OK;return true;
    }catch(const winrt::hresult_error&e){error=e.code();Stop();return false;}catch(...){error=E_FAIL;Stop();return false;}
}
bool Capture::Next(Frame&out,DWORD timeout,HRESULT&error,std::int64_t notBefore)noexcept{
    out={};error=E_INVALIDARG;if(!impl_->pool||!timeout||timeout>10000)return false;
    try{
        const auto deadline=GetTickCount64()+timeout;
        while(GetTickCount64()<deadline){
            if(impl_->closed->load()){error=RO_E_CLOSED;return false;}
            Observation now{};if(!InspectExplicitWindow(impl_->initial.identity,now,error)){impl_->closed->store(true);return false;}
            if(now.dpi!=impl_->initial.dpi||now.windowThread!=impl_->initial.windowThread||now.style!=impl_->initial.style||now.extendedStyle!=impl_->initial.extendedStyle||!sameRect(now.clientScreen,impl_->initial.clientScreen)||!sameRect(now.windowScreen,impl_->initial.windowScreen)||!sameRect(now.compositorFrameScreen,impl_->initial.compositorFrameScreen)){impl_->closed->store(true);error=E_UNEXPECTED;return false;}
            auto frame=impl_->pool.TryGetNextFrame();
            if(frame){
                auto time=frame.SystemRelativeTime().count();auto size=frame.ContentSize();
                if(time<=impl_->lastTime||time<=notBefore){frame.Close();continue;}
                if(size.Width<1||size.Height<1||size.Width>8192||size.Height>8192){error=E_UNEXPECTED;return false;}
                auto access=frame.Surface().as<::Windows::Graphics::DirectX::Direct3D11::IDirect3DDxgiInterfaceAccess>();winrt::com_ptr<ID3D11Texture2D> texture;
                winrt::check_hresult(access->GetInterface(__uuidof(ID3D11Texture2D),texture.put_void()));
                D3D11_TEXTURE2D_DESC desc{};texture->GetDesc(&desc);
                if(desc.Format!=DXGI_FORMAT_B8G8R8A8_UNORM||unsigned(size.Width)>desc.Width||unsigned(size.Height)>desc.Height){error=E_UNEXPECTED;return false;}
                desc.Usage=D3D11_USAGE_STAGING;desc.BindFlags=0;desc.CPUAccessFlags=D3D11_CPU_ACCESS_READ;desc.MiscFlags=0;
                winrt::com_ptr<ID3D11Texture2D> staging;winrt::check_hresult(impl_->device->CreateTexture2D(&desc,nullptr,staging.put()));impl_->context->CopyResource(staging.get(),texture.get());
                out.width=unsigned(size.Width);out.height=unsigned(size.Height);out.bgra.resize(std::size_t(out.width)*out.height*4);
                D3D11_MAPPED_SUBRESOURCE mapped{};winrt::check_hresult(impl_->context->Map(staging.get(),0,D3D11_MAP_READ,0,&mapped));
                for(unsigned row=0;row<out.height;++row)std::memcpy(out.bgra.data()+std::size_t(row)*out.width*4,static_cast<unsigned char*>(mapped.pData)+std::size_t(row)*mapped.RowPitch,std::size_t(out.width)*4);
                impl_->context->Unmap(staging.get(),0);out.serial=++impl_->serial;out.systemRelativeTime=time;impl_->lastTime=time;frame.Close();
                Observation after{};if(impl_->closed->load()||!InspectExplicitWindow(impl_->initial.identity,after,error)||after.windowThread!=impl_->initial.windowThread||after.style!=impl_->initial.style||after.extendedStyle!=impl_->initial.extendedStyle||after.dpi!=impl_->initial.dpi||!sameRect(after.clientScreen,impl_->initial.clientScreen)||!sameRect(after.windowScreen,impl_->initial.windowScreen)||!sameRect(after.compositorFrameScreen,impl_->initial.compositorFrameScreen)){impl_->closed->store(true);out={};error=E_UNEXPECTED;return false;}
                error=S_OK;return true;
            }
            // Pump only this process/thread's own messages. No external HWND is
            // enumerated, messaged, focused, or used as a screenshot source.
            MSG message{};while(PeekMessageW(&message,nullptr,0,0,PM_REMOVE)){if(message.message==WM_QUIT){error=E_ABORT;return false;}TranslateMessage(&message);DispatchMessageW(&message);}Sleep(10);
        }
        error=HRESULT_FROM_WIN32(WAIT_TIMEOUT);return false;
    }catch(const winrt::hresult_error&e){error=e.code();return false;}catch(...){error=E_FAIL;return false;}
}
}

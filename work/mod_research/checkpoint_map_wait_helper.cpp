#include "checkpoint_map_wait_helper_common.h"
using namespace map_wait;
struct Helper {
    std::string phase="NEW",session,attachment,view,mode,surface=randomId(),oldFrameId,newFrameId,preparedToken,newAttachment,reason;
    DWORD idleMs=30000;ULONGLONG lastCommand=GetTickCount64();bool exit=false,eofHeld=false,invalidTarget=false,bindAttempted=false;
    visual::Binding target{};visual::Observation original{};visual::Capture targetCapture,coverCapture;
    visual::Frame frozen,prepared;HWND window=nullptr;Paint paint;
    ~Helper(){coverCapture.Stop();targetCapture.Stop();if(window&&IsWindow(window))DestroyWindow(window);}
    JsonObject status(const std::string&id,bool okay,const std::string&error=""){
        JsonObject o;string(o,L"id",id);string(o,L"session",session);flag(o,L"ok",okay);string(o,L"phase",phase);string(o,L"error",error);string(o,L"hold_reason",reason);string(o,L"surface",surface);
        flag(o,L"cover_window_visible",window&&IsWindow(window)&&IsWindowVisible(window));flag(o,L"old_pixels_retained",!frozen.bgra.empty());flag(o,L"target_binding_lost",invalidTarget);flag(o,L"input_gate_provided",false);flag(o,L"physical_monitor_unoccluded_proved",false);flag(o,L"native_load_requested",false);flag(o,L"gameplay_authorized",false);integer(o,L"helper_pid",GetCurrentProcessId());integer(o,L"helper_birth",birth());string(o,L"cover_class",std::string("CheckpointMapWaitHelper"));integer(o,L"cover_hwnd",std::uintptr_t(window));integer(o,L"cover_activations",paint.activations);return o;
    }
    bool stable(){if(phase=="NEW"||phase=="REVEALED")return true;if(invalidTarget)return false;visual::Observation now{};HRESULT hr{};
        bool okay=visual::InspectExplicitWindow(target,now,hr)&&now.windowThread==original.windowThread&&now.dpi==original.dpi&&now.style==original.style&&now.extendedStyle==original.extendedStyle&&sameRect(now.clientScreen,original.clientScreen)&&sameRect(now.windowScreen,original.windowScreen)&&sameRect(now.compositorFrameScreen,original.compositorFrameScreen);
        if(!okay)invalidTarget=true;return okay;
    }
    void hold(const std::string&why){if(phase=="NEW"||phase=="REVEALED")return;phase="HELD";reason=why;preparedToken.clear();newFrameId.clear();paint.frame=frozen.bgra.empty()?nullptr:&frozen;paint.message=winrt::to_hstring("SYNC HELD: "+why);paint.failure=true;
        if(window&&IsWindow(window))try{redraw(window);}catch(...){};
    }
    visual::Frame targetFrame(std::int64_t cutoff){need(stable(),"target binding changed");HRESULT hr{};visual::Frame frame;need(targetCapture.Next(frame,3000,hr,cutoff),"target frame unavailable");need(stable(),"target changed while capturing");return crop(frame,original);}
    visual::Frame verifyCover(const visual::Frame&expected,std::int64_t cutoff,bool band){HRESULT hr{};auto until=GetTickCount64()+3500;while(GetTickCount64()<until){visual::Frame frame;need(coverCapture.Next(frame,1000,hr,cutoff),"cover frame unavailable");if(frame.width!=expected.width||frame.height!=expected.height)throw std::runtime_error("cover capture size changed");auto bytes=std::size_t(expected.width)*(expected.height-(band?64:0))*4;if(std::memcmp(frame.bgra.data(),expected.bgra.data(),bytes)==0)return frame;}throw std::runtime_error("cover pixels not confirmed");}
    JsonObject command(const JsonObject&request){auto id=str(request,L"id"),op=str(request,L"op"),nonce=str(request,L"session");need(!id.empty()&&id.size()<=80&&hex32(nonce),"bad request identity");
        if(op=="stop"&&phase=="NEW"){session=nonce;exit=true;return status(id,true);}
        if(op=="bind"){
            need(phase=="NEW"&&!bindAttempted,"helper is single-use");bindAttempted=true;session=nonce;auto pid=request.GetNamedNumber(L"pid");need(pid>0&&pid<=MAXDWORD&&pid==DWORD(pid),"bad target PID");target={reinterpret_cast<HWND>(number(str(request,L"hwnd"))),DWORD(pid),number(str(request,L"birth")),request.GetNamedString(L"class").c_str()};
            attachment=str(request,L"attachment");view=str(request,L"view");mode=str(request,L"window_mode");need(hex32(attachment)&&hex32(view)&&(mode=="windowed"||mode=="borderless"),"bad attachment/view/mode");auto idle=request.GetNamedNumber(L"idle_timeout_ms");need(idle>=200&&idle<=600000&&idle==DWORD(idle),"bad timeout");idleMs=DWORD(idle);HRESULT hr{};
            need(visual::InspectExplicitWindow(target,original,hr),"target observation rejected");need(targetCapture.Start(target,hr),"WGC target start failed");phase="BOUND";lastCommand=GetTickCount64();return status(id,true);
        }
        need(nonce==session&&!session.empty(),"foreign session");lastCommand=GetTickCount64();
        if(op=="force_stop"){need(request.GetNamedBoolean(L"accept_cover_loss"),"explicit cover loss acknowledgement required");auto reply=status(id,true);flag(reply,L"cover_loss_explicit",true);exit=true;return reply;}
        if(op=="stop"){need(phase=="NEW"||phase=="BOUND"||phase=="REVEALED","stop would silently uncover an active hold");exit=true;return status(id,true);}
        if(op=="status"||op=="ping"){if(!stable())hold("TARGET_BINDING_LOST");return status(id,true);}
        if(op=="hold"){auto message=str(request,L"message");need(!message.empty()&&message.size()<=160,"bad hold message");hold(message);return status(id,true);}
        need(stable()&&phase!="HELD","terminal hold or target loss");
        if(op=="cover"){
            need(phase=="BOUND","cover out of order");phase="ARMING";frozen=targetFrame(clock100ns());oldFrameId=randomId();paint.frame=&frozen;paint.message=L"Synchronizing - old map retained; game input barrier is external";
            auto&r=original.clientScreen;window=CreateWindowExW(WS_EX_NOACTIVATE|WS_EX_APPWINDOW,L"CheckpointMapWaitHelper",L"Map synchronization wait",WS_POPUP,r.left,r.top,r.right-r.left,r.bottom-r.top,target.window,nullptr,GetModuleHandleW(nullptr),&paint);need(window!=nullptr,"cover creation failed");
            need(GetWindow(window,GW_OWNER)==target.window&&!(GetWindowLongPtrW(window,GWL_STYLE)&WS_CHILD),"cover owner relationship rejected");ShowWindow(window,SW_SHOWNOACTIVATE);redraw(window);
            auto until=GetTickCount64()+150;while(GetTickCount64()<until){pump();Sleep(10);}visual::Binding coverBinding{window,GetCurrentProcessId(),birth(),L"CheckpointMapWaitHelper"};HRESULT hr{};need(coverCapture.Start(coverBinding,hr),"WGC cover start failed");auto cut=clock100ns();redraw(window);auto shown=verifyCover(frozen,cut,true);need(stable(),"target changed before cover acknowledgement");phase="COVERED";
            auto reply=status(id,true);string(reply,L"old_attachment",attachment);string(reply,L"view",view);string(reply,L"old_frame",oldFrameId);string(reply,L"old_frame_sha256",digest(frozen.bgra));integer(reply,L"old_capture_time",frozen.systemRelativeTime);integer(reply,L"cover_capture_time",shown.systemRelativeTime);string(reply,L"cover_observation",std::string("OWN_WGC_FRAME_ONLY"));return reply;
        }
        if(op=="prepare"){
            need(phase=="COVERED","prepare out of order");newAttachment=str(request,L"new_attachment");need(hex32(newAttachment)&&newAttachment!=attachment&&str(request,L"view")==view,"new attachment/view rejected");auto after=number(str(request,L"after_time"));need(after<=INT64_MAX,"bad capture cutoff");auto cutoff=std::max<std::int64_t>(after,clock100ns());phase="PREPARING";prepared=targetFrame(cutoff);preparedToken=randomId();newFrameId=randomId();phase="PREPARED";
            auto reply=status(id,true);string(reply,L"new_attachment",newAttachment);string(reply,L"view",view);string(reply,L"prepared_token",preparedToken);string(reply,L"new_frame",newFrameId);string(reply,L"new_frame_sha256",digest(prepared.bgra));integer(reply,L"capture_time",prepared.systemRelativeTime);integer(reply,L"minimum_frame_time",cutoff);string(reply,L"world_attribution",std::string("CALLER_ASSERTION_ONLY"));return reply;
        }
        if(op=="reveal"){
            need(phase=="PREPARED"&&str(request,L"prepared_token")==preparedToken&&str(request,L"new_attachment")==newAttachment&&str(request,L"view")==view&&str(request,L"new_frame")==newFrameId&&hex32(str(request,L"controller_grant")),"reveal identity/grant mismatch");
            phase="REVEALING";auto cut=clock100ns();paint.frame=&prepared;paint.message.clear();paint.failure=false;redraw(window);auto shown=verifyCover(prepared,cut,false);need(stable(),"target changed before uncover");ShowWindow(window,SW_HIDE);need(SUCCEEDED(DwmFlush())&&!IsWindowVisible(window),"cover hide not confirmed");phase="REVEALED";coverCapture.Stop();targetCapture.Stop();
            auto reply=status(id,true);string(reply,L"new_attachment",newAttachment);string(reply,L"new_frame",newFrameId);string(reply,L"prepared_token",preparedToken);integer(reply,L"new_cover_capture_time",shown.systemRelativeTime);integer(reply,L"minimum_frame_time",cut);flag(reply,L"image_release_confirmed",true);return reply;
        }
        throw std::runtime_error("unknown operation");
    }
};
int main(){try{
    SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);winrt::init_apartment(winrt::apartment_type::multi_threaded);WNDCLASSW type{};type.hInstance=GetModuleHandleW(nullptr);type.lpfnWndProc=surfaceProc;type.lpszClassName=L"CheckpointMapWaitHelper";need(RegisterClassW(&type)!=0,"helper class");Reader reader;Helper helper;
    auto ready=helper.status("",true);string(ready,L"event",std::string("READY_NO_TARGET"));emit(ready);
    while(!helper.exit){pump();std::string line;if(reader.next(line)){
        std::string id;try{auto request=JsonObject::Parse(winrt::to_hstring(line));id=str(request,L"id");auto result=helper.command(request);emit(result);}
        catch(const std::exception&e){if(helper.phase=="ARMING"||helper.phase=="PREPARING"||helper.phase=="REVEALING")helper.hold("VISUAL_OPERATION_FAILED");else if(helper.phase!="NEW"&&helper.phase!="HELD"&&helper.phase!="REVEALED"&&!helper.stable())helper.hold("TARGET_BINDING_LOST");emit(helper.status(id,false,e.what()));}
        catch(const winrt::hresult_error&e){if(helper.phase=="ARMING"||helper.phase=="PREPARING"||helper.phase=="REVEALING")helper.hold("VISUAL_OPERATION_FAILED");emit(helper.status(id,false,winrt::to_string(e.message())));}
        catch(...){helper.hold("CONTROL_EXCEPTION");emit(helper.status(id,false,"control exception"));}
    }
        if(helper.phase!="NEW"&&helper.phase!="REVEALED"&&helper.phase!="HELD"){
            if(!helper.stable()){helper.hold("TARGET_BINDING_LOST");auto event=helper.status("",false);string(event,L"event",std::string("HELD"));emit(event);}
            else if(GetTickCount64()-helper.lastCommand>helper.idleMs){helper.hold("CONTROLLER_TIMEOUT");auto event=helper.status("",false);string(event,L"event",std::string("HELD"));emit(event);}
        }
        if(reader.done&&!helper.eofHeld){helper.eofHeld=true;if(helper.phase=="NEW"||helper.phase=="BOUND"||helper.phase=="REVEALED")helper.exit=true;else{helper.hold("CONTROLLER_EOF");auto event=helper.status("",false);string(event,L"event",std::string("HELD"));emit(event);}}
        Sleep(10);
    }
    return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"helper startup failure\n";return 2;}}

#include "checkpoint_target_storage_adapter.h"
#include <cstring>
#include <cwchar>

namespace checkpoint_target_storage {
namespace {
template<class T> T at(uintptr_t p){return *reinterpret_cast<const T*>(p);}
constexpr char Version[]="STEAMREMOTESTORAGE_INTERFACE_VERSION014";
bool imageMethod(uintptr_t address,bool pin){
    MEMORY_BASIC_INFORMATION m{};
    if(!address||VirtualQuery(reinterpret_cast<void*>(address),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||m.Type!=MEM_IMAGE||
       (m.Protect&(PAGE_GUARD|PAGE_NOACCESS)))return false;
    DWORD p=m.Protect&0xff;
    if(p!=PAGE_EXECUTE&&p!=PAGE_EXECUTE_READ&&p!=PAGE_EXECUTE_READWRITE&&p!=PAGE_EXECUTE_WRITECOPY)return false;
    HMODULE module=nullptr;
    if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
          reinterpret_cast<LPCWSTR>(address),&module)||module!=m.AllocationBase)return false;
#ifndef CHECKPOINT_TARGET_STORAGE_FIXTURE
    wchar_t path[32768]{};
    if(!GetModuleFileNameW(module,path,32768))return false;
    constexpr wchar_t Steam[]=L"C:\\Program Files (x86)\\Steam\\steamclient64.dll";
    constexpr wchar_t Api[]=L"C:\\Program Files (x86)\\Steam\\steamapps\\common\\Romance_of_the_Three_Kingdoms_14\\steam_api64.dll";
    if(_wcsicmp(path,Steam)&&_wcsicmp(path,Api))return false;
#endif
    if(pin){HMODULE pinned=nullptr;
        if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
              reinterpret_cast<LPCWSTR>(address),&pinned)||pinned!=module)return false;}
    return true;
}
}
bool Context::Open(uintptr_t base,CheckBoundary check,void* owner) noexcept {
    if(attempted_)return false;attempted_=true;
    try {
        base_=base;check_=check;owner_=owner;
        if(!base_||!check_||!check_(owner_))return false;
        if(std::memcmp(reinterpret_cast<void*>(base_+0x12AA6B8),Version,sizeof Version)||
           at<uintptr_t>(base_+0x18D08B8)!=base_+0x2FCB90)return false;
        contextInit_=at<uintptr_t>(base_+0x123CB28);
        if(!imageMethod(contextInit_,true))return false;
        using Init=void*(__cdecl*)(void*);
        ++contextCalls_;
        holder_=uintptr_t(reinterpret_cast<Init>(contextInit_)(reinterpret_cast<void*>(base_+0x18D08B8)));
        if(!holder_||(storage_=at<uintptr_t>(holder_))==0||(vtable_=at<uintptr_t>(storage_))==0)return false;
        api_.storage=reinterpret_cast<void*>(storage_);
        api_.exists=reinterpret_cast<native_storage_read::FileExists>(at<uintptr_t>(vtable_+0x68));
        api_.size=reinterpret_cast<native_storage_read::GetFileSize>(at<uintptr_t>(vtable_+0x78));
        api_.read=reinterpret_cast<native_storage_read::FileRead>(at<uintptr_t>(vtable_+8));
        if(!imageMethod(uintptr_t(api_.exists),true)||!imageMethod(uintptr_t(api_.size),true)||!imageMethod(uintptr_t(api_.read),true))return false;
        api_.validate=&Context::Validate;api_.validationContext=this;active_=true;
        if(!Valid()){active_=false;return false;}
        return true;
    }catch(...){active_=false;return false;}
}
bool Context::Valid() const noexcept {
    try {
        return active_&&check_&&check_(owner_)&&
            !std::memcmp(reinterpret_cast<void*>(base_+0x12AA6B8),Version,sizeof Version)&&
            at<uintptr_t>(base_+0x18D08B8)==base_+0x2FCB90&&at<uintptr_t>(base_+0x123CB28)==contextInit_&&
            at<uintptr_t>(holder_)==storage_&&at<uintptr_t>(storage_)==vtable_&&
            at<uintptr_t>(vtable_+0x68)==uintptr_t(api_.exists)&&at<uintptr_t>(vtable_+0x78)==uintptr_t(api_.size)&&
            at<uintptr_t>(vtable_+8)==uintptr_t(api_.read)&&imageMethod(contextInit_,false)&&
            imageMethod(uintptr_t(api_.exists),false)&&imageMethod(uintptr_t(api_.size),false)&&imageMethod(uintptr_t(api_.read),false);
    }catch(...){return false;}
}
bool Context::Validate(void* p) noexcept {return p&&static_cast<Context*>(p)->Valid();}
checkpoint_target_metadata::Presence Context::Presence(const char* name) noexcept {
    using Result=checkpoint_target_metadata::Presence;
    try {
        if(!name||!Valid())return Result::Unknown;
        ++presenceCalls_;
        bool exists=api_.exists(api_.storage,name);
        return Valid()?(exists?Result::Present:Result::Absent):Result::Unknown;
    }catch(...){return Result::Unknown;}
}
bool Context::SlotName(unsigned slot,char out[16]) noexcept {
    try {
        if(!out||slot<63||slot>109||!Valid())return false;
        using Format=const char*(__fastcall*)(unsigned,unsigned,unsigned);
        ++formatterCalls_;
        auto text=reinterpret_cast<Format>(base_+0x2F1650)(slot,0,0);
        if(!text)return false;
        // Copy the returned native temporary immediately; do not retain it.
        size_t length=0;for(;length<16&&text[length];++length){}
        if(length!=13||length>=16)return false;
        std::memset(out,0,16);std::memcpy(out,text,length);
        return Valid();
    }catch(...){return false;}
}
}

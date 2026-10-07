#include "checkpoint_dynamic_file_profile.h"
#include <cstring>
namespace checkpoint_dynamic_file_profile {
bool Validate(const Profile&p) noexcept {
    __try {
        if(p.slot!=SupportedSlot||!p.size||p.size>MaximumSize||memcmp(p.name,SupportedName,NameBytes))return false;
        for(size_t i=NameBytes;i<sizeof p.name;++i)if(p.name[i])return false;
        unsigned hash=0;for(auto b:p.sha256)hash|=b;return hash!=0;
    }__except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
bool Capture(const Profile*source,Profile&out) noexcept {
    __try {
        if(!source)return false;
        const Profile first=*source;MemoryBarrier();const Profile second=*source;
        if(memcmp(&first,&second,sizeof first)||!Validate(first))return false;
        out=first;return true;
    }__except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
bool Same(const Profile&a,const Profile&b) noexcept {
    __try {return Validate(a)&&Validate(b)&&!memcmp(&a,&b,sizeof a);}
    __except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
bool Equal(const Profile&a,const Profile&b) noexcept {return Same(a,b);}
}

"""One-time successor derivation. Frozen sources remain intact."""
from pathlib import Path
P=Path(__file__).resolve().parent
assert not (P/'checkpoint_dynamic_title_identity_adapter.h').exists()
for ext in ('h','cpp'):
 s=(P/f'checkpoint_title_identity_adapter.{ext}').read_text()
 for old,new in [('checkpoint_title_identity_adapter','checkpoint_dynamic_title_identity_adapter'),('checkpoint_cc_load_lifecycle','checkpoint_dynamic_cc_load_lifecycle'),('checkpoint_cc_load_observer','checkpoint_dynamic_cc_load_observer')]:s=s.replace(old,new)
 if ext=='h':
  s=s.replace('struct Config {','''// Identity is bound by the accepted host checkpoint and recipient assignment.
// Object pointers and opaque force+47 bytes are resolved only in the owned new
// Title callback, never imported from the previous client world.
struct Identity {std::uint16_t ruler=0;std::uint8_t force=0,district=0;};
struct WorldProfile {std::uint16_t year=0;std::uint8_t month=0,day=0;Identity source{},target{};};
bool ValidWorldProfile(const WorldProfile&) noexcept;
struct Config {
    const checkpoint_dynamic_file_profile::Profile* profile=nullptr;
    WorldProfile worldProfile{};''')
  s=s.replace('static_assert(sizeof(Report)==344);','')
  s=s.replace('unsigned char originalXmm0[16]{};', 'unsigned capturedSource47=0,capturedTarget47=0;\n    unsigned char originalXmm0[16]{};')
  s=s.replace('SRWLOCK lock=SRWLOCK_INIT;Config config{};', 'SRWLOCK lock=SRWLOCK_INIT;checkpoint_dynamic_file_profile::Profile profile{};Config config{};')
 else:
  s=s.replace('#include <cstring>','#include <cstring>\n#include "checkpoint_persistent_logical_adapter.h"')
  s=s.replace('CheckpointLoadWorkerCurrentOwner','checkpoint_persistent_logical_adapter::CurrentOwner').replace('CheckpointLoadWorkerClaim','checkpoint_persistent_logical_adapter::Claim')
  s=s.replace('!memcmp(b.sha256,by::TargetSha256,32)', '!memcmp(b.sha256,o.profile.sha256,32)&&b.requested==o.profile.size&&b.returned==o.profile.size')
  s=s.replace('at<std::int32_t>(title+0x47C)!=63','at<std::int32_t>(title+0x47C)!=static_cast<std::int32_t>(o.profile.slot)')
  s=s.replace('    auto b=o.config.base,root=', '    const auto&p=o.config.worldProfile;\n    auto b=o.config.base,root=')
  s=s.replace('at<WORD>(world+0x34)!=203||at<BYTE>(world+0x36)!=8||at<BYTE>(world+0x37)!=11', 'at<WORD>(world+0x34)!=p.year||at<BYTE>(world+0x36)!=p.month||at<BYTE>(world+0x37)!=p.day')
  s=s.replace('(after?2:12)','(after?p.target.force:p.source.force)')
  s=s.replace('root+0xDCA0+12*8','root+0xDCA0+p.source.force*8').replace('root+0x148+666*8','root+0x148+p.source.ruler*8').replace('root+0xDCA0+2*8','root+0xDCA0+p.target.force*8').replace('root+0x148+952*8','root+0x148+p.target.ruler*8')
  s=s.replace('at<WORD>(source.force+0x10)!=666||at<WORD>(target.force+0x10)!=952||at<BYTE>(source.force+0x47)!=6||at<BYTE>(target.force+0x47)!=7||','at<WORD>(source.force+0x10)!=p.source.ruler||at<WORD>(target.force+0x10)!=p.target.ruler||')
  s=s.replace('personForce(b,root,source.person,666,11,12)','personForce(b,root,source.person,p.source.ruler,p.source.district,p.source.force)').replace('personForce(b,root,target.person,952,2,2)','personForce(b,root,target.person,p.target.ruler,p.target.district,p.target.force)')
  s=s.replace('    if(capture)TI_LOCK', '''    if(source.force==target.force||source.person==target.person)return false;
    // These fields are opaque serialized scenario values. Capture them from
    // this new world and require stability during the transaction; do not
    // assume the historical scenario's 6/7 values apply to other checkpoints.
    const auto source47=at<BYTE>(source.force+0x47),target47=at<BYTE>(target.force+0x47);
    if(capture)TI_LOCK(o,o.report.capturedSource47=source47;o.report.capturedTarget47=target47);
    else if(source47!=o.report.capturedSource47||target47!=o.report.capturedTarget47)return false;
    if(capture)TI_LOCK''')
  s=s.replace('bool Initialize(Adapter&o,const Config&c) noexcept {','''bool ValidWorldProfile(const WorldProfile&p) noexcept {
    auto valid=[](const Identity&i){return i.force>0&&i.force<52&&i.district>0&&i.district<52&&i.ruler>0&&i.ruler<6000;};
    return p.year&&p.month>=1&&p.month<=12&&(p.day==1||p.day==11||p.day==21)&&
        valid(p.source)&&valid(p.target)&&p.source.force!=p.target.force&&p.source.ruler!=p.target.ruler;
}
bool Initialize(Adapter&o,const Config&c) noexcept {''')
  s=s.replace('if(c.base<0x10000', 'if(!c.profile||!checkpoint_dynamic_file_profile::Validate(*c.profile)||!ValidWorldProfile(c.worldProfile)||c.base<0x10000')
  s=s.replace('bool terminated=false;', '''if(!checkpoint_dynamic_file_profile::Equal(*c.profile,c.lifecycle->profile)||!checkpoint_dynamic_file_profile::Equal(*c.profile,c.bytes->profile)){fail(o,Error::Config);return false;}
        bool terminated=false;''')
  s=s.replace('o.config=c;o.config.intentPath', 'o.profile=*c.profile;o.config=c;o.config.profile=&o.profile;o.config.intentPath')
 (P/f'checkpoint_dynamic_title_identity_adapter.{ext}').write_text(s)
for ext in ('h','cpp'):
 s=(P/f'checkpoint_persistent_native_session.{ext}').read_text()
 for old,new in [('checkpoint_persistent_native_session','checkpoint_dynamic_native_session'),('checkpoint_load_request_commit','checkpoint_dynamic_load_request_commit'),('checkpoint_cc_load_observer','checkpoint_dynamic_cc_load_observer'),('checkpoint_cc_load_lifecycle','checkpoint_dynamic_cc_load_lifecycle'),('checkpoint_title_identity_adapter','checkpoint_dynamic_title_identity_adapter')]:s=s.replace(old,new)
 if ext=='h':
  s=s.replace('// Current cores retain the validated fixed archive/scenario profile. Production\n// activation is closed until native scheduler/admission and dynamic profile bind.','// File/date/faction profiles are immutable per generation. Production activation\n// stays closed until the native scheduler and admission owner are integrated.')
  s=s.replace('void* userObservationContext=nullptr;', '''void (*userObservationFinally)(const CheckpointPushFrame*,const CheckpointLoadWorkerExit*,void*) noexcept=nullptr;
    void* userObservationContext=nullptr;''')
 else:
  s=s.replace('bool(c.userObservationBefore)!=bool(c.userObservationAfter)||','bool(c.userObservationBefore)!=bool(c.userObservationAfter)||(c.userObservationBefore&&!c.userObservationFinally)||')
  s=s.replace('        for(unsigned i=0;i<6;++i)if(c.hooks', '''        if(!c.request.profile||!c.bytes.profile||!c.lifecycle.profile||!c.identity.profile||
           !checkpoint_dynamic_file_profile::Equal(*c.request.profile,*c.bytes.profile)||
           !checkpoint_dynamic_file_profile::Equal(*c.request.profile,*c.lifecycle.profile)||
           !checkpoint_dynamic_file_profile::Equal(*c.request.profile,*c.identity.profile)){fail(Error::Config);return false;}
        for(unsigned i=0;i<6;++i)if(c.hooks''')
  s=s.replace('        if(e->abnormal)s.fail(Error::DispatchPair);', '''        if(f->slot==0&&s.config_.userObservationFinally)s.config_.userObservationFinally(f,e,s.config_.userObservationContext);
        if(e->abnormal)s.fail(Error::DispatchPair);''')
 (P/f'checkpoint_dynamic_native_session.{ext}').write_text(s)

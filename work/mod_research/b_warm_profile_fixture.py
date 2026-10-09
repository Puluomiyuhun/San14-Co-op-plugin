"""Owned native-business substitutions for the immutable-profile warm chain."""
from pathlib import Path

def transform(run:Path,P:Path):
    gp='b_warm_profile::Get()'
    body=(run/'chain_body.inc').read_text()
    body='static unsigned profileVariant=0;\n'+body
    for name,field in [('TargetName','name'),('TargetSize','size'),('TargetSha256','sha256')]:body=body.replace('by::'+name,gp+'.file.'+field)
    # Initial client state differs from the checkpoint's world after Load.
    body=body.replace('fclose(file);setup();','fclose(file);setup();layout.config.year='+gp+'.before.year;layout.config.month='+gp+'.before.month;layout.config.day='+gp+'.before.day;layout.config.force='+gp+'.currentForce;put<WORD>(world+0x34,layout.config.year);put<BYTE>(world+0x36,layout.config.month);put<BYTE>(world+0x37,layout.config.day);put<BYTE>(world+0x3A,layout.config.force);')
    for a,b in [('+0xDCA0+12*8','+0xDCA0+'+gp+'.source.force*8'),('+0x148+666*8','+0x148+'+gp+'.source.ruler*8'),('+0xDE40+11*8','+0xDE40+'+gp+'.source.district*8'),('+0xDCA0+2*8','+0xDCA0+'+gp+'.target.force*8'),('+0x148+952*8','+0x148+'+gp+'.target.ruler*8'),('+0xDE40+2*8','+0xDE40+'+gp+'.target.district*8'),('(forceA+0x10,666)','(forceA+0x10,'+gp+'.source.ruler)'),('(forceB+0x10,952)','(forceB+0x10,'+gp+'.target.ruler)'),('(personA+0x10,666)','(personA+0x10,'+gp+'.source.ruler)'),('(personB+0x10,952)','(personB+0x10,'+gp+'.target.ruler)'),('(personA+0x118,11)','(personA+0x118,'+gp+'.source.district)'),('(personB+0x118,2)','(personB+0x118,'+gp+'.target.district)'),('(districtA+0x10,12)','(districtA+0x10,'+gp+'.source.force)'),('(districtB+0x10,2)','(districtB+0x10,'+gp+'.target.force)'),('(districtA+0x12,666)','(districtA+0x12,'+gp+'.source.ruler)'),('(districtB+0x12,952)','(districtB+0x12,'+gp+'.target.ruler)'),('chosen.person==personB?2:12','chosen.person==personB?'+gp+'.target.force:'+gp+'.source.force'),('(base+0x1FCA518,2)','(base+0x1FCA518,DWORD('+gp+'.target.force))'),('(forceA+0x47,6)','(forceA+0x47,profileVariant?21:6)'),('(forceB+0x47,7)','(forceB+0x47,profileVariant?33:7)')]:
        assert a in body,a;body=body.replace(a,b)
    body=body.replace('put<DWORD>(base+0x201EC08,1);return;', 'put<WORD>(world+0x34,'+gp+'.loaded.year);put<BYTE>(world+0x36,'+gp+'.loaded.month);put<BYTE>(world+0x37,profileVariant==3?21:'+gp+'.loaded.day);put<BYTE>(world+0x3A,'+gp+'.source.force);put<DWORD>(base+0x201EC08,1);return;')
    body=body.replace('scenario==L"preflight-corrupt";','scenario==L"preflight-corrupt"||scenario==L"wrong-profile-hash";')
    body=body.replace('const bool identityPass=bytePass&&scenario!=L"title-exception";','const bool identityPass=bytePass&&scenario!=L"title-exception"&&profileVariant!=3;')
    body=body.replace('if(bytePass)check(r.identity.casApplied','if(bytePass&&profileVariant!=3)check(r.identity.casApplied')
    (run/'chain_body.inc').write_text(body)
    auth=(run/'chain_authorized.inc').read_text().replace('at<WORD>(world+0x34)==203','at<WORD>(world+0x34)=='+gp+'.before.year').replace('at<BYTE>(world+0x3A)==12','at<BYTE>(world+0x3A)=='+gp+'.currentForce')
    (run/'chain_authorized.inc').write_text(auth)
    fixture=(run/'fixture.cpp').read_text().replace('"b_warm_retire_owner.cpp"','"b_warm_profile_owner.cpp"')
    pos=fixture.index('int wmain(')
    fixture=fixture[:pos]+(P/'b_warm_profile_fixture.inc').read_text()+fixture[pos:]
    fixture=fixture.replace('if(argc!=6)return 2;const std::wstring which=argv[1];','if(argc!=6)return 2;if(!configureProfile(argv[2]))return 3;const std::wstring which=argv[1];')
    begin=fixture.index('    b_warm_retire::Report retired{};');end=fixture.index('    check(writeReport',begin)
    prior=fixture[begin:end]
    prior=prior.replace('which==L"success-new"||which==L"restore-conflict"','profileVariant<2').replace('(which==L"success-new")','(profileVariant<2)').replace('(which==L"restore-conflict")','false')
    prior=prior.replace('check(!s.hooksRestored,"failed completion keeps observations");','check(profileVariant==2?s.hooksRestored:!s.hooksRestored,"preCAS cleanup versus uncertain postCAS");')
    prior=prior.replace('for(unsigned i=0;i<6;++i)check(GuestSessionSlots[i]==reinterpret_cast<void*>(wire.hooks[i].hook),"noncomplete source kept");','if(profileVariant==3)for(unsigned i=0;i<6;++i)check(GuestSessionSlots[i]==reinterpret_cast<void*>(wire.hooks[i].hook),"uncertain source kept");')
    prior+='''
    if(profileVariant==2)check(!s.casPublished&&!s.request.casAttempts&&!s.request.read.matched,"wrong immutable hash rejects before CAS");
    if(profileVariant==3)check(s.casPublished&&s.bytes.observedWorkerAndBytes&&s.identity.error==LONG(ti::Error::World)&&!s.identity.casAttempts&&!retired.sealed,"wrong loaded date rejects actual identity guard");
    b_warm_profile::Report profileReport{};b_warm_profile::Snapshot(profileReport);check(profileReport.ready&&!b_warm_profile::Capture(profileReport.profile),"profile cannot reconfigure bank");
    printf("PROFILE variant=%u before=%u-%u-%u current=%u loaded=%u-%u-%u source=%u target=%u size=%u\\n",profileVariant,profileReport.profile.before.year,profileReport.profile.before.month,profileReport.profile.before.day,profileReport.profile.currentForce,profileReport.profile.loaded.year,profileReport.profile.loaded.month,profileReport.profile.loaded.day,profileReport.profile.source.force,profileReport.profile.target.force,profileReport.profile.file.size);
'''
    fixture=fixture[:begin]+prior+fixture[end:];(run/'fixture.cpp').write_text(fixture)

from pathlib import Path
P=Path(__file__).resolve().parent
assert not (P/'checkpoint_dynamic_native_session_fixture.cpp').exists()
s=(P/'checkpoint_persistent_native_session_fixture.cpp').read_text()
for old,new in [('checkpoint_persistent_native_session','checkpoint_dynamic_native_session'),('checkpoint_load_request_commit','checkpoint_dynamic_load_request_commit'),('checkpoint_cc_load_observer','checkpoint_dynamic_cc_load_observer'),('checkpoint_cc_load_lifecycle','checkpoint_dynamic_cc_load_lifecycle'),('checkpoint_title_identity_adapter','checkpoint_dynamic_title_identity_adapter')]:s=s.replace(old,new)
s=s.replace('static ns::Session* currentSession=nullptr;', '''static checkpoint_dynamic_file_profile::Profile fileProfile{};
static checkpoint_dynamic_title_identity_adapter::WorldProfile worldProfile{};
static ns::Session* currentSession=nullptr;''')
s=s.replace('by::TargetName','fileProfile.name').replace('by::TargetSize','fileProfile.size')
s=s.replace('put<BYTE>(world+0x3A,12);put<BYTE>(world+0x165D,2);','put<BYTE>(world+0x3A,worldProfile.source.force);put<BYTE>(world+0x165D,2);\n        put<WORD>(world+0x34,worldProfile.year);put<BYTE>(world+0x36,worldProfile.month);put<BYTE>(world+0x37,worldProfile.day);')
s=s.replace('chosen.person==personB?2:12','chosen.person==personB?worldProfile.target.force:worldProfile.source.force')
for old,new in [('root+0xDCA0+12*8','root+0xDCA0+worldProfile.source.force*8'),('root+0xDCA0+2*8','root+0xDCA0+worldProfile.target.force*8'),('root+0x148+666*8','root+0x148+worldProfile.source.ruler*8'),('root+0x148+952*8','root+0x148+worldProfile.target.ruler*8'),('root+0xDE40+11*8','root+0xDE40+worldProfile.source.district*8'),('root+0xDE40+2*8','root+0xDE40+worldProfile.target.district*8')]:s=s.replace(old,new)
for obj,who in [('forceA','source'),('forceB','target'),('personA','source'),('personB','target')]:
 s=s.replace(f'put<WORD>({obj}+0x10,'+('666' if who=='source' else '952')+')',f'put<WORD>({obj}+0x10,worldProfile.{who}.ruler)')
for obj,who in [('personA','source'),('personB','target')]:s=s.replace(f'put<BYTE>({obj}+0x118,'+('11' if who=='source' else '2')+')',f'put<BYTE>({obj}+0x118,worldProfile.{who}.district)')
for obj,who in [('districtA','source'),('districtB','target')]:
 s=s.replace(f'put<BYTE>({obj}+0x10,'+('12' if who=='source' else '2')+')',f'put<BYTE>({obj}+0x10,worldProfile.{who}.force)')
 s=s.replace(f'put<WORD>({obj}+0x12,'+('666' if who=='source' else '952')+')',f'put<WORD>({obj}+0x12,worldProfile.{who}.ruler)')
s=s.replace('put<BYTE>(forceA+0x47,6)','put<BYTE>(forceA+0x47,BYTE(40+generationIndex))').replace('put<BYTE>(forceB+0x47,7)','put<BYTE>(forceB+0x47,BYTE(60+generationIndex))')
s=s.replace('scenario=argv[1];archive.resize(fileProfile.size);buffer.resize(fileProfile.size);','''scenario=argv[1];
    FILE* measure=nullptr;_wfopen_s(&measure,argv[2],L"rb");if(!measure)return 3;
    fseek(measure,0,SEEK_END);fileProfile.size=static_cast<unsigned>(ftell(measure));fclose(measure);
    strcpy_s(fileProfile.name,"svdexccSC03.s14");fileProfile.slot=63;
    archive.resize(fileProfile.size);buffer.resize(fileProfile.size);
    worldProfile={203,8,BYTE(generationIndex?21:11),{WORD(generationIndex?766:666),12,BYTE(generationIndex?13:11)},{WORD(generationIndex?1052:952),2,BYTE(generationIndex?5:2)}};
    if(scenario==L"alternate-factions"){worldProfile.source.force=18;worldProfile.target.force=7;}
''')
s=s.replace('fclose(file);setup();layout.config.attempt+=generationIndex;','''fclose(file);check(native_storage_read::Sha256(archive.data(),archive.size(),fileProfile.sha256),"dynamic expected digest");setup();layout.config.attempt+=generationIndex;
    layout.config.force=generationIndex?worldProfile.target.force:worldProfile.source.force;put<BYTE>(world+0x3A,layout.config.force);''')
s=s.replace('    if(generationIndex){layout.config.force=2;put<BYTE>(world+0x3A,2);}','')
s=s.replace('ns::Config c{};','''ns::Config c{};c.request.profile=c.bytes.profile=c.lifecycle.profile=c.identity.profile=&fileProfile;c.identity.worldProfile=worldProfile;''')
s=s.replace('std::wstring caseName=i?L"success":first;', 'std::wstring caseName=i&&first!=L"alternate-factions"?L"success":first;')
s=s.replace('wchar_t* args[]={argv[0],caseName.data(),argv[2],req.data(),identity.data()};','''std::wstring localArchive=folder+L"/"+std::to_wstring(i)+L"/svdexccSC03.s14";
        wchar_t* args[]={argv[0],caseName.data(),localArchive.data(),req.data(),identity.data()};''')
s=s.replace('check(bool(r.identity.receiptReady)==identityPass,"identity adapter runs in real shared Session dispatcher");','''check(bool(r.identity.receiptReady)==identityPass,"dynamic identity adapter runs in shared Session dispatcher");
    if(identityPass)check(r.identity.capturedSource47==40+generationIndex&&r.identity.capturedTarget47==60+generationIndex,"opaque fields captured from new world");''')
(P/'checkpoint_dynamic_native_session_fixture.cpp').write_text(s)
s=(P/'checkpoint_persistent_native_session_test.py').read_text()
s=s.replace('checkpoint_persistent_native_session','checkpoint_dynamic_native_session')
s=s.replace("'checkpoint_persistent_native_session'", "'checkpoint_dynamic_native_session'")
for old,new in [('checkpoint_cc_load_observer','checkpoint_dynamic_cc_load_observer'),('checkpoint_cc_load_lifecycle','checkpoint_dynamic_cc_load_lifecycle'),('checkpoint_title_identity_adapter','checkpoint_dynamic_title_identity_adapter'),('checkpoint_load_request_commit','checkpoint_dynamic_load_request_commit')]:s=s.replace(old,new)
s=s.replace("UNITS=['checkpoint_persistent_bridge'", "UNITS=['checkpoint_dynamic_file_profile','checkpoint_persistent_bridge'")
s=s.replace('/DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE','/DCHECKPOINT_DYNAMIC_CC_LOAD_OBSERVER_FIXTURE').replace('/DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE','/DCHECKPOINT_DYNAMIC_CC_LOAD_LIFECYCLE_FIXTURE')
s=s.replace("('checkpoint_dynamic_cc_load_observer','checkpoint_dynamic_title_identity_adapter')", "('checkpoint_dynamic_cc_load_observer',)")
s=s.replace("'post-cas-reject']","'post-cas-reject','alternate-factions']")
s=s.replace("folder=run/case;folder.mkdir();archive=folder/'svdexccSC03.s14';shutil.copyfile(ARCHIVE,archive)","""folder=run/case;folder.mkdir();archive=folder/'0'/'svdexccSC03.s14';archive.parent.mkdir();shutil.copyfile(ARCHIVE,archive)
  second=folder/'1'/'svdexccSC03.s14';second.parent.mkdir();payload=bytearray(ARCHIVE.read_bytes());payload[77]^=0x5a;payload.extend(bytes(range(128)));second.write_bytes(payload)
  second_sha=sha(second)""")
s=s.replace("row['archive_unchanged']=sha(archive)==EXPECTED", "row['archive_unchanged']=sha(archive)==EXPECTED and sha(second)==second_sha")
s=s.replace('san14.persistent-session-core-integration.v1','san14.dynamic-session-core-integration.v1')
s=s.replace("'repeated_real_game_load_proven':False", "'dynamic_native_file_date_identity_tested':True,'repeated_real_game_load_proven':False")
s=s.replace('Fixed historical file/date/factions; no game deserialization, changing checkpoint parameters, planning readiness or controller integration.', 'Second generation uses different bytes, size, digest, date, rulers, districts and opaque fields; alternate-factions case also varies source/target force IDs. No game deserialization, planning readiness or controller integration.')
(P/'checkpoint_dynamic_native_session_test.py').write_text(s)

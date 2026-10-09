static bool configureProfile(const wchar_t*path){
    wchar_t mode[8]{};GetEnvironmentVariableW(L"B_WARM_PROFILE_VARIANT",mode,8);profileVariant=unsigned(_wtoi(mode));
    std::ifstream file(path,std::ios::binary);std::vector<unsigned char> data((std::istreambuf_iterator<char>(file)),{});
    b_warm_profile::Profile p{};strcpy_s(p.file.name,checkpoint_dynamic_file_profile::SupportedName);p.file.slot=63;p.file.size=std::uint32_t(data.size());
    if(data.empty()||!native_storage_read::Sha256(data.data(),data.size(),p.file.sha256))return false;
    if(profileVariant==0){p.before={203,8,11};p.loaded={203,8,11};p.currentForce=12;p.source={666,12,11};p.target={952,2,2};}
    else {p.before={204,9,1};p.loaded={204,9,11};p.currentForce=2;p.source={111,7,6};p.target={222,9,8};}
    if(profileVariant==2)p.file.sha256[0]^=1;
    return b_warm_profile::Capture(p);
}

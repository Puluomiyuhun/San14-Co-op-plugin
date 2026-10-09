extern "C" {
__declspec(dllimport) uintptr_t HostStorageVtable[16],HostStorage[2];
__declspec(dllimport) bool HostExists(void*,const char*);
__declspec(dllimport) std::int32_t HostFileSize(void*,const char*);
}
static void pairModule(checkpoint_live_storage_binding::ModuleApproval&m,HMODULE module){
    m={};m.base=uintptr_t(module);GetModuleFileNameW(module,m.path,1024);
    const auto*pe=reinterpret_cast<const IMAGE_NT_HEADERS64*>(m.base+reinterpret_cast<const IMAGE_DOS_HEADER*>(m.base)->e_lfanew);m.sizeOfImage=pe->OptionalHeader.SizeOfImage;m.timestamp=pe->FileHeader.TimeDateStamp;
    std::ifstream in(m.path,std::ios::binary);std::vector<unsigned char> bytes((std::istreambuf_iterator<char>(in)),{});m.fileSize=bytes.size();
    check(native_storage_read::Sha256(bytes.data(),bytes.size(),m.fileSha256)&&native_storage_read::Sha256(reinterpret_cast<void*>(m.base),4096,m.headerSha256),"two actual MEM_IMAGE module identities");
}
static void pairConfig(checkpoint_complete_live_owner::Config&c){
    HMODULE bank=nullptr;check(GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,reinterpret_cast<LPCWSTR>(&InstallCheckpointCompleteLiveOwner),&bank)!=0,"actual bank module");
    c.storageModuleCount=2;pairModule(c.storageModules[0],bank);pairModule(c.storageModules[1],GetModuleHandleW(nullptr));
    factoryEndpoint(c.exists,reinterpret_cast<void*>(&HostExists));factoryEndpoint(c.fileSize,reinterpret_cast<void*>(&HostFileSize));
    c.contextInit.moduleIndex=c.exists.moduleIndex=c.fileSize.moduleIndex=c.read.moduleIndex=1;c.ownedReadBridge.moduleIndex=0;
    c.storage=uintptr_t(HostStorage);c.storageVtable=uintptr_t(HostStorageVtable);c.storageCounter=uintptr_t(&BindingFixtureGeneration);c.vtableModuleIndex=c.counterModuleIndex=1;
    HostStorageVtable[13]=c.exists.address;HostStorageVtable[15]=c.fileSize.address;
    put<uintptr_t>(base+0x18d08c8,c.storage);
}

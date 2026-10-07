#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdio>
#include <string>
#include <vector>
int main(int argc,char**argv){if(argc>1){Sleep(500);return 0;}char path[32768];GetModuleFileNameA(nullptr,path,sizeof path);STARTUPINFOA s{};s.cb=sizeof s;PROCESS_INFORMATION p{};std::string command=std::string("\"")+path+"\" child";std::vector<char> c(command.begin(),command.end());c.push_back(0);if(!CreateProcessA(path,c.data(),nullptr,nullptr,FALSE,CREATE_NO_WINDOW,nullptr,nullptr,&s,&p))return 2;if(!DebugActiveProcess(p.dwProcessId))return 3;if(!DebugSetProcessKillOnExit(FALSE))return 4;DEBUG_EVENT e{};if(!WaitForDebugEvent(&e,5000))return 5;printf("event=%lu\n",e.dwDebugEventCode);BOOL detached=DebugActiveProcessStop(p.dwProcessId);printf("detach=%d error=%lu\n",detached,GetLastError());DWORD wait=WaitForSingleObject(p.hProcess,3000),code=0;GetExitCodeProcess(p.hProcess,&code);printf("wait=%lu exit=%lu\n",wait,code);if(e.dwDebugEventCode==CREATE_PROCESS_DEBUG_EVENT&&e.u.CreateProcessInfo.hFile)CloseHandle(e.u.CreateProcessInfo.hFile);CloseHandle(p.hThread);CloseHandle(p.hProcess);return detached&&wait==WAIT_OBJECT_0&&code==0?0:9;}

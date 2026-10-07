"""Version-locked one-shot DLL pilot; default is a dry update-hook check.

New remote threads ONLY load the DLL, install its pending request, or cancel the
hook. The actual game function runs from the native player update callback.
The DLL stays inert in the process after the vtable slot is restored, until exit.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import time

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'outputs'/'san14-link'))
sys.path.insert(0,str(ROOT/'python_deps'))
import pefile
from battle_observer import BattleObserver
from pilot_evidence import check_checkpoint,check_restored,load_json,require,check_native_trace,check_native_effect

REPORT=struct.Struct('<14I7Q4I')
REPORT_NAMES=('magic version status error active_callbacks accepted installer_thread executor_thread original_calls submit_calls '
              'before_garrison after_garrison before_action after_action base caller state unit slot original hook '
              'slot_restored protection_restored exception_code reserved').split()


def wincheck(value):
    if not value: raise C.WinError(C.get_last_error())
    return value


class ProcessAPI:
    def __init__(self,reader):
        self.reader=reader
        self.k=C.WinDLL('kernel32',use_last_error=True)
        self.p=C.WinDLL('psapi',use_last_error=True)
        bindings={
            'OpenProcess':([W.DWORD,W.BOOL,W.DWORD],W.HANDLE),
            'CloseHandle':([W.HANDLE],W.BOOL),
            'VirtualAllocEx':([W.HANDLE,C.c_void_p,C.c_size_t,W.DWORD,W.DWORD],C.c_void_p),
            'VirtualFreeEx':([W.HANDLE,C.c_void_p,C.c_size_t,W.DWORD],W.BOOL),
            'WriteProcessMemory':([W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)],W.BOOL),
            'CreateRemoteThread':([W.HANDLE,C.c_void_p,C.c_size_t,C.c_void_p,C.c_void_p,W.DWORD,C.POINTER(W.DWORD)],W.HANDLE),
            'WaitForSingleObject':([W.HANDLE,W.DWORD],W.DWORD),
            'GetExitCodeThread':([W.HANDLE,C.POINTER(W.DWORD)],W.BOOL),
            'GetModuleHandleW':([W.LPCWSTR],W.HMODULE),
            'GetProcAddress':([W.HMODULE,C.c_char_p],C.c_void_p),
            'GetModuleHandleExW':([W.DWORD,C.c_void_p,C.POINTER(W.HMODULE)],W.BOOL),
            'GetModuleFileNameW':([W.HMODULE,W.LPWSTR,W.DWORD],W.DWORD),
            'CheckRemoteDebuggerPresent':([W.HANDLE,C.POINTER(W.BOOL)],W.BOOL),
        }
        for name,(args,result) in bindings.items():
            function=getattr(self.k,name);function.argtypes=args;function.restype=result
        self.p.EnumProcessModulesEx.argtypes=[W.HANDLE,C.POINTER(C.c_void_p),W.DWORD,C.POINTER(W.DWORD),W.DWORD]
        self.p.EnumProcessModulesEx.restype=W.BOOL
        self.p.GetModuleFileNameExW.argtypes=[W.HANDLE,W.HMODULE,W.LPWSTR,W.DWORD]
        self.p.GetModuleFileNameExW.restype=W.DWORD
        self.handle=wincheck(self.k.OpenProcess(0x0400|0x0010|0x0020|0x0008|0x0002,False,reader.pid))
        debugger=W.BOOL()
        wincheck(self.k.CheckRemoteDebuggerPresent(self.handle,C.byref(debugger)))
        require(not debugger.value,'Another debugger is attached')

    def close(self):
        self.k.CloseHandle(self.handle)

    def modules(self):
        entries=(C.c_void_p*2048)();size=W.DWORD()
        wincheck(self.p.EnumProcessModulesEx(self.handle,entries,C.sizeof(entries),C.byref(size),3))
        require(size.value<=C.sizeof(entries),'Module list exceeded capacity')
        result=[]
        for base in entries[:size.value//C.sizeof(C.c_void_p)]:
            path=C.create_unicode_buffer(32768)
            wincheck(self.p.GetModuleFileNameExW(self.handle,base,path,32768))
            result.append((base,Path(path.value)))
        return result

    def load_library_address(self):
        module=wincheck(self.k.GetModuleHandleW('kernel32.dll'))
        address=wincheck(self.k.GetProcAddress(module,b'LoadLibraryW'))
        owner=W.HMODULE()
        wincheck(self.k.GetModuleHandleExW(6,address,C.byref(owner)))
        path=C.create_unicode_buffer(32768)
        wincheck(self.k.GetModuleFileNameW(owner,path,32768))
        candidates=[base for base,p in self.modules() if p.name.lower()==Path(path.value).name.lower()]
        require(len(candidates)==1,'Cannot resolve the remote LoadLibraryW owner module')
        return candidates[0]+address-owner.value

    def call_adapter(self,address,data=None):
        allocation=None;thread=None;completed=False
        try:
            if data is not None:
                allocation=wincheck(self.k.VirtualAllocEx(self.handle,None,len(data),0x3000,0x04))
                buffer=C.create_string_buffer(data);written=C.c_size_t()
                wincheck(self.k.WriteProcessMemory(self.handle,allocation,buffer,len(data),C.byref(written)))
                require(written.value==len(data),'Partial adapter input write')
            tid=W.DWORD()
            thread=wincheck(self.k.CreateRemoteThread(self.handle,None,0,address,allocation,0,C.byref(tid)))
            wait=self.k.WaitForSingleObject(thread,10000)
            require(wait==0,'Adapter thread did not finish within 10 seconds; input kept allocated, thread not terminated')
            completed=True
            code=W.DWORD();wincheck(self.k.GetExitCodeThread(thread,C.byref(code)))
            return code.value
        finally:
            if thread:self.k.CloseHandle(thread)
            # Never free an argument buffer while a timed-out thread may still read it.
            if allocation and (completed or not thread):
                wincheck(self.k.VirtualFreeEx(self.handle,allocation,0,0x8000))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true',help='Submit exactly one recorded Zhang Lu 1300 command after native update')
    parser.add_argument('--command-file',type=Path,help='Use a strictly validated pilot command envelope from the local receiver')
    args=parser.parse_args()
    original_trace=ROOT/'native-traces'/'20261004-192236-615008'/'trace.jsonl'
    rows=[json.loads(line) for line in original_trace.read_text().splitlines() if line]
    words=check_native_trace(rows)
    network_request=None
    if args.command_file:
        from pilot_request import validate_payload
        network_request=load_json(args.command_file)
        received_words=validate_payload(network_request)
        require(received_words==words,'Received payload differs from the captured reference')
        words=received_words
    baseline=load_json(ROOT/'before-native-submit.json')
    checkpoint=ROOT.parent/'mod_test'/'replay-checkpoint-34'/'svdexSC34.s14'
    check_checkpoint(checkpoint)
    check_checkpoint(Path(r'C:\Program Files (x86)\Steam\userdata\391007908\872410\remote\svdexSC34.s14'))
    run=ROOT/'autonomous-traces'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True,exist_ok=False)
    reader=BattleObserver();api=None;report_address=None;cancel_address=None
    try:
        before=reader.capture();check_restored(baseline,before)
        require(before['state_stack']==['CRootState','CMotorGameState','CGameState','CStrategyState','CUserStrategyState'],
                'Expected plain map, with no order dialog')
        base=reader.memory.base
        image=(ROOT/'game-runtime-image.bin').read_bytes()
        for rva in (0x1D1940,0x3F9B00):
            require(reader.memory.read(base+rva,32)==image[rva:rva+32],'Runtime fingerprint mismatch')
        slot=base+0x12CC4A8+0x28
        require(struct.unpack('<Q',reader.memory.read(slot,8))[0]==base+0x3F9B00,'Update slot was already changed')
        dll=run/f'san14-pilot-{run.name}.dll'
        shutil.copyfile(ROOT/'autonomous_pilot.dll',dll)
        pe=pefile.PE(str(dll))
        exports={s.name.decode():s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
        require(all(name in exports for name in ('InstallPilot','CancelPilot','PilotReport')),'Unexpected adapter exports')
        pe.close()
        info={'mode':'autonomous-single-sortie' if args.execute else 'dry-update-hook',
              'pid':reader.pid,'base':hex(base),'game_sha256':reader.sha256,'dll_path':str(dll),
              'dll_sha256':hashlib.sha256(dll.read_bytes()).hexdigest(),'command_words':words,
              'request_id':network_request['request_id'] if network_request else None,
              'command_source':'validated-command-file' if network_request else 'native-capture',
              'before':before,'inert_module_remains_loaded_until_game_exit':True}
        (run/'metadata.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
        api=ProcessAPI(reader)
        api.call_adapter(api.load_library_address(),str(dll).encode('utf-16le')+b'\0\0')
        modules=[b for b,path in api.modules() if str(path).lower()==str(dll).lower()]
        require(len(modules)==1,'Adapter module not found after LoadLibraryW')
        module=modules[0];report_address=module+exports['PilotReport'];cancel_address=module+exports['CancelPilot']
        def read_report():
            report=dict(zip(REPORT_NAMES,REPORT.unpack(reader.memory.read(report_address,REPORT.size))))
            require(report['magic']==0x1414A001 and report['version']==1,'Invalid adapter report')
            return report
        config=struct.pack('<QII26I',0x53414E3134503031,1,int(args.execute),*words)
        code=api.call_adapter(module+exports['InstallPilot'],config)
        deadline=time.monotonic()+8
        report=read_report()
        while time.monotonic()<deadline and (report['status']<3 or report['active_callbacks']):
            time.sleep(.05);report=read_report()
        if report['status']==1:
            api.call_adapter(cancel_address);report=read_report()
        (run/'adapter-report.json').write_text(json.dumps(report,indent=2))
        require(code==0,f'Adapter installation failed with {code}: {report}')
        require(report['status']==(4 if args.execute else 3),f'Adapter rejected or failed: {report}')
        require(report['slot_restored']==1 and report['protection_restored']==1 and not report['active_callbacks'],
                'Adapter callback cleanup is incomplete')
        require(struct.unpack('<Q',reader.memory.read(slot,8))[0]==base+0x3F9B00,'Actual update slot did not restore')
        require(report['caller']==base+0x50B785 and report['installer_thread']!=report['executor_thread'],
                'Native scheduling evidence is missing')
        require(report['submit_calls']==int(args.execute),'Unexpected game submit count')
        # Allow the ordinary game update/render jobs to settle; no UI input is sent.
        time.sleep(.4)
        after=reader.capture()
        (run/'after.json').write_text(json.dumps(after,ensure_ascii=False,indent=2),encoding='utf-8')
        if args.execute:
            effects=check_native_effect(before,after,words)
            comparison=check_restored(load_json(ROOT/'after-native-captured-submit.json'),after)
        else:
            effects={'game_submit_calls':0}
            comparison=check_restored(before,after)
        result={'result':'PASS','mode':info['mode'],'directory':str(run),'adapter':report,
                'request_id':info['request_id'],'command_source':info['command_source'],
                'effects':effects,'state_comparison':comparison,
                'manual_game_confirmation_required':False,'network_connected':False,
                'two_client_multiplayer':False,'inert_module_remains_loaded_until_game_exit':True,
                'post_test_restore':'REQUIRED' if args.execute else 'NOT_NEEDED'}
        (run/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        output=ROOT.parents[1]/'outputs'/'san14-link'/('自动出征试验.json' if args.execute else '自动提交接入验证.json')
        output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result,ensure_ascii=True,indent=2))
    except Exception:
        if api and report_address and cancel_address:
            try:
                data=dict(zip(REPORT_NAMES,REPORT.unpack(reader.memory.read(report_address,REPORT.size))))
                if data['status']==1:api.call_adapter(cancel_address)
                (run/'failure-adapter-report.json').write_text(json.dumps(data,indent=2))
            except Exception:pass
        raise
    finally:
        if api:api.close()
        reader.close()


if __name__=='__main__':main()

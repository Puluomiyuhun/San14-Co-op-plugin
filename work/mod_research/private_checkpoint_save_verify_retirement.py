"""Own-process checks of disabled production entrypoints; no SAN14 access."""
from pathlib import Path
from datetime import datetime
import ctypes as C,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parent;rows=[]
for filename,export,report,size in [('private_checkpoint_save_disabled.dll','InstallPrivateCheckpointSave','PrivateCheckpointSaveReport',288),
                                    ('private_checkpoint_save_standard_disabled.dll','InstallSaveCheckpoint','SaveCheckpointReport',184)]:
    path=ROOT/filename;dll=C.WinDLL(str(path));fn=getattr(dll,export);fn.argtypes=[C.c_void_p];fn.restype=C.c_uint32
    value=fn(None);data=bytes((C.c_ubyte*size).in_dll(dll,report));assert value==9001 and not any(data[8:]),(filename,value)
    rows.append({'binary':filename,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'entry_return':value,'report_after_header_zero':True,'own_process_only':True})
for filename in ('private_checkpoint_save_start.py','save_checkpoint_start.py'):
    for mode in ('--precheck','--dry','--execute'):
        p=subprocess.run([sys.executable,str(ROOT/filename),mode],capture_output=True,text=True,timeout=5,creationflags=subprocess.CREATE_NO_WINDOW)
        result=json.loads(p.stdout);assert result['result']=='RETIRED_UNSAFE_STATE_ENTRY' and result['game_access'] is False
        assert p.returncode in (0,2);rows.append({'launcher':filename,'mode':mode,'returncode':p.returncode,'game_access':False})
path=ROOT/('private_checkpoint_save_retirement_verification_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
result={'result':'PASS','checks':rows,'game_access':False,'historical_binaries_overwritten':False,'historical_once_or_results_changed':False}
with path.open('x',encoding='utf8') as f:json.dump(result,f,indent=2)
print(json.dumps({'result':'PASS','checks':len(rows),'evidence':str(path),'game_access':False}))

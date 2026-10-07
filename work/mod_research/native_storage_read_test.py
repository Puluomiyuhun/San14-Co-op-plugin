"""Creates only fresh synthetic fixture files under work; never accesses Steam."""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parent
cases=('match','pin_blocks_write','missing','size_zero','size_negative','size_huge','size_wrong',
 'read_zero','read_negative','read_short','read_excess','first_bytes_wrong','second_bytes_wrong',
 'size_changed','vanished','context_invalid','context_drift','api_exception','local_hash_wrong',
 'local_size_wrong','name_wrong','path_escape','null_api','input_zero','input_huge')
folder=ROOT/'native_storage_read_fixtures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True,exist_ok=False)
rows=[]
for case in cases:
    destination=folder/case;destination.mkdir()
    result=subprocess.run([str(ROOT/'native_storage_read_fixture.exe'),case,str(destination)],capture_output=True,text=True,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
    (destination/'stdout.txt').write_text(result.stdout,encoding='utf-8');(destination/'stderr.txt').write_text(result.stderr,encoding='utf-8')
    row=json.loads(result.stdout);assert result.returncode==0 and row['passed'],(row,result.stderr)
    rows.append(row)
report={'schema':'san14.native-storage-read-core-fixtures.v1','result':'PASS','cases':rows,
 'game_access':False,'Steam_API_called':False,'fixture_files_written':True,
 'scope':'Real read-only core, Windows local file pin and BCrypt hashing; native Storage API is an in-process explicit fake. No game hook, native load, or real Steam content identity claim.',
 'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('native_storage_read_core.h','native_storage_read_core.cpp','native_storage_read_fixture.cpp')}}
with (folder/'result.json').open('x',encoding='utf-8') as file:json.dump(report,file,indent=2)
print(json.dumps({'result':'PASS','cases':len(rows),'path':str(folder/'result.json'),'game_access':False}))

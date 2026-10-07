"""Uses only the work archive; fake Storage API returns archive bytes."""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parent
archive=ROOT/'checkpoint_push_archives/20261006-204306-581930/mppush01.s14'
expected='88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
assert archive.stat().st_size==274880 and hashlib.sha256(archive.read_bytes()).hexdigest()==expected
destination=ROOT/'native_storage_read_fixtures'/('archive-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
destination.mkdir(parents=True,exist_ok=False)
p=subprocess.run([str(ROOT/'native_storage_read_fixture.exe'),'archive_match',str(destination),str(archive)],capture_output=True,text=True,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
(destination/'stdout.txt').write_text(p.stdout,encoding='utf-8');(destination/'stderr.txt').write_text(p.stderr,encoding='utf-8')
row=json.loads(p.stdout);assert p.returncode==0 and row['passed'] and row['matched'],(p.returncode,row,p.stderr)
report={'schema':'san14.native-storage-read-archived-file-fixture.v1','result':'PASS','case':row,
 'archived_input':str(archive.relative_to(ROOT)),'bytes':274880,'sha256':expected,
 'game_access':False,'Steam_API_called':False,'actual_native_local_identity_proven':False,
 'scope':'Core uses the actual successful export archive as its local bytes. The own-process fake Storage API returns those same archived bytes. This checks full real-file size/hash/pin handling but is NOT the real Steam read.',
 'core_cpp_sha256':hashlib.sha256((ROOT/'native_storage_read_core.cpp').read_bytes()).hexdigest(),
 'fixture_cpp_sha256':hashlib.sha256((ROOT/'native_storage_read_fixture.cpp').read_bytes()).hexdigest()}
with (destination/'result.json').open('x',encoding='utf-8') as f:json.dump(report,f,indent=2)
print(json.dumps({'result':'PASS','cases':1,'path':str(destination/'result.json'),'Steam_API_called':False}))

"""Native C++ integration-core tests with explicit fixture-native adapters."""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parent
shadow=json.loads((ROOT/'private_checkpoint_metadata_shadow.json').read_text())
assert shadow['result']=='PASS'
folder=ROOT/'private_checkpoint_metadata_fixtures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
header=folder/'native-parsed-header.bin';header.write_bytes(bytes.fromhex(shadow['cases'][0]['header_hex']))
payload=(ROOT.parent/'mod_test/replay-checkpoint-34/svdexSC34.s14').read_bytes()[:512]
digest=hashlib.sha256(payload).hexdigest()
cases=('execute','preexisting','dry','duplicate','wrong_slot','wrong_hash','wrong_mode','pending','occupied','table_foreign','list_corrupt','existing_name','not_idle','existing_once','native_slot_exists','local_slot_exists','missing_native_target','open_fails','wrong_stream_mode','wrong_version','parse_fails','header_magic','header_date','header_ruler','header_snapshot_mismatch','copy_filename','drift_before_node','drift_before_commit')
results=[]
for case in cases:
    out=folder/case;out.mkdir();checkpoint=out/'mpckpt01.s14';checkpoint.write_bytes(payload)
    once=out/'private_checkpoint_metadata_mpckpt01_once.json'
    if case=='existing_once':once.write_text('keep original intent\n')
    if case=='local_slot_exists':(out/'svdexCC03.s14').write_bytes(b'preserve existing native file')
    before={p.name:p.read_bytes() for p in out.iterdir()}
    ran=subprocess.run([str(ROOT/'private_checkpoint_metadata_fixture.exe'),str(out),case,digest,str(header)],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
    assert ran.returncode==0,(case,ran.stdout,ran.stderr)
    item=json.loads(ran.stdout);assert item['result']=='PASS' and not item['game_access']
    for name,data in before.items():assert (out/name).read_bytes()==data,(case,'existing file changed',name)
    if item['intent_created']:
        intent=json.loads(once.read_text());assert intent['sha256']==digest and intent['filename']=='mpckpt01.s14' and not intent['submits_load'] and intent['outcome']=='unknown_no_auto_retry'
    elif case!='existing_once':assert not once.exists()
    results.append(item);print(json.dumps({'case':case,'result':'PASS'}),flush=True)
report={'schema':'san14.private-checkpoint-metadata-fixture.v1','result':'PASS','cases':results,'directory':str(folder),'binary_sha256':hashlib.sha256((ROOT/'private_checkpoint_metadata_fixture.exe').read_bytes()).hexdigest(),
 'scope':'Compiled native registration core with real Windows file pin/hash/create-new journal and owned-memory/list checks. Game calls and stable-boundary query are explicit fixture adapters; actual copied native ABI/parser/ownership is separately tested in Unicorn. No live game adapter, injector, scheduler hook or load request is provided.',
 'eligible_live_execution':False,'game_access':False}
(ROOT/'private_checkpoint_metadata_fixture_results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'result':'PASS','cases':len(cases),'game_access':False,'eligible_live_execution':False}))

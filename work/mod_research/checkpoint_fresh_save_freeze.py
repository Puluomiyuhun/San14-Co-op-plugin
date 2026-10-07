"""Freeze the two-request export component; never access the game."""
from pathlib import Path
import hashlib,json,shutil
P=Path(__file__).resolve().parent
RUN=P/'checkpoint_fresh_save_runs/20261007-233532-287724'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p.resolve()),'sha256':sha(p)}
def main():
 result=json.loads((RUN/'result.json').read_text())
 assert result['result']=='PASS' and len(result['cases'])==26
 assert all(r['result']=='PASS' and r['exit']==0 for r in result['cases'])
 for name,digest in result['sources'].items():assert sha(P/name)==digest,name
 frozen=RUN/'frozen_sources';frozen.mkdir()
 for name in (*result['sources'],'checkpoint_fresh_save_test.py'):shutil.copy2(P/name,frozen/name)
 handoff={'schema':'san14.fresh-save-handoff.v1','result':'PASS_TWO_REQUEST_OWNED_EXPORT_COMPONENT',
 'result_file':ref(RUN/'result.json'),'production_library':ref(RUN/'checkpoint_fresh_save.lib'),
 'sources':result['sources'],'test_runner':ref(P/'checkpoint_fresh_save_test.py'),'cases':26,
 'production_path':'Actual fixed native 2FC750 Save binder and 2DF990 type0 push queue; configured to be called from the real User AFTER scope. No source installer in this component.',
 'request_scope':'Two retained requests in one Driver and unchanged bridge configuration. Each request has its own exclusive durable intent, mod-only mpXXXXXXXX.s14 filename, generation/date/faction and opaque room/cut fields. These fields do not grant room authority.',
 'native_completion':'Original Save Update phases 0..4, started/joined/success/finalizer, request-global/cache cleanup, then same original User and world/date/rng at a later actual return scope. Completion is published only by FINALLY.',
 'bytes':'New target absent locally and through native FileExists before queue. After native completion, pin local file without write/delete sharing; derive size/hash; frozen native_storage_read::Verify compares two native reads through approved Api and retains its own handle. CopyArtifact returns an owned vector by completed generation. Failed/partial export returns nothing.',
 'stop':'Before binder, Stop rejects subsequent admission. Once binder may have run, Stop never claims cancellation, never retries the request and permits existing normal native completion to be observed; it permanently rejects all further Submit calls. Late Stop is reflected in Snapshot and FINALLY.',
 'tested':['Two dates, two unique files and differing hashes in the same process, first bytes still available after second export','Real immutable Win64 assembly bridge, ownership TLS and FINALLY including native SEH','Actual Windows CREATE_NEW/FlushFileBuffers intents, file leases and two storage-read comparisons','No source overwrite from duplicate generation/name; period zero rejected','Selected/pending state, date drift, storage errors, binder/queue mismatch, wrong Save object/phase, native failure and late return drift reject','Partial bytes, native byte mismatch and invalid storage binding reject; late Stop tested inside worker and byte read'],
 'fixture_limits':'Native User/Save bodies, binder/queue and Steam storage interface bodies are explicit doubles. The fixture payload is diagnostic, not a SAN14 save. Passing this suite does not prove two real game saves or current authoritative room export.',
 'integration_required':['Retained actual User and Save callback publication; never replay the retired type2 Save route or reset old one-shot claims','Both originals must be the actual native bodies. A planning dispatcher wrapper returning while suppressing User is not an original User return; do not send that result to Driver::After','Supported executable and source profile plus approved live_storage_binding Api/module/world lifetimes; real physical bridge claim/owner ports','Room validates opaque request binding/cut and provides actual input exclusion. This component observes idle planning but does not prevent all other input','Feed CopyArtifact bytes into existing CheckpointPackage only after the trusted room owns the current authoritative boundary; B load/identity/full-world confirmation remains separate'],
 'game_access_this_component':False,'game_installer':False,'new_native_save_live':False,'full_world':False,'room_ready':False,'two_real_clients':False}
 path=P/'checkpoint_fresh_save_handoff.json'
 with path.open('x',encoding='utf8')as f:json.dump(handoff,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps(ref(path)))
if __name__=='__main__':main()

"""Independent frozen artifact/evidence audit; no native execution or game access."""
from datetime import datetime
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    hp=P/'checkpoint_live_storage_binding_handoff.json';h=json.loads(hp.read_text())
    assert sha(hp)=='636cf0752d3de77a5d6762ee0775a4d59e996807cfc9400163c9f9002d4adac6'
    rows=[]
    def check(path,wanted):
        actual=sha(path);rows.append({'path':str(path),'sha256':actual,'matches':actual==wanted})
        assert actual==wanted
    for name,wanted in h['source_sha256'].items():check(P/name,wanted)
    for name,wanted in h['evidence_sources'].items():check(P/name,wanted)
    check(Path(h['fixture_report']),h['fixture_report_sha256'])
    check(P/h['fixture_binary'],h['fixture_binary_sha256'])
    check(P/h['production_object'],h['production_object_sha256'])
    check(P/'checkpoint_live_storage_binding_fixture_core.obj',h['fixture_core_sha256'])
    check(P/'checkpoint_live_storage_binding_notes.txt',h['notes_sha256'])
    result=json.loads(Path(h['fixture_report']).read_text())
    assert result['result']=='PASS' and len(result['cases'])==24
    assert all(c['passed'] and c['exit_code']==0 for c in result['cases'])
    assert result['source_unchanged_during_build_and_run']
    review={'schema':'san14.live-storage-binding-independent-review.v1',
        'result':'PASS_STATIC_AND_EVIDENCE_REVIEW_NO_NEW_BLOCKER','reviewer':'/root',
        'handoff_sha256':sha(hp),'hash_checks':rows,'owned_cases':24,'tests_rerun':False,'game_access':False,
        'reviewed_properties':[
            'Cached ContextInit code and RIP-relative generation are checked without invoking ContextInit.',
            'Token/version/IAT/cached holder/object/VT/methods are rechecked around mandatory owner callbacks.',
            'Api.read remains the approved immutable original when VT+08 is an explicitly owned bridge.',
            'Actual loaded module lookup, PIN, mapped PE identity, endpoint bytes and cross-region readability checks.',
            'Open hashes approved module files once; subsequent Valid uses only small mapped checks.',
            'Validation failure/Invalidate/repeated Open are terminal; concurrent/reentrant validation refuses.',
            'Only fixture allows an own-PE path/synthetic game base; production object has no such define.'
        ],'limits':[
            'No real Steam execution or installation; future trusted callback/lifetime guards remain mandatory.',
            'Disk file handles close after initial hash. Module PIN and selected code/header checks are not full-image immutability.',
            'No scheduler fence, global input hold, complete world check, or automatic-load authority.',
            'Validator graph must remain acyclic; do not call storage.Valid recursively from checkOwner.'
        ]}
    path=P/('checkpoint_live_storage_binding_review_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
    with path.open('x',encoding='utf8',newline='\n')as f:json.dump(review,f,indent=2);f.write('\n')
    print(json.dumps({'result':review['result'],'path':str(path),'sha256':sha(path),'hash_checks':len(rows)}))
if __name__=='__main__':main()

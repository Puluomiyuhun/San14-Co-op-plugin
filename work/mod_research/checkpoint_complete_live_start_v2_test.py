"""Verify V2 cannot run over its retained V1 owner; no process access."""
import json,tempfile,types
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from datetime import datetime
import checkpoint_complete_live_start_v2 as start
P=Path(__file__).resolve().parent

def main():
    rows=[]
    with tempfile.TemporaryDirectory(prefix='san14-v2-attachment-') as temp:
        folder=Path(temp)
        (folder/'checkpoint_complete_live_once.json').write_text(json.dumps(dict(pid=19,birth=29)),encoding='utf8')
        for pid,birth,rejected_for_same in ((19,29,True),(19,30,False),(20,31,False)):
            with ExitStack()as stack:
                stack.enter_context(patch.object(start,'P',folder))
                stack.enter_context(patch.object(start,'CLAIM',folder/'new-once.json'))
                stack.enter_context(patch.object(start,'process_birth',lambda reader:birth))
                stack.enter_context(patch.object(start,'APPROVED_DLL','UNREVIEWED'))
                try:start.execute(types.SimpleNamespace(pid=pid),None,{})
                except RuntimeError as exc:
                    if rejected_for_same:assert 'fresh game process' in str(exc)
                    else:assert 'Unreviewed owner artifact' in str(exc)
                else:raise AssertionError('Unreviewed fixture ran')
                assert not (folder/'new-once.json').exists()
                rows.append(dict(pid=pid,birth=birth,rejected_existing_lifetime=rejected_for_same,passed=True))
    out=P/'checkpoint_complete_live_start_v2_tests'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    (out/'result.json').write_text(json.dumps(dict(passed=True,cases=rows,game_access=False),indent=2),encoding='utf8')
    print(json.dumps(dict(passed=True,cases=len(rows),path=str(out/'result.json'))))

if __name__=='__main__':main()

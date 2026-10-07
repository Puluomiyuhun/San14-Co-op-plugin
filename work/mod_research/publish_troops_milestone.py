"""Publish the bounded native-query milestone, not a playable build claim."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parents[1]/'outputs'/'san14-link'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
native=load(ROOT/'troops-fixture-results.json')
guards=load(ROOT/'troops-reader-guard-tests.json')
policy=load(ROOT/'human-ai-with-troops-results.json')
preview=load(OUT/'双人控制范围含编组预览.json')
closeout=load(ROOT/'human-ai-closeout.json')
assert all(r['result']=='PASS' for r in [native,guards,policy,closeout])
assert preview['army_groups_decoded'] and not preview['applied_to_game']
assert policy['live_preview_sha256']==hashlib.sha256((OUT/'双人控制范围含编组预览.json').read_bytes()).hexdigest()
assert closeout['known_rng_equal_to_recent_restore'] and closeout['checkpoint34_unchanged']
paths=[OUT/'troops_reader.py',OUT/'human_control_reader.py',OUT/'human_ai_policy.h',
       OUT/'双人控制范围含编组预览.json',OUT/'双人联机当前缺口与使用形态.txt',
       ROOT/'make_troops_fixture.py',ROOT/'troops_fixture.cpp',ROOT/'troops_fixture_code.h',
       ROOT/'validate_troops_fixture.py',ROOT/'test_troops_reader_guards.py']
result={'schema':'san14.troops-and-human-control-milestone.v1','created':datetime.now().astimezone().isoformat(),
        'result':'READ_ONLY_GROUP_OWNERSHIP_CORRELATED_NATIVE_AI_HOOK_PENDING',
        'native_getter':native,'native_source':load(ROOT/'troops-fixture-source.json'),
        'reader_failure_guards':guards,'candidate_ai_rule_fixture':policy,
        'live_routing_summary':preview['summary'],'closeout':closeout,
        'limitations':['No in-game getter invocation in this milestone; native query bodies execute in an isolated process.',
                       'Native AI wrapper fixture retains controlled stubs; group-query dependency is correlated separately.',
                       'Current live planning exclusion lists are empty; nonempty relation parsing needs live correlation.',
                       'No installed human AI hook, local viewer change, actual movement or two-game synchronization.',
                       'Read-only captures are repeated stable samples, not an atomic/full-world snapshot.'],
        'provenance':[{'path':str(p.relative_to(ROOT.parents[1])), 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]}
target=OUT/'编组归属与控制范围验证证据.json'
target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'result':result['result'],'native_comparisons':native['native_fixture']['native_getter_comparisons'],
                  'routing_checks':policy['total'],'output':str(target)},ensure_ascii=True))

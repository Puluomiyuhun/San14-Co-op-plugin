"""One-time composition correction: install pure forwarding before Session init."""
from pathlib import Path
P=Path(__file__).resolve().parent
for source,target in [('checkpoint_dynamic_native_queue_fixture.inc','checkpoint_persistent_runtime_admission.inc'),('checkpoint_dynamic_planning_fixture_helpers.inc','checkpoint_persistent_runtime_planning.inc')]:
 p=P/target;assert not p.exists()
 text=(P/source).read_text();assert text.count('generationIndex+1')==1
 p.write_text(text.replace('generationIndex+1','generationIndex+2'))
p=P/'checkpoint_persistent_runtime_fixture.cpp';s=p.read_text()
s=s.replace('"checkpoint_dynamic_native_queue_fixture.inc"','"checkpoint_persistent_runtime_admission.inc"').replace('"checkpoint_dynamic_planning_fixture_helpers.inc"','"checkpoint_persistent_runtime_planning.inc"')
s=s.replace('mapping.generation=generationIndex+1','mapping.generation=generationIndex+2')
s=s.replace('        p.initial=logical->RouteGeneration();p.validate=physicalGuard;p.context=&physicalOwner;','        p.validate=physicalGuard;p.context=&physicalOwner;')
s=s.replace('    }else{\n        check(physicalOwner.PublishForOfflineExercise(generationIndex,logical->RouteGeneration()),"owner-controlled fixture generation transition");\n    }','    }')
needle='    check(session.ActivateForOfflineExercise(),"explicit fixture-only activation");'
assert s.count(needle)==1
s=s.replace(needle,needle+'\n    check(physicalOwner.PublishForOfflineExercise(generationIndex+1,logical->RouteGeneration()),"publish only the fully prepared generation after bootstrap");')
s=s.replace('report.transitions==1&&report.generations==2','report.transitions==2&&report.generations==3')
p.write_text(s)
p=P/'checkpoint_persistent_runtime_test.py';s=p.read_text().replace('checkpoint_dynamic_native_queue_fixture.inc','checkpoint_persistent_runtime_admission.inc').replace('checkpoint_dynamic_planning_fixture_helpers.inc','checkpoint_persistent_runtime_planning.inc')
s=s.replace('No game deserialization, full-world/READY proof, actual scheduler handoff, persistent production owner installer or game presentation/input hold.','No game deserialization, full-world/READY proof, actual scheduler handoff, live-game owner installation or game presentation/input hold.')
s=s.replace('and retains them across both fixture generations.','and retains them across both fixture generations. Initial bootstrap forwards without exposing partially initialized Session; fixture publication occurs after Session Initialize/activation.')
p.write_text(s)

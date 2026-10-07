"""Create a four-slot dispatch bridge from the frozen two-slot PE bridge.

The original bridge and its evidence are not modified. No game access.
"""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent
inputs=('checkpoint_push_bridge.h','checkpoint_push_bridge.cpp','checkpoint_push_bridge.asm','checkpoint_push_bridge_fixture.cpp','checkpoint_push_bridge_fixture.asm','checkpoint_push_bridge_fixture_build.cmd')
frozen={name:hashlib.sha256((P/name).read_bytes()).hexdigest() for name in inputs}
header='''#pragma once
#include "checkpoint_push_bridge.h"
// Four immutable dispatch slots; the frame/observer ABI remains identical to
// the frozen two-slot bridge. Originals are never suppressed. No installer.
using CheckpointLoadDispatchBridgeConfig=CheckpointPushBridgeConfig;
using CheckpointLoadDispatchBridgeStats=CheckpointPushBridgeStats;
extern "C" {
int CheckpointLoadDispatchBridgeConfigure(unsigned,const CheckpointLoadDispatchBridgeConfig*) noexcept;
int CheckpointLoadDispatchBridgeSnapshot(unsigned,CheckpointLoadDispatchBridgeStats*) noexcept;
'''+''.join(f'std::uint64_t CheckpointLoadDispatchBridge{i}(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);\n' for i in range(4))+'}\n'
(P/'checkpoint_load_dispatch_bridge.h').write_text(header)
cpp=(P/inputs[1]).read_text().replace('checkpoint_push_bridge.h','checkpoint_load_dispatch_bridge.h').replace('CheckpointPushBridge','CheckpointLoadDispatchBridge')
cpp=cpp.replace('Slot slots[2]{}','Slot slots[4]{}').replace('slot > 1','slot > 3')
old='config->original == reinterpret_cast<void*>(&CheckpointLoadDispatchBridge1) ||'
assert old in cpp
cpp=cpp.replace(old,old+'\n        config->original == reinterpret_cast<void*>(&CheckpointLoadDispatchBridge2) ||\n        config->original == reinterpret_cast<void*>(&CheckpointLoadDispatchBridge3) ||')
(P/'checkpoint_load_dispatch_bridge.cpp').write_text(cpp)
asm=(P/inputs[2]).read_text().replace('CheckpointPushBridge','CheckpointLoadDispatchBridge')
asm=asm.replace('BRIDGE_ENTRY CheckpointLoadDispatchBridge1, 1','BRIDGE_ENTRY CheckpointLoadDispatchBridge1, 1\nBRIDGE_ENTRY CheckpointLoadDispatchBridge2, 2\nBRIDGE_ENTRY CheckpointLoadDispatchBridge3, 3')
(P/'checkpoint_load_dispatch_bridge.asm').write_text(asm)
fixture=(P/inputs[3]).read_text().replace('checkpoint_push_bridge.h','checkpoint_load_dispatch_bridge.h').replace('CheckpointPushBridge','CheckpointLoadDispatchBridge')
fixture=fixture.replace('[2]','[4]').replace('f->slot > 1','f->slot > 3').replace('i<2','i<4').replace('s<2','s<4')
fixture=fixture.replace('void CheckpointPushFixtureOriginal1();','void CheckpointPushFixtureOriginal1();\nvoid CheckpointPushFixtureOriginal2();\nvoid CheckpointPushFixtureOriginal3();')
fixture=fixture.replace('int main() {','int main() {\n    const CheckpointPushEntry entries[]={CheckpointLoadDispatchBridge0,CheckpointLoadDispatchBridge1,CheckpointLoadDispatchBridge2,CheckpointLoadDispatchBridge3};\n    void* originals[]={reinterpret_cast<void*>(&CheckpointPushFixtureOriginal0),reinterpret_cast<void*>(&CheckpointPushFixtureOriginal1),reinterpret_cast<void*>(&CheckpointPushFixtureOriginal2),reinterpret_cast<void*>(&CheckpointPushFixtureOriginal3)};')
fixture=fixture.replace('s ? reinterpret_cast<void*>(&CheckpointPushFixtureOriginal1) : reinterpret_cast<void*>(&CheckpointPushFixtureOriginal0)','originals[s]')
fixture=fixture.replace('s ? CheckpointLoadDispatchBridge1 : CheckpointLoadDispatchBridge0','entries[s]')
fixture=fixture.replace('mode = 1;','check("entry2 unwind", has_unwind(reinterpret_cast<void*>(&CheckpointLoadDispatchBridge2)));\n    check("entry3 unwind", has_unwind(reinterpret_cast<void*>(&CheckpointLoadDispatchBridge3)));\n    for(unsigned extra=2;extra<4;++extra){CheckpointLoadDispatchBridgeStats stats{};check("extra snapshot",CheckpointLoadDispatchBridgeSnapshot(extra,&stats)==1);check("extra slot independent",stats.started==1&&stats.native_started==1&&stats.native_returned==1&&stats.active==0&&stats.abnormal_exits==0);}\n    CheckpointLoadDispatchBridgeConfig rejected{};rejected.original=originals[0];\n    check("reject slot4",CheckpointLoadDispatchBridgeConfigure(4,&rejected)==0);\n    mode = 1;',1)
fixture=fixture.replace('san14.checkpoint-push-bridge-fixture.v1','san14.checkpoint-load-dispatch-bridge-fixture.v1')
(P/'checkpoint_load_dispatch_bridge_fixture.cpp').write_text(fixture)
fixtureasm=(P/inputs[4]).read_text().replace('ORIGINAL CheckpointPushFixtureOriginal1, 1','ORIGINAL CheckpointPushFixtureOriginal1, 1\nORIGINAL CheckpointPushFixtureOriginal2, 2\nORIGINAL CheckpointPushFixtureOriginal3, 3')
(P/'checkpoint_load_dispatch_bridge_fixture.asm').write_text(fixtureasm)
build=(P/inputs[5]).read_text().replace('checkpoint_push_bridge','checkpoint_load_dispatch_bridge').replace('/W4 ','/W4 /WX ')
(P/'checkpoint_load_dispatch_bridge_build.cmd').write_text(build)
(P/'checkpoint_load_dispatch_bridge_origin.json').write_text(json.dumps({'schema':'san14.four-slot-dispatch-bridge-origin.v1','source_sha256':frozen,'note':'Independent names and four immutable slots. Frame ABI and exception behavior unchanged; no live use.'},indent=2)+'\n')
assert frozen=={name:hashlib.sha256((P/name).read_bytes()).hexdigest() for name in inputs}

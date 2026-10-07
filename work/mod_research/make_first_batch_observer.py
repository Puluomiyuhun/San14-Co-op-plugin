"""Build an adaptive four-slot observer without changing previous observers."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
base=(ROOT/'observe_combat_gate.cpp').read_text(encoding='utf-8')
branch=(ROOT/'observe_battle_branches.cpp').read_text(encoding='utf-8')
stage=(ROOT/'observe_stage_path.cpp').read_text(encoding='utf-8')
head=base[:base.index('static bool observe(')].replace('#include <vector>','#include <vector>\n#include <set>')
helpers=branch[branch.index('static void onePair('):branch.index('static bool observe(')]
lists=stage[stage.index('static void inputLists('):stage.index('static void stageSample(')]
main=base[base.index('int wmain('):]
old='''c.Dr0=target; c.Dr6=0;
                        c.Dr7=(c.Dr7&~DWORD64(0xffff00ff))|1;
                        if(!fixtureMode) { c.Dr1=base+0x16C640;c.Dr2=base+0x16C685;c.Dr3=base+0x3F935A;c.Dr7|=started?0x54:0x14; }'''
assert old in main;main=main.replace(old,'armPoints(c,base,target);')
a=main.index('bool ours=');b=main.index('if(ours)',a)
main=main[:a]+'''bool ours=((c.Dr6&1)&&c.Rip==c.Dr0)||(!fixtureMode&&
                            (((c.Dr6&2)&&c.Rip==c.Dr1)||((c.Dr6&4)&&c.Rip==c.Dr2)||((c.Dr6&8)&&c.Rip==c.Dr3)));
                        '''+main[b:]
main=main.replace('bool wasStarted=started;','auto oldEpoch=pointEpoch;')
main=main.replace('if(started) c.Dr7|=0x40;','armPoints(c,base,target);')
main=main.replace('if(!wasStarted && started) {','if(oldEpoch!=pointEpoch) {')
main=main.replace('otherContext.Dr7|=0x40;','armPoints(otherContext,base,target);')
main=main.replace('Arm planning return observation','Rearm adaptive decision points')
source=head+helpers+lists+'\n#include "first_batch_observe.inc"\n'+main
assert 'WriteProcessMemory(' not in source and 'wasStarted' not in source
(ROOT/'observe_first_batch.cpp').write_text(source,encoding='utf-8')
test=(ROOT/'test_combat_gate_observer.py').read_text(encoding='utf-8').replace('observe_combat_gate.exe','observe_first_batch.exe').replace('combat-gate-fixtures.json','first-batch-fixtures.json')
(ROOT/'test_first_batch_observer.py').write_text(test,encoding='utf-8')
# Synthetic memory fixture invokes every production payload path and both adaptive changes.
fixture=(ROOT/'stage_path_payload_fixture.cpp').read_text(encoding='utf-8').replace('observe_stage_path.cpp','observe_first_batch.cpp').replace('stackBytes(0x100)','stackBytes(0x120)')
a=fixture.index('        CONTEXT c{};');b=fixture.index('        std::fclose(log);log=nullptr;',a)
fixture=fixture[:a]+'''        CONTEXT c{};c.Rbx=progress;c.Rsp=stack;c.Rbp=0;c.Rsi=0;c.Rip=base+0x3F9344;
        put<uint8_t>(world+0x38,0);require(!observe(log,GetCurrentProcess(),base,c,1),"early gate");
        armPoints(c,base,base+0x3F9344);require(c.Dr0==base+0x3F9344&&c.Dr2==base+0x16C685,"initial points");
        put<uint8_t>(world+0x38,10);c.Rbp=1;c.Rsi=5;require(!observe(log,GetCurrentProcess(),base,c,1),"scheduled gate");
        armPoints(c,base,base+0x3F9344);require(c.Dr0==base+0x3F935F&&c.Dr2==base+0x16C685,"boundary point switch");
        c.Rip=base+0x16C640;c.Rcx=base+0x1A24CF0;require(!observe(log,GetCurrentProcess(),base,c,1),"entry");
        c.Rip=base+0x16C685;c.Rbx=base+0x1A24CF0;c.Rax=1;require(!observe(log,GetCurrentProcess(),base,c,1),"ready");
        armPoints(c,base,base+0x3F9344);require(c.Dr2==base+0x16AC60,"damage point switch");
        c.Rip=base+0x15C045;c.R15=base+0x1A38840;c.Rbx=address(pair);c.Rbp=1;
        put<uint32_t>(stack+0xA8,1);put<uint32_t>(stack+0xAC,2);require(!observe(log,GetCurrentProcess(),base,c,1),"eligibility");
        c.Rip=base+0x16AC60;c.Rcx=27;c.Rdx=2;c.R8=11;c.R9=27;put<uint32_t>(stack+0x28,1);
        require(!observe(log,GetCurrentProcess(),base,c,1),"damage");
        c.Rip=base+0x3F935F;c.Rbx=progress;c.Rbp=1;put<uint32_t>(progress+0x484,13);
        require(observe(log,GetCurrentProcess(),base,c,1),"boundary stop");
'''+fixture[b:]
fixture=fixture.replace('local synthetic memory and four observation entry paths','local synthetic memory, six event types and two adaptive point changes')
(ROOT/'first_batch_payload_fixture.cpp').write_text(fixture,encoding='utf-8')
runner=(ROOT/'start_battle_branch_observer.py').read_text(encoding='utf-8')
runner=runner.replace('battle-branch-fixtures.json','first-batch-fixtures.json').replace('observe_battle_branches.exe','observe_first_batch.exe')
runner=runner.replace('points = (0x3F9344,0x16C685,0x15C045,0x15C0B0)','points = (0x3F9344,0x3F935F,0x16C640,0x16C685,0x16AC60,0x15C045)')
runner=runner.replace("    run.mkdir()","    payload = json.loads((ROOT/'first-batch-payload-validation.json').read_text())\n    assert payload['result'] == 'PASS'\n    assert diag['world_subday_38'] == 0\n    run.mkdir()")
runner=runner.replace('Hardware execution breakpoints at combat gate, pair rebuild return, per-pair eligibility and phase dispatch. No game code/data writes.','Adaptive four hardware breakpoints: scheduled gate to next phase boundary, entry, build-return to damage, eligibility. No game code/data writes.')
runner=runner.replace('After day12 subday12 gate, 3000 events, or timeout/cancel; native game continues after detach','After first scheduled stage12 completes and stage13 begins, or timeout/cancel; does NOT pause the game')
(ROOT/'start_first_batch_observer.py').write_text(runner,encoding='utf-8')
print('Generated adaptive first-batch observer, tests and bounded runner')

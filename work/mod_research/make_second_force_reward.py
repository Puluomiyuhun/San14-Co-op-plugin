"""Create a separate, fixed Liu Bei reward pilot; never replace earlier evidence."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def adapt(text):
    for a,b in [('+19*8','+13*8'),('+11*8','+2*8'),('+9*8','+2*8'),('+12*8','+2*8'),
                ('666','952'),('83308','20804'),('83208','20704'),('83008','20504'),('15204','4639')]:
        text=text.replace(a,b)
    text=text.replace('city+0x10)!=19','city+0x10)!=13').replace('city+0x30)!=11','city+0x30)!=2')
    text=text.replace('district+0x10)!=12','district+0x10)!=2').replace('owner+0x10)!=12','owner+0x10)!=2')
    text=text.replace('person+0x118)!=9','person+0x118)!=2').replace('d+0x10)==12','d+0x10)==2')
    text=text.replace('district+0x14)!=18','district+0x14)!=10').replace('actionsBefore=18','actionsBefore=10').replace('actionsAfter==17','actionsAfter==9')
    return text

header=(ROOT/'reward_execution_pilot.h').read_text().replace('0x53414E1452455831ULL','0x53414E1452464231ULL')
header=header.replace('PROBE_IDS[3]={97,759,904}','PROBE_IDS[3]={101,264,411}').replace('PROBE_LOYALTY[3]={90,94,92}','PROBE_LOYALTY[3]={93,91,99}')
(ROOT/'second_force_reward_pilot.h').write_text(header)
guard=adapt((ROOT/'reward_execution_guard.inc').read_text())
host='''// This pilot keeps the host's real local player as Zhang Lu (12).
static bool hostGuard() {
    auto root=at<uintptr_t>(gameBase+0x1FCA1E0),world=at<uintptr_t>(root+0x85130);
    auto city=at<uintptr_t>(root+0xDAA8+19*8),district=at<uintptr_t>(root+0xDE40+11*8);
    if(at<uint8_t>(world+0x3A)!=12 || at<uintptr_t>(city)!=gameBase+0x129FD10 ||
       at<uintptr_t>(district)!=gameBase+0x129FEC8 || at<uint16_t>(city+0x10)!=19 ||
       at<uint8_t>(city+0x30)!=11 || at<uint8_t>(district+0x10)!=12 ||
       at<uint32_t>(city+0x34)!=83308 || at<uint32_t>(city+0x3C)!=15204 ||
       at<uint8_t>(district+0x14)!=18) return reject(75);
    return true;
}
'''
guard=guard.replace('static bool guard(void* self) {','static bool guard(void* self) {\n    if(!hostGuard())return false;')
guard=guard.replace('static bool postcheck() {','static bool postcheck() {\n    if(!hostGuard())return false;')
(ROOT/'second_force_reward_guard.inc').write_text(host+guard)
pilot=adapt((ROOT/'reward_execution_pilot.cpp').read_text())
pilot=pilot.replace('reward_execution_pilot.h','second_force_reward_pilot.h').replace('reward_execution_guard.inc','second_force_reward_guard.inc')
pilot=pilot.replace('Fixed three-person test on checkpoint34 only.','Fixed Liu Bei (2) command on Zhang Lu (12) host, checkpoint34 only.')
(ROOT/'second_force_reward_pilot.cpp').write_text(pilot)
fixture=adapt((ROOT/'reward_execution_fixture.cpp').read_text()).replace('reward_execution_pilot.h','second_force_reward_pilot.h')
for a,b in [('district=root+0x8A000+11*0x40','district=root+0x8A000+2*0x40'),
            ('city+0x10,19','city+0x10,13'),('city+0x30,11','city+0x30,2'),('city+0x4E,19','city+0x4E,13'),
            ('ruler+0x11A,19','ruler+0x11A,13'),('district+0x10,12','district+0x10,2'),('district+0x14,18','district+0x14,10'),
            ('person+0x118,9','person+0x118,2'),('root+0xDE40+2*8)+0x10,12','root+0xDE40+2*8)+0x10,2'),
            ('if(test==L"scope-drift")mainNode.value=ref<uintptr_t>(root+0xDE40+2*8);','if(test==L"scope-drift")mainNode.value=ref<uintptr_t>(root+0xDE40+9*8);'),
            ('else if(test==L"foreign-owner")error=14;','else if(test==L"foreign-owner")error=12;')]:
    assert a in fixture,a
    fixture=fixture.replace(a,b)
host_fixture='''    auto hostCity=root+0x98000,hostDistrict=ref<uintptr_t>(root+0xDE40+11*8);
    put<uintptr_t>(root+0xDAA8+19*8,hostCity);put<uintptr_t>(hostCity,base+0x129FD10);
    put<uint16_t>(hostCity+0x10,19);put<uint8_t>(hostCity+0x30,11);put<uint8_t>(hostDistrict+0x10,12);
    put<uint32_t>(hostCity+0x34,83308);put<uint32_t>(hostCity+0x3C,15204);put<uint8_t>(hostDistrict+0x14,18);
'''
fixture=fixture.replace('    auto dll=LoadLibraryW(argv[1]);',host_fixture+'    auto dll=LoadLibraryW(argv[1]);')
fixture=fixture.replace('    if(test==L"cancel")cancel(nullptr);','    if(test==L"host-resource-drift")put<uint32_t>(hostCity+0x34,83208);\n    if(test==L"cancel")cancel(nullptr);')
fixture=fixture.replace('else if(test==L"gold-drift")error=13;','else if(test==L"gold-drift")error=13;\n        else if(test==L"host-resource-drift")error=75;')
(ROOT/'second_force_reward_fixture.cpp').write_text(fixture)
build=(ROOT/'build_reward_execution.cmd').read_text().replace('reward_execution','second_force_reward')
(ROOT/'build_second_force_reward.cmd').write_text(build)
test=(ROOT/'test_reward_execution_fixture.py').read_text().replace('reward_execution_fixture','second_force_reward_fixture').replace('reward-execution-fixtures.json','second-force-reward-fixtures.json')
test=test.replace("'cancel','bad-config')","'cancel','bad-config','host-resource-drift')")
(ROOT/'test_second_force_reward_fixture.py').write_text(test)
print('Generated separate Liu Bei command pilot, native guard and 25 isolated fixture cases')

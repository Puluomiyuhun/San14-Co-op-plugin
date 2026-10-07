"""Reuse verified scheduling with a distinct fixed-command envelope and evidence."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=(ROOT/'run_reward_execution_pilot.py').read_text(encoding='utf-8')
s=s.replace('from reward_preflight import','from authority_reward import')
s=s.replace('from test_reward_execution_fixture import','from test_second_force_reward_fixture import')
s=s.replace('IDS=(97,759,904)','IDS=(101,264,411)')
for a,b in [('reward-execution','second-force-reward'),('reward_execution_pilot.dll','second_force_reward_pilot.dll'),
            ("'city:19'","'city:13'"),("'district:11'","'district:2'"),
            ('83308','20804'),('83008','20504'),('district[4]==17','district[4]==9'),
            ("'actions_before':18,'actions_after':17","'actions_before':10,'actions_after':9"),
            ('0x53414E1452455831','0x53414E1452464231')]:s=s.replace(a,b)
s=s.replace('parser.add_argument(\'--execute\',action=\'store_true\');args=parser.parse_args()',
            'parser.add_argument(\'--execute\',action=\'store_true\');parser.add_argument(\'--command-file\',type=Path);args=parser.parse_args()')
old='context=capture_context(reader);preflight=validate_reward(make_command(context,11,list(IDS)),context,12)'
new='''context=capture_context(reader,2)
        command=make_command(context,2,list(IDS))
        if args.execute:
            require(args.command_file is not None,'Execution requires the separately authorized fixed command file')
            received=load_json(args.command_file)
            require(received==command,'Fixed command or current authoritative context does not match')
        preflight=validate_reward(command,context,2)
        require(preflight['viewer_force_id']==12 and preflight['authorized_force_id']==2,'Actor/viewer mismatch')'''
assert old in s;s=s.replace(old,new)
s=s.replace("return {'focused':focused,'eligibility':eligibility,'records':records,'pools':pools,",
            "return {'focused':focused,'eligibility':eligibility,'records':records,'pools':pools,\n            'global_rng':int.from_bytes(memory.read(memory.base+0x18EB8B0,4),'little'),\n            'world_rng_fields_hex':memory.read(reader.pointer(root+0x85130)+0x450,16).hex(),")
s=s.replace("'stage':'NATIVE_REWARD_EXECUTED_RESTORE_PENDING' if args.execute else 'NATIVE_REWARD_DRY_PASS',",
            "'stage':'NATIVE_SECOND_FORCE_REWARD_EXECUTED_RESTORE_PENDING' if args.execute else 'NATIVE_SECOND_FORCE_REWARD_DRY_PASS',\n                'viewer_force_id':12,'command_force_id':2,'command':command,")
s=s.replace("        print(json.dumps({k:v for k,v in result.items() if k not in ('adapter','effects')},ensure_ascii=True,indent=2))\n        print(json.dumps(comparison,ensure_ascii=True,indent=2))",
            "        print(json.dumps(result,ensure_ascii=True))")
s=s.replace('Development-only fixed reward pilot.','Development-only fixed second-faction reward pilot; the local player stays Zhang Lu.')
(ROOT/'run_second_force_reward.py').write_text(s,encoding='utf-8')
print('Generated dry-first second-force runner with fixed command-file verification')

from pathlib import Path
P=Path(__file__).resolve().parent
s=(P/'checkpoint_cc_file_start.py').read_text(encoding='utf8')
for a,b in [('checkpoint_cc_file_probe','checkpoint_cc_publish'),('checkpoint_cc_file_fixture_gate','checkpoint_cc_publish_gate'),
            ('checkpoint_cc_file_runs','checkpoint_cc_publish_runs'),('checkpoint_cc_file_', 'checkpoint_cc_publish_'),
            ('CheckpointCcFile','CheckpointCcPublish'),('0x53414E1443434631','0x53414E1443435031'),
            ('--read','--execute'),('args.read','args.execute'),('args.absent','False'),
            ('san14.checkpoint-cc-file-live.v1','san14.checkpoint-cc-publish-live.v1'),('san14.checkpoint-cc-file-once.v1','san14.checkpoint-cc-publish-once.v1')]:s=s.replace(a,b)
s=s.replace("    mode.add_argument('--absent', action='store_true')\n",'')
s=s.replace("requested_mode=2 if False else int(args.execute)","requested_mode=int(args.execute)")
s=s.replace("mode_name='absent' if False else 'read' if args.execute else 'dry'", "mode_name='publish' if args.execute else 'dry'")
s=s.replace("class Report(C.Structure):", """class PublishPart(C.Structure):
    _fields_=[(k,C.c_uint32) for k in ('state','osError','exceptionCode','existsCalls','writeAttempts','writeReturned','nativeWriteReturn','intentCreated','intentDurable','localPinReleased','sourceMatched','matched','publishAttempts','reserved')]
    _fields_ += [('writeMethod',C.c_uint64),('sourceSha256',C.c_ubyte*32),('stage',C.c_char*64)]

class Report(C.Structure):""")
s=s.replace("    _fields_ += [(k, C.c_uint32) for k in ('bridgeDrainedSnapshot', 'modulePinned', 'nativeLoadAuthorized', 'fullWorldVerified')]", "    _fields_ += [(k, C.c_uint32) for k in ('bridgeDrainedSnapshot', 'modulePinned', 'nativeLoadAuthorized', 'fullWorldVerified')]\n    _fields_ += [('publish',PublishPart)]")
s=s.replace('C.sizeof(Report) == 520','C.sizeof(Report) == 680 and C.sizeof(PublishPart)==160')
s=s.replace('report.size == 520','report.size == 680')
s=s.replace('    return value\n\n\ndef load(',"""    part=report.publish
    value['publish']={k:getattr(part,k) for k,_ in PublishPart._fields_}
    value['publish']['sourceSha256']=bytes(part.sourceSha256).hex()
    value['publish']['stage']=part.stage.decode('ascii')
    return value


def load(""")
s=s.replace('    if not mode:\n', '''    p=r['publish']
    if not mode:
        if any(p[k] for k in ('writeAttempts','intentCreated','intentDurable','publishAttempts','matched','writeMethod')):return False
''')
a=s.index('    if mode==2:');b=s.index("    return (r['verifyAttempts']",a)
s=s[:a]+'''    if not (p['state']==5 and p['osError']==p['exceptionCode']==p['reserved']==0 and p['existsCalls']==3
        and all(p[k]==1 for k in ('writeAttempts','writeReturned','nativeWriteReturn','intentCreated','intentDurable','localPinReleased','sourceMatched','matched','publishAttempts'))
        and p['writeMethod']>=0x10000 and p['sourceSha256']==SHA and p['stage']=='published_and_observed_twice'):
        return False
'''+s[b:]
a=s.index('        if requested_mode==1:');b=s.index('        # Exact probe binary/source fixtures',a)
s=s[:a]+'''        binding=load(ROOT/'checkpoint_cc_publish_binding.json')
        stage=load(ROOT/'checkpoint_cc_stage_result.json')
        assert stage['result']=='PASS' and sha(ROOT/'checkpoint_cc_stage_result.json')==binding['stage_sha256']
        assert stage['target']==str(TARGET) and stage['target_sha256']==sha(TARGET)==SHA
        assert not os.path.lexists(binding['intent']),'Native publication intent already consumed'
'''+s[b:]
s=s.replace("        assert (sha(TARGET)==SHA) if requested_mode==1 else not os.path.lexists(TARGET)", '        assert sha(TARGET)==SHA')
s=s.replace("            'native_absence_observed_twice':bool(passed and False), 'target':str(TARGET),", "            'native_publish_complete':bool(passed and args.execute), 'target':str(TARGET),")
s=s.replace("'game_file_writes_requested': False", "'game_file_writes_requested':bool(args.execute)")
s=s.replace("'native_load_requested': False})", "'native_load_requested': False,'native_write_requested':bool(args.execute)})")
s=s.replace("'source_known_coverage': source_coverage,", "'source_known_coverage': source_coverage, 'stage_receipt_sha256':binding['stage_sha256'], 'native_intent':binding['intent'],")
with (P/'checkpoint_cc_publish_start.py').open('x',encoding='utf8') as f:f.write(s)
print('Created scoped publisher launcher; no game access.')

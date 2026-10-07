from pathlib import Path
P=Path(__file__).resolve().parent
s=(P/'native_file_identity_start.py').read_text(encoding='utf8')
for a,b in [('native_file_identity_probe','checkpoint_cc_file_probe'),('native_file_identity_fixture_gate','checkpoint_cc_file_fixture_gate'),
            ('native_file_identity_runs','checkpoint_cc_file_runs'),('native_file_identity_', 'checkpoint_cc_file_'),
            ('NativeFileIdentity','CheckpointCcFile'),('0x53414E1446494431','0x53414E1443434631'),
            ('remote\\mppush01.s14','remote\\svdexccSC03.s14'),('san14.native-file-identity-live.v1','san14.checkpoint-cc-file-live.v1'),
            ('san14.native-file-read-once.v1','san14.checkpoint-cc-file-once.v1')]:s=s.replace(a,b)
a=s.index('def precheck(reader):');b=s.index('\n\ndef get_report(',a)
s=s[:a]+'''def precheck(reader):
    from checkpoint_load_mode_capture import snapshot
    before=snapshot(reader)
    handoff=load(ROOT/'checkpoint_load_mode_verified_handoff.json')
    old=load(handoff['mode_result'])
    assert old['result']=='PASS' and sha(handoff['mode_result'])==handoff['mode_result_sha256']
    for key,value in handoff['current_game'].items():
        assert before[key]==value, ('Planning attachment changed',key)
    assert before['cache_graph']==handoff['current_cache_graph']
    archive=load(ARCHIVE_RESULT)
    assert sha(archive['archive'])==archive['sha256']==SHA
    image=(ROOT/'game-runtime-image.bin').read_bytes()
    assert hashlib.sha256(image).hexdigest()=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
    for rva,size in ((0x2FCB90,0x30),(0x3A90C0,0x1C0)):
        assert reader.memory.read(reader.memory.base+rva,size)==image[rva:rva+size]
    return before
'''+s[b:]
s=s.replace("'state': 5 if mode else 4", "'state': 5 if mode else 4")
s=s.replace("    return (r['verifyAttempts'] == 1", """    if mode==2:
        return (r['stage']=='native_absence_observed_twice' and r['contextCalls']==1
            and r['existsCalls']==r['sizeCalls']==2 and r['sizes'][0]<=0 and r['sizes'][1]<=0 and r['sizes'][2]==0
            and r['readReturns']==[0,0] and all(r[k]==0 for k in ('verifyAttempts','readCalls','identityMatched','verifiedSize','localPinReleased')))
    return (r['verifyAttempts'] == 1""")
s=s.replace("    mode.add_argument('--read', action='store_true')", "    mode.add_argument('--read', action='store_true')\n    mode.add_argument('--absent', action='store_true')")
s=s.replace("    args = p.parse_args()", "    args = p.parse_args()\n    requested_mode=2 if args.absent else int(args.read)\n    mode_name='absent' if args.absent else 'read' if args.read else 'dry'")
s=s.replace('args.dry or args.read','args.dry or args.read or args.absent')
s=s.replace('if args.read:\n            assert args.dry_evidence','if requested_mode:\n            assert args.dry_evidence')
s=s.replace("'read' if args.read else 'dry'", 'mode_name')
s=s.replace("mode_name='absent' if args.absent else mode_name", "mode_name='absent' if args.absent else 'read' if args.read else 'dry'")
s=s.replace('int(args.read)','requested_mode')
s=s.replace('requested_mode=2 if args.absent else requested_mode','requested_mode=2 if args.absent else int(args.read)')
# Exact local presence is checked in this launcher before any hook and again on return.
s=s.replace('        # Exact probe binary/source fixtures', '''        if requested_mode==1:
            stage=load(ROOT/'checkpoint_cc_stage_result.json')
            assert stage['result']=='PASS' and stage['target']==str(TARGET) and stage['target_sha256']==SHA
            assert sha(TARGET)==SHA
        else:
            assert not os.path.lexists(TARGET),'CC target is not physically empty'
        # Exact probe binary/source fixtures''')
s=s.replace("        save(run / 'trace.json', trace)", "        save(run / 'trace.json', trace)\n        assert (sha(TARGET)==SHA) if requested_mode==1 else not os.path.lexists(TARGET)")
s=s.replace("'two_observed_native_reads_matched': bool(passed and args.read),", "'two_observed_native_reads_matched': bool(passed and args.read),\n            'native_absence_observed_twice':bool(passed and args.absent), 'target':str(TARGET),")
s=s.replace("        stream.write('\\n')", "        stream.write('\\n')\n        stream.flush()\n        os.fsync(stream.fileno())")
with (P/'checkpoint_cc_file_start.py').open('x',encoding='utf8') as f:f.write(s)
print('Created independent CC launcher; no game access.')

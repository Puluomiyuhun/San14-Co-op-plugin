"""Offline candidate-site and historical-stack audit, never a live installer."""
from pathlib import Path
import collections,hashlib,json,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'python_deps'))
import capstone
image=(ROOT/'game-runtime-image.bin').read_bytes()
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
anchors=[(0x1ab6f4,'call',0x1a1c10,'person_text_scope'),
         (0x2d9243,'jmp',0x3aa3f0,'expression_percentage_tail'),
         (0x2d9261,'jmp',0x3aa7c0,'expression_range_tail'),
         (0x3b3774,'call',0x3aa7c0,'voice_variant')]
sites=[]
for address,op,target,label in anchors:
    ins=next(md.disasm(image[address:address+5],address))
    assert ins.size==5 and ins.mnemonic==op and int(ins.op_str,16)==target
    sites.append({'rva':hex(address),'instruction':f'{ins.mnemonic} {ins.op_str}',
                  'bytes':ins.bytes.hex(),'return_or_next_rva':hex(address+5),'role':label})
source=ROOT/'rng-domain-classification-l.json'
domains=json.loads(source.read_text())
audits={}
for run,data in domains.items():
    counts=collections.Counter();cross=collections.Counter();events=[]
    for row in data['events']:
        frames=row['frames']
        if '0x3b3779' in frames:route='voice_candidate'
        elif '0x1ab6f9' in frames:route='text_scope_candidate'
        else:route='native_or_unknown'
        assert not (row['group']=='other_message_context' and route!='native_or_unknown')
        assert not (row['group']=='person_line_subtree' and route=='native_or_unknown')
        counts[route]+=1;cross[f"{row['group']} -> {route}"]+=1
        events.append({'seq':row['seq'],'route':route,'group':row['group'],
                       'message_id':row['message_id'],'writer_pc':frames[0]})
    audits[run]={'counts':dict(counts),'cross_classification':dict(cross),'events':events}
assert audits['camera-near-rng-k2']['counts']=={
    'native_or_unknown':86,'text_scope_candidate':33,'voice_candidate':25}
report={'status':'OFFLINE_CANDIDATE_AUDIT_NOT_INSTALLED','sites':sites,
        'source_classification_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'historical_coverage':audits,
        'policy':{'scope':'Only synchronous descendants of call 1AB6F4 to 1A1C10.',
                  'exclude':'UI callbacks and voice call before/after text scope; other message paths remain native.',
                  'voice':'Separate experimental candidate at 3B3774, not a whole-voice-manager scope.',
                  'default':'Unknown expression contexts stay native.',
                  'logic_seed':'Keep native 18EB8B0 for logic and read-only consumers.'},
        'limits':['Historical stack classification is not observation of an installed wrapper.',
                  'Captured writes exclude zero-draw calls (e.g. range bound below two) and uncaptured paths.',
                  'Far trace has three known state gaps; this audit does not classify their absent writers.',
                  'Indirect callbacks, asynchronous descendants, and transitive side effects are not exhaustively audited.',
                  'Adding a DLL wrapper changes timing and stack shape. These fixtures do not validate live patch installation.',
                  'Original A first-batch skip remains unexplained.']}
(ROOT/'rng-route-site-audit-m.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'sites':sites,'coverage':{k:v['counts'] for k,v in audits.items()}}))

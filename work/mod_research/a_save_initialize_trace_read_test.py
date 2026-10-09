"""Owned-file and explicit process-double tests; no game discovery or access."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import a_save_initialize_trace_read as r


def packet(**changes):
    values=dict.fromkeys(r.FIELDS,0)
    values.update(size=144,version=1,pid=123,thread=7,controller=1,owner=2,base=0x10000,
                  root=0x20000,world=0x30000,stage=46,input_menu_command=-1)
    values.update(changes)
    return r.FORMAT.pack(*(values[k] for k in r.FIELDS))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-record',type=Path,required=True)
    parser.add_argument('--dll',type=Path,required=True)
    args=parser.parse_args()
    folder=r.PRIVATE/'a_save_initialize_trace_read_test_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
    result=dict(result='FAIL',cases=[],game_access=False,native_calls=0,process_double=True)
    def case(name,fn):
        try:fn();result['cases'].append(dict(case=name,passed=True))
        except Exception as exc:result['cases'].append(dict(case=name,passed=False,error=repr(exc)))
    def expect_refusal(fn,text):
        try:fn()
        except RuntimeError as exc:assert text in str(exc)
        else:raise AssertionError('Expected refusal')
    def native():
        raw=args.native_record.read_bytes();value=r.decode_pair(raw,raw)
        assert value['status']=='FIRST_FAILURE_OBSERVED'
        assert value['first_failure']['stage']==46
        assert value['first_failure']['input_error']==7 and value['first_failure']['input_decision']==0
        assert value['first_failure']['input_menu_command']==-1
        assert value['first_failure']['input_stack_count']==5 and value['first_failure']['input_user_phase']==2
        result['native_decoded']=value
    case('real_owned_native_DATA_cross_language',native)
    def pe():
        layout=r.export_layout(args.dll,r.digest(args.dll));assert layout['size']==144
        result['export_rva']=layout['rva']
    case('actual_compiled_DATA_export',pe)
    def not_published():
        assert r.decode_pair(packet(stage=0,a=4),packet(stage=0,a=5))['status']=='NOT_PUBLISHED'
    case('stage_zero_is_never_success',not_published)
    def unstable():
        assert r.decode_pair(packet(stage=0),packet())['status']=='UNSTABLE'
        assert r.decode_pair(packet(a=3),packet(a=4))['status']=='UNSTABLE'
    case('partial_or_changed_publication_is_unstable',unstable)
    case('unknown_stage_refused',lambda:expect_refusal(lambda:r.decode_pair(packet(stage=999),packet(stage=999)),'Unknown'))
    case('wrong_size_refused',lambda:expect_refusal(lambda:r.decode_pair(packet()[:-1],packet()[:-1]),'Incomplete'))
    case('wrong_version_refused',lambda:expect_refusal(lambda:r.decode_pair(packet(version=2),packet(version=2)),'ABI'))
    with tempfile.TemporaryDirectory() as temporary:
        temp=Path(temporary);game=temp/'owned-image';dll=temp/'owned-module'
        game.write_bytes(b'owned fake process image');dll.write_bytes(b'owned fake DLL')
        class Process:
            def __init__(self,pid):self.closed=False;self.observations=0;self.pages=[]
            def identity(self):self.observations+=1;return 456,game
            def modules(self):return [(0x10000,game),(0x40000,dll)]
            def read(self,address,size):return bytes(64) if address==0x40000 else packet(pid=self.record_pid)
            def data_page(self,*args):self.pages.append(args)
            def close(self):self.closed=True
            record_pid=123
        layout=dict(rva=0x1000,size=144,headers=bytes(64),image_base_offset=16)
        def observed(bad=False):
            process=Process(123);process.record_pid=124 if bad else 123
            try:
                with patch.object(r,'export_layout',return_value=layout):
                    value=r.observe(123,456,0x10000,0x20000,0x30000,0x40000,dll,r.digest(dll),
                                    process_factory=lambda pid:process,image_sha=r.digest(game))
                assert not bad and value['status']=='FIRST_FAILURE_OBSERVED' and value['native_calls']==value['writes']==0
                assert len(process.pages)==2 and value['first_failure']['input_menu_command']==-1
            finally:assert process.closed
        case('scoped_double_read_and_close',observed)
        case('foreign_record_rejected_and_handle_closed',lambda:expect_refusal(lambda:observed(True),'another attachment'))
        def wide_pid():
            def forbidden(pid):raise AssertionError('Out-of-range PID opened a process')
            with patch.object(r,'export_layout',return_value=layout):
                expect_refusal(lambda:r.observe(2**32+123,456,0x10000,0x20000,0x30000,0x40000,dll,r.digest(dll),
                    process_factory=forbidden,image_sha=r.digest(game)),'bounded attachment')
        case('oversized_pid_refused_before_open',wide_pid)
    paths=[Path(__file__),Path(r.__file__),r.P/'a_save_failure_diagnostic.py',args.native_record,args.dll]
    result['pins']={str(p.resolve()):r.digest(p) for p in paths}
    result['result']='PASS' if len(result['cases'])==10 and all(c['passed'] for c in result['cases']) else 'FAIL'
    output=folder/'result.json';output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(result=result['result'],path=str(output),sha256=r.digest(output))))
    return 0 if result['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())

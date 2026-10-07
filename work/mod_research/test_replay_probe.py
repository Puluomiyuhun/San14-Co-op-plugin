import json,struct,subprocess,tempfile
from pathlib import Path
from test_submit_probe import ROOT,FLAGS,wait_json

def run_case(substitute):
    with tempfile.TemporaryDirectory(dir=ROOT,prefix='replay-test-') as directory:
        root=Path(directory);ready=root/'ready.json';go=root/'go';log=root/'trace.jsonl'
        expected=[0]*26;expected[0]=666;expected[2]=1000;expected[15]=20
        replacement=expected.copy();replacement[2]=1300
        (root/'expected.bin').write_bytes(struct.pack('<26I',*expected))
        (root/'recorded.bin').write_bytes(struct.pack('<26I',*replacement))
        command=[str(ROOT/'submit_probe_fixture.exe'),str(ready),str(go)]
        if substitute:command.append('1000')
        fixture=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=FLAGS)
        tracer=None
        try:
            info=wait_json(ready)
            tracer=subprocess.Popen([str(ROOT/'replay_submit.exe'),str(info['pid']),hex(info['base']),hex(info['rva']),'10',str(log),str(root/'expected.bin'),str(root/'recorded.bin')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=FLAGS)
            wait_json(log,'armed')
            go.write_text('go')
            out,err=tracer.communicate(timeout=15)
            rows=[json.loads(line) for line in log.read_text().splitlines()]
            assert tracer.returncode==(0 if substitute else 1),(rows,err)
            if substitute:
                assert any(row['event']=='recorded_command_substituted' for row in rows)
                assert rows[-1]['registers_restored'] is True
            else:
                assert not any(row['event']=='recorded_command_substituted' for row in rows)
                assert rows[-1]=={'event':'error_cleanup','registers_restored':True,'detached':True}
            output,error=fixture.communicate(timeout=5)
            assert fixture.returncode==0,(output,error)
            original=json.loads(output)
            assert original=={'calls':1,'original_function_returned':True}
            return {'case':'substitute-recorded-command' if substitute else 'reject-live-parameter-mismatch',
                    'result':'PASS','trace':rows,'fixture':original}
        finally:
            if tracer and tracer.poll() is None:tracer.wait(timeout=20)
            if fixture.poll() is None:fixture.terminate();fixture.wait(timeout=5)

if __name__=='__main__':
    report=[run_case(True),run_case(False)]
    (ROOT/'replay-probe-self-test.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

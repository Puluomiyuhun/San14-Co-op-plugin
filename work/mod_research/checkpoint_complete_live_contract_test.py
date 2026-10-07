"""Cross-language ABI verification plus corrupted-report refusal, without game access."""
import ctypes as C
from datetime import datetime
import hashlib,json,re,subprocess,unittest
from pathlib import Path
import checkpoint_complete_live_owner_contract as abi
from checkpoint_live_prefetch_contract import HardwareReceipt
P=Path(__file__).resolve().parent

def cpp_probe():
    types=[(abi.Config,'checkpoint_complete_live_owner::Config'),(abi.Report,'checkpoint_complete_live_owner::Report'),
        (abi.Description,'checkpoint_complete_live_owner::Description'),
        (abi.ModuleApproval,'checkpoint_live_storage_binding::ModuleApproval'),
        (abi.Endpoint,'checkpoint_live_storage_binding::Endpoint'),
        (abi.BytesReceipt,'checkpoint_cc_load_observer::Report'),
        (abi.LifecycleReceipt,'checkpoint_cc_load_lifecycle::Report'),
        (abi.IdentityReceipt,'checkpoint_title_identity_adapter::Report'),
        (HardwareReceipt,'checkpoint_native_input_hwbp::HardwareReceipt')]
    source=['#include "checkpoint_complete_live_owner.h"','#include "checkpoint_cc_load_observer.h"',
        '#include "checkpoint_cc_load_lifecycle.h"','#include "checkpoint_title_identity_adapter.h"',
        '#include "checkpoint_native_input_hwbp.h"','#include <cstdio>','int main(){']
    expected={}
    for typ,cpp in types:
        source.append(f'printf("{typ.__name__}.sizeof %zu\\n",sizeof({cpp}));')
        expected[typ.__name__+'.sizeof']=C.sizeof(typ)
        for field,_ in typ._fields_:
            source.append(f'printf("{typ.__name__}.{field} %zu\\n",offsetof({cpp},{field}));')
            expected[typ.__name__+'.'+field]=getattr(typ,field).offset
    source+=['return 0;}']
    cpp_path=P/'checkpoint_complete_live_abi_verify.cpp';cpp_path.write_text('\n'.join(source)+'\n')
    build=P/'checkpoint_complete_live_abi_verify.cmd'
    build.write_text('@echo off\ncall "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul\nif errorlevel 1 exit /b 1\npushd "%~dp0"\ncl /nologo /std:c++17 /EHa /W4 /WX /MT /O2 /Fe:checkpoint_complete_live_abi_verify.exe /Fo:checkpoint_complete_live_abi_verify.obj checkpoint_complete_live_abi_verify.cpp\nset taskExit=%errorlevel%\npopd\nexit /b %taskExit%\n')
    proc=subprocess.run(['cmd','/c',str(build)],cwd=P,capture_output=True);assert proc.returncode==0,proc.stdout+proc.stderr
    values=subprocess.check_output([str(P/'checkpoint_complete_live_abi_verify.exe')],text=True)
    actual={line.split()[0]:int(line.split()[1]) for line in values.splitlines()}
    assert actual==expected,(set(actual.items())^set(expected.items()))
    h=(P/'checkpoint_complete_live_owner.h').read_text()
    enum=re.search(r'enum class Value:unsigned\s*\{([^}]+)\}',h,re.S).group(1)
    names=tuple(n.strip() for n in enum.split(',') if n.strip()!='Count')
    assert names==abi.VALUE_NAMES and len(set(names))==len(names)
    return len(expected)

class ContractTests(unittest.TestCase):
    def make(self):
        r=abi.Report();r.magic=abi.MAGIC;r.size=C.sizeof(r);r.version=abi.VERSION
        return r
    def test_value_order_is_not_deduplicated(self):
        r=self.make()
        for i in range(len(abi.VALUE_NAMES)):r.value[i]=1000+i
        out=abi.decode_report(bytes(r))
        self.assertEqual([out[n] for n in abi.VALUE_NAMES],list(range(1000,1130)))
    def test_nested_identity_bytes_are_decoded_without_pointer_reads(self):
        r=self.make();b=abi.BytesReceipt();b.version=1;b.size=C.sizeof(b);b.token=0x1122334455667788
        b.sha256[:]=bytes(range(32));r.bytesReceipt[:]=bytes(b)
        t=abi.IdentityReceipt();t.version=1;t.size=C.sizeof(t);t.target.force=0x1234567887654321
        t.target.person=0x8765432112345678;t.worldForceAfter=2;t.worldControlAfter=1;r.identityReceipt[:]=bytes(t)
        out=abi.decode_report(bytes(r))
        self.assertEqual(out['bytes']['token'],b.token)
        self.assertEqual(out['bytes']['sha256'],bytes(range(32)).hex())
        self.assertEqual(out['identity']['target'],dict(force=t.target.force,person=t.target.person))
        self.assertEqual(out['identity']['worldControlAfter'],1)
    def test_wrong_report_header_refuses(self):
        r=self.make();r.version+=1
        with self.assertRaises(ValueError):abi.decode_report(bytes(r))
    def test_wrong_nested_header_refuses(self):
        r=self.make();r.bytesReceipt[0]=1
        with self.assertRaises(ValueError):abi.decode_report(bytes(r))
    def test_unknown_description_reserved_refuses(self):
        d=abi.Description();d.magic=abi.MAGIC;d.size=C.sizeof(d);d.version=1
        d.configSize=abi.CONFIG_SIZE;d.reportSize=abi.REPORT_SIZE;d.valueCount=len(abi.VALUE_NAMES);d.reserved=1
        with self.assertRaises(ValueError):abi.decode_description(bytes(d))
    def test_truncated_report_refuses(self):
        with self.assertRaises(ValueError):abi.decode_report(bytes(self.make())[:-1])

if __name__=='__main__':
    fields=cpp_probe();suite=unittest.defaultTestLoader.loadTestsFromTestCase(ContractTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    folder=P/'checkpoint_complete_live_contract_tests'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
    record=dict(result='PASS' if result.wasSuccessful() else 'FAIL',cross_language_fields=fields,
        enum_values=len(abi.VALUE_NAMES),tests=result.testsRun,game_access=False,
        contract_sha256=hashlib.sha256((P/'checkpoint_complete_live_owner_contract.py').read_bytes()).hexdigest())
    (folder/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(**record,path=str(folder/'result.json'))))
    raise SystemExit(0 if result.wasSuccessful() else 1)

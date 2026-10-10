"""Read-only approval of one three-slot Runtime/publisher/source bundle.
No game discovery, process opening, legacy-build fallback or installation.
"""
import ctypes as C
import json
from pathlib import Path
from a_save_runtime_control import require,sha
import a_save_three_runtime_contract as wire
import a_save_three_repeat_contract as repeat
P=Path(__file__).resolve().parent

def _read(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def _schema(value,types):
    require(set(value['structures'])==set(types),'Native ABI structures differ')
    for name,kind in types.items():
        row=value['structures'][name]
        require(row['size']==C.sizeof(kind) and set(row['fields'])=={n for n,_ in kind._fields_},'Native ABI differs: '+name)
        for name,typ in kind._fields_:
            field=row['fields'][name]
            require(field['offset']==getattr(kind,name).offset and field['size']==C.sizeof(typ),'Native field differs: '+name)
            if 'count' in field:
                require(field['count']==(typ._length_ if issubclass(typ,C.Array) else 1),'Native field count differs: '+name)

def verify_native_build(args):
    folder=Path(args.build_run).resolve(strict=True);value=_read(folder/'result.json')
    require(value.get('schema')=='san14.a-three-runtime-exports-build.v1' and value.get('result')=='PASS' and
        value.get('abi_magic')==wire.MAGIC and value.get('capacity')==3 and value.get('schema_fields_verified') is True and
        value.get('production_abi_executed') is True,'Dedicated three-slot production build required')
    sources=value.get('sources',{});generated=value.get('generated_sources',{});artifacts=value.get('artifacts',{})
    require(all(type(x) is dict and x for x in (sources,generated,artifacts)),'Complete build source/artifact closure required')
    required=('a_save_three_exports_build.py','a_save_three_exports_sources.py','a_save_three_runtime_contract.py',
              'a_native_turn_runtime.cpp','a_native_turn_runtime.h','a_native_turn_exports.cpp','a_save_repeat_publish.cpp')
    for n in required:require(str(P/n) in sources,'Missing production source: '+n)
    for name,h in sources.items():
        p=Path(name);require(p.is_absolute() and p.parent==P and p.is_file() and sha(p)==h,'Production source drift: '+name)
    for name,h in generated.items():
        p=Path(name).resolve(strict=True);require(p.is_relative_to(folder/'src') and sha(p)==h,'Generated source drift: '+name)
    for name,h in artifacts.items():
        p=(folder/name).resolve(strict=True);require(not Path(name).is_absolute() and p.is_relative_to(folder) and sha(p)==h,'Build artifact drift: '+name)
    def item(key):
        row=value[key];p=Path(row['path']).resolve(strict=True)
        require(p.is_relative_to(folder) and artifacts.get(str(p.relative_to(folder)))==row['sha256'] and sha(p)==row['sha256'],
            'Bundle component differs: '+key)
        return p
    dll=item('production_dll');dep=item('dependency_dll');publisher=item('publisher')
    require(dll.name=='a_save_local_runtime.dll' and dep.name=='checkpoint_planning_hold.dll' and publisher.name=='publisher.exe',
        'Production component names differ')
    _schema(_read(item('schema_snapshot')),wire.TYPES);_schema(_read(item('schema_repeat')),repeat.TYPES)
    for key in ('repeat_abi_checks','publisher_checks','native_three_checks'):
        proof=_read(item(key));require(proof.get('result')=='PASS','Required owned check failed: '+key)
    require(_read(item('repeat_abi_checks'))['dll_sha256']==value['production_dll']['sha256'],'Repeat ABI checked another DLL')
    require(Path(args.publisher_build).resolve(strict=True)==publisher.parent,'Old or foreign publisher folder')
    require(Path(args.repeat_abi_run).resolve(strict=True)==item('repeat_abi_checks').parent,'Old or foreign repeat ABI folder')
    return (dict(production=dict(binaries={dll.name:sha(dll),dep.name:sha(dep)}),approved_three_bundle=value),
            item('schema_snapshot').parent,dict(binaries={publisher.name:sha(publisher)}))

"""Read the initialization first-error DATA export; never execute target code."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import struct
import sys

P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps')]
from a_save_failure_diagnostic import ReadOnlyProcess,digest
from a_save_runtime_control import require

FORMAT=struct.Struct('<4I8Q2Q3Ii5I4xIi')
FIELDS=('size version pid thread controller owner base root world a b c '
        'input_stack_count input_queue_count input_error input_decision input_stage input_menu_command '
        'input_user_phase input_game_transition input_load_queued input_advance input_panel_advance exception_code stage').split()
EXPORT=b'ASaveInitializeFirstFailure'
GAME_SHA='42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
STAGES={1:'initialize_config',2:'initialize_clean',3:'initialize_claim_fallback',4:'initialize_date_exception',
        10:'read_owner_binding',11:'read_current_controller',12:'read_date_changed',13:'read_date_exception',
        14:'read_reward_snapshot',15:'read_hook_shape',16:'read_hook_entry',17:'read_live_slot',18:'read_slot_exception',
        30:'claim_owner_binding',31:'claim_quiet',32:'claim_retired',33:'claim_binding',34:'claim_date',
        35:'claim_already_owned',36:'claim_period_thread_or_date',40:'fresh_missing_sampler',41:'fresh_date',
        42:'fresh_sampler_refused',43:'fresh_source_identity',44:'fresh_reward_endpoint',45:'fresh_adapter_bind',
        46:'fresh_inspector',47:'fresh_exception'}


def decode_pair(first,second):
    require(len(first)==len(second)==FORMAT.size,'Incomplete initialization DATA')
    a,b=(dict(zip(FIELDS,FORMAT.unpack(x))) for x in (first,second))
    require(all(x['size']==FORMAT.size and x['version']==1 for x in (a,b)),'Initialization DATA ABI differs')
    require(all(x['stage'] in (0,*STAGES) for x in (a,b)),'Unknown initialization failure stage')
    if a['stage']==b['stage']==0:return dict(status='NOT_PUBLISHED',first_failure=None)
    if first!=second:return dict(status='UNSTABLE',first_failure=None)
    return dict(status='FIRST_FAILURE_OBSERVED',stage_name=STAGES[b['stage']],first_failure=b)


def export_layout(path,expected_sha):
    import pefile
    require(digest(path)==expected_sha,'Initialization DLL identity differs')
    pe=pefile.PE(str(path))
    try:
        require(pe.FILE_HEADER.Machine==0x8664 and pe.OPTIONAL_HEADER.Magic==0x20b,'x64 PE32+ required')
        rows=[s for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name==EXPORT]
        require(len(rows)==1 and not rows[0].forwarder,'Unique initialization DATA export required')
        rva=rows[0].address
        sections=[s for s in pe.sections if s.VirtualAddress<=rva and rva+FORMAT.size<=s.VirtualAddress+s.Misc_VirtualSize]
        require(len(sections)==1,'Initialization DATA is outside one section')
        flags=sections[0].Characteristics
        require(flags&0x40000000 and flags&0x80000000 and not flags&0x20000000,'Initialization export is not readable non-executable DATA')
        require(rva%8==0 and rva+FORMAT.size<=pe.OPTIONAL_HEADER.SizeOfImage,'Initialization DATA range/alignment differs')
        size=pe.OPTIONAL_HEADER.SizeOfHeaders
        require(0<size<=65536,'Unbounded PE headers')
        return dict(rva=rva,size=FORMAT.size,headers=pe.__data__[:size],
                    image_base_offset=pe.OPTIONAL_HEADER.get_field_absolute_offset('ImageBase'))
    finally:pe.close()


def observe(pid,birth,base,root,world,module,dll,dll_sha,*,process_factory=ReadOnlyProcess,image_sha=GAME_SHA):
    dll=Path(dll).resolve(strict=True);layout=export_layout(dll,dll_sha)
    require(all(type(x) is int and 0<x<2**64 for x in (pid,birth,base,root,world,module)) and
            pid<2**32,'Explicit bounded attachment required')
    process=process_factory(pid)
    try:
        actual_birth,image=process.identity()
        require(actual_birth==birth and digest(image)==image_sha,'Unexpected process incarnation/image')
        def check():
            require(process.identity()==(birth,image),'Process identity changed')
            modules=process.modules()
            require((base,image) in modules and [(b,p) for b,p in modules if b==module or p==dll]==[(module,dll)],'Loaded image or exact DLL changed')
            headers=layout['headers'];rebased=bytearray(headers)
            struct.pack_into('<Q',rebased,layout['image_base_offset'],module)
            require(process.read(module,len(headers)) in (headers,bytes(rebased)),'Loaded DLL headers differ')
            process.data_page(module+layout['rva'],FORMAT.size,module)
        check()
        first=process.read(module+layout['rva'],FORMAT.size);second=process.read(module+layout['rva'],FORMAT.size)
        check()
        require(digest(dll)==dll_sha and digest(image)==image_sha,'Identity files changed during read')
        result=decode_pair(first,second);record=result['first_failure']
        if record is not None:
            require((record['pid'],record['base'],record['root'],record['world'])==(pid,base,root,world) and
                    record['thread']>0 and record['controller']>0 and record['owner']>0,'Initialization record is from another attachment')
        result.update(pid=pid,birth=birth,module=module,dll_sha256=dll_sha,export_rva=layout['rva'],
                      raw_samples=[first.hex(),second.hex()],native_calls=0,writes=0,
                      restore_permission=False,retry_permission=False,save_accepted=False)
        return result
    finally:process.close()


def read_json(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def observe_run(run):
    run=Path(run).resolve(strict=True);capture=read_json(run/'capture.json');plan=read_json(run/'002-Plans-decoded.json')
    c=capture['planning'];pid,birth,base=(c[k] for k in ('pid','birth','base'))
    require((plan['pid'],plan['birth'],plan['base'])==(pid,birth,base),'Run plan/capture attachment differs')
    claim=read_json(PRIVATE/'a_save_runtime_live_claims'/f'{pid}-{birth}.json')
    require(Path(claim['run']).resolve(strict=True)==run and (claim['pid'],claim['birth'],claim['nonce'])==
            (pid,birth,plan['nonce']),'Run claim differs; never create or reset it')
    result=observe(pid,birth,base,c['root'],c['world'],plan['module'],run/'a_save_local_runtime.dll',claim['dll_sha256'])
    result['source_sha256']=digest(Path(__file__))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--observe',action='store_true');parser.add_argument('--run',type=Path)
    args=parser.parse_args()
    if not args.observe:parser.print_help();return 0
    if args.run is None:parser.error('--run required')
    folder=PRIVATE/'a_save_initialize_trace_read_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
    try:result=observe_run(args.run)
    except Exception as exc:result=dict(status='READ_REFUSED',error=repr(exc),native_calls=0,writes=0)
    path=folder/'result.json';path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],path=str(path),sha256=digest(path))))
    return 0 if result['status'] in ('FIRST_FAILURE_OBSERVED','NOT_PUBLISHED') else 1


if __name__=='__main__':raise SystemExit(main())

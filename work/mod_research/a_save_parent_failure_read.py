"""Explicit RPM-only parent-initialization diagnosis for the pinned A Runtime.

Default help. --observe is performed only by the live coordinator. No exports
are called, no debugger attached, no memory written, no once claim created.
"""
import argparse
import ctypes as C
from datetime import datetime
import json
from pathlib import Path
import struct
import sys

P = Path(__file__).resolve().parent
PRIVATE = P.parents[2] / 'mod_research'
sys.path[:0] = [str(PRIVATE / 'python_deps')]
from a_save_failure_diagnostic import ReadOnlyProcess, MemoryPage, digest, export_layout
from a_save_runtime_control import require

DLL_SHA = '8125ec17de92bd46f9fcda780008990b5c8c1b9456630f895de8bb39886054cb'
LAYOUT = PRIVATE / 'a_save_parent_failure_layout_runs/20261009-222350-412512/layout.json'
LAYOUT_SHA = '7a90099ca6313310ea9386226476f7d737ecbb845816baa2ccddda71686855ec'
RUNTIME_POINTER_RVA = 0x60f08
GAME_SHA = '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def layout():
    require(digest(LAYOUT) == LAYOUT_SHA, 'Exact owned MSVC layout required')
    x = read_json(LAYOUT)
    require(x['Runtime']['_size'] == 18232 and x['Runtime']['controller_']['offset'] == 12456 and
            x['Controller']['r_'] == dict(offset=136, size=2032), 'Bounded layout differs')
    return x


def scalar_fields(data, table):
    result = {}
    for name, span in table.items():
        if name == '_size' or span['size'] not in (1, 2, 4, 8):
            continue
        begin, size = span['offset'], span['size']
        require(begin + size <= len(data), 'Incomplete report')
        result[name] = int.from_bytes(data[begin:begin+size], 'little')
    return result


def decode_runtime(data, schema):
    require(len(data) == schema['Runtime']['_size'], 'Wrong Runtime size')
    start = schema['Runtime']['controller_']['offset'] + schema['Controller']['r_']['offset']
    cr = data[start:start + schema['ControllerReport']['_size']]
    answer = {'controller': scalar_fields(cr, schema['ControllerReport'])}
    for field, name in (('reward', 'RewardReport'), ('owner', 'OwnerReport'), ('gate', 'GateReport')):
        item = schema['ControllerReport'][field]
        answer[field + '_cached'] = scalar_fields(cr[item['offset']:item['offset']+item['size']], schema[name])
    start = schema['Runtime']['host_']['offset'] + schema['Host']['r_']['offset']
    answer['host'] = scalar_fields(data[start:start+schema['HostReport']['_size']], schema['HostReport'])
    c = answer['controller']
    if not c['initialized'] and c['error'] == 1:
        stage = 'CONTROLLER_INITIALIZE_READ_OR_CLEAN_OR_CLAIM_REJECTED'
    elif not c['initialized'] and c['error'] == 3:
        stage = 'CONTROLLER_INITIALIZE_DATE_READ_EXCEPTION_AFTER_CLAIM'
    elif c['initialized']:
        stage = 'CONTROLLER_REQUEST_OR_LATER_INITIALIZATION_REJECTED'
    else:
        stage = 'NOT_LOCALIZED_BY_RETAINED_REPORT'
    answer['localization'] = stage
    answer['limitation'] = 'Controller cached subreports reflect its last read, not a new live Snapshot. Config error merges read/clean/ClaimController; no exact fresh Inspector predicate is stored.'
    return answer


def observe(run, *, process_factory=ReadOnlyProcess):
    run = Path(run).resolve(strict=True)
    schema = layout()
    capture = read_json(run/'capture.json'); before = capture['preflight']
    plan = read_json(run/'002-Plans-decoded.json')
    result = read_json(run/'result.json')
    require(result['cleanup_verified'] is True and result['sources_restored'] is True and not result['real_fresh_save'],
            'Only the already restored no-save failure is in scope')
    pid, birth, base, module = before['pid'], before['birth'], before['base'], plan['module']
    require(type(pid) is int and 0 < pid < 2**32 and type(birth) is int and birth > 0 and
            (plan['pid'], plan['birth'], plan['base']) == (pid, birth, base), 'Invalid exact attachment')
    dll = (run/'a_save_local_runtime.dll').resolve(strict=True)
    pe_layout = export_layout(dll, DLL_SHA)
    import pefile
    pe = pefile.PE(str(dll))
    try:
        symbols = {s.name:s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
        require(symbols[b'ASaveRuntimeSnapshot'] == 0x104b0, 'Snapshot export differs')
        references = {0xc12d: bytes.fromhex('48833dd34d050000'), 0xfc80: bytes.fromhex('488b0d81120500')}
        for rva, code in references.items():
            require(pe.get_data(rva, len(code)) == code, 'Runtime singleton reference differs')
        require(0xc135+0x54dd3 == RUNTIME_POINTER_RVA == 0xfc87+0x51281, 'Independent singleton references disagree')
    finally:
        pe.close()
    process = process_factory(pid)
    try:
        image_path = process.identity()[1]
        require(digest(image_path) == GAME_SHA, 'Unexpected game image identity')
        def identity():
            require(process.identity() == (birth, image_path), 'Process incarnation changed')
            modules = process.modules()
            require((base, image_path) in modules and [(b,p) for b,p in modules if b == module or p == dll] == [(module,dll)],
                    'Exact image/module attachment differs')
            original = pe_layout['headers']; rebased = bytearray(original)
            struct.pack_into('<Q',rebased,pe_layout['image_base_offset'],module)
            require(process.read(module,len(original)) in (original,bytes(rebased)), 'Loaded module headers differ')
            for rva, code in references.items():
                require(process.read(module+rva,len(code)) == code, 'Loaded singleton references differ')
            process.data_page(module+RUNTIME_POINTER_RVA,8,module)
        identity()
        pointer = process.read(module+RUNTIME_POINTER_RVA,8)
        runtime = struct.unpack('<Q',pointer)[0]
        require(runtime and runtime % 8 == 0, 'Missing aligned Runtime')
        # Readable heap range only. Never treat an arbitrary remote pointer as code.
        page = MemoryPage()
        require(process.k.VirtualQueryEx(process.handle,runtime,C.byref(page),C.sizeof(page)) == C.sizeof(page) and
                page.State == 0x1000 and page.Type == 0x20000 and page.Protect in (0x04,0x08) and
                runtime+schema['Runtime']['_size'] <= page.BaseAddress+page.RegionSize, 'Runtime is not one readable private allocation range')
        first = process.read(runtime,schema['Runtime']['_size'])
        second = process.read(runtime,schema['Runtime']['_size'])
        require(first == second, 'Runtime changed during bounded two-read diagnosis')
        require(struct.unpack_from('<I',first,0)[0] == pid and struct.unpack_from('<Q',first,8)[0] == birth and
                struct.unpack_from('<Q',first,16)[0] == base, 'Runtime Config is from another attachment')
        require(process.read(module+RUNTIME_POINTER_RVA,8) == pointer, 'Runtime pointer changed')
        identity()
        require(digest(dll) == DLL_SHA and digest(image_path) == GAME_SHA, 'Files changed during read')
        return dict(result='PASS_READ_ONLY_PARENT_FAILURE_OBSERVATION',pid=pid,birth=birth,base=base,module=module,
                    runtime=runtime,runtime_pointer_rva=RUNTIME_POINTER_RVA,dll_sha256=DLL_SHA,layout_sha256=LAYOUT_SHA,
                    decoded=decode_runtime(first,schema),raw_runtime=first.hex(),native_calls=0,writes=0,
                    restore_permission=False,retry_permission=False,source_sha256=digest(Path(__file__)))
    finally:
        process.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observe',action='store_true');parser.add_argument('--run',type=Path)
    args=parser.parse_args()
    if not args.observe:
        parser.print_help();return 0
    if not args.run:parser.error('--run required')
    out=PRIVATE/'a_save_parent_failure_read_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    try: result=observe(args.run)
    except Exception as error: result=dict(result='FAIL_READ_ONLY',error=repr(error),native_calls=0,writes=0)
    path=out/'result.json'
    with path.open('x',encoding='utf-8',newline='\n') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(result=result['result'],path=str(path),sha256=digest(path))))
    return 0 if result['result'].startswith('PASS_') else 1


if __name__=='__main__':raise SystemExit(main())

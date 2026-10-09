"""Read-only files/build preflight for the existing two-load diagnostic.

No PID, process reader, native call, claim, staging write or execution callback
is accepted here. Success is not permission to execute and does not prove the
archives' internal gameplay contents. With no arguments, only help is printed.
"""
import argparse
from contextlib import ExitStack
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
from pathlib import Path

from b_warm_coordinator import approved_component, validate_pair
from b_warm_profile_capture import profile_from_dict, integer
import b_warm_staging as files

# Exact frozen storage_bindings build profile. Copied data only: importing that
# module would also import process-memory capability code. Tests AST-check parity.
STEAM_HASHES = {
    'steam_api64.dll': 'e61ac9a9ac216d56abc70aaeefedc11708ef45aa1aa48f1dd313adfd9aa99150',
    'steamclient64.dll': '52ff7a513f8d5913a185ac8820eadb17d6e8e4144cd8fff36cc5bae6fa9d3fee',
}


def need(ok, text):
    if not ok: raise ValueError(text)


def dll_identity(path):
    """Read a pinned ordinary file in bounded chunks (Steam DLL may exceed 16MiB)."""
    path=files.clean_path(path)
    with ExitStack() as held:
        files.pin_parents(held,path)
        handle=held.enter_context(files.Handle(path))
        before=handle.info();size=(before.sizeHigh<<32)|before.sizeLow
        need(0<size<=256*1024*1024,'DLL size out of bounds')
        buf=C.create_string_buffer(1024*1024);digest=hashlib.sha256();remaining=size
        while remaining:
            count=min(remaining,len(buf));done=W.DWORD()
            need(files.kernel().ReadFile(handle.value,buf,count,C.byref(done),None) and done.value==count,
                 'Short DLL read')
            digest.update(buf.raw[:count]);remaining-=count
        after=handle.info();need(files.identity(before)==files.identity(after),'DLL changed during read')
        return dict(path=str(path),size=size,sha256=digest.hexdigest(),file_id=files.identity(after))


def preflight(plan_path, *, helper_build, helper_sha256, pair_build, pair_sha256):
    plan_path=files.clean_path(plan_path)
    plan_identity,raw=files.read_file(plan_path)
    need(len(raw)<=256*1024,'Plan too large')
    plan=json.loads(raw.decode('utf-8-sig'))
    need(type(plan) is dict and set(plan)=={'profiles','target','second_source','expected_ruler','steam_paths'},
         'Exact two-file plan required')
    need(type(plan['profiles']) is list and len(plan['profiles'])==2,'Exactly two profiles required')
    profiles=[profile_from_dict(p) for p in plan['profiles']];validate_pair(profiles)
    integer(plan['expected_ruler'],1,5999)
    target=files.clean_path(plan['target']);second=files.clean_path(plan['second_source'])
    need(target.name==files.NAME,'First file must already occupy exact native CC03 name')
    identity1,_=files.read_file(target);identity2,_=files.read_file(second)
    for index,identity in enumerate((identity1,identity2)):
        p=profiles[index]
        need((identity['size'],identity['sha256'])==(p.file.size,bytes(p.file.sha256).hex()),
             'First staged file differs' if index==0 else 'Second source file differs')
    need(identity1['file_id'][:3]!=identity2['file_id'][:3],'Two file paths must not alias')
    steam=plan['steam_paths']
    need(type(steam) is dict and set(steam)==set(STEAM_HASHES),'Exact two Steam module paths required')
    steam_rows={}
    for name,digest in STEAM_HASHES.items():
        p=files.clean_path(steam[name]);need(p.name==name,'Steam filename differs')
        row=dll_identity(p);need(row['sha256']==digest,'Unapproved Steam file: '+name)
        steam_rows[name]=row
    helper_path=Path(helper_build).resolve(strict=True);pair_path=Path(pair_build).resolve(strict=True)
    helper=approved_component(helper_path,helper_sha256,'san14.b-warm-coordinator.v1')
    pair=approved_component(pair_path,pair_sha256,'san14.b-warm-factory-pair.v1')
    for name,digest in helper['sources'].items():
        if Path(name).suffix in ('.cpp','.h'):
            need(pair['sources'].get(name)==digest,'Pair/helper native handover source differs')
    components={}
    for name,path,result,h in (('helper',helper_path,helper,helper_sha256),('pair',pair_path,pair,pair_sha256)):
        dll=Path(result['production_dll']['path']).resolve(strict=True);digest=result['production_dll']['sha256']
        need(dll.is_relative_to(path.parent) and result['binaries'].get(str(dll))==digest and
             hashlib.sha256(dll.read_bytes()).hexdigest()==digest,'Production DLL outside verified output closure')
        components[name]=dict(result_path=str(path),result_sha256=h,production_dll=dict(path=str(dll),sha256=digest))
    # Recheck plan and both saves after the potentially longer build-closure
    # reads. No lock/claim persists after returning: runtime must still recheck.
    need(files.read_file(plan_path)[0]==plan_identity and files.read_file(target)[0]==identity1 and
         files.read_file(second)[0]==identity2,'Plan/files changed during preflight')
    normalized={**plan,'target':str(target),'second_source':str(second),
                'steam_paths':{name:row['path'] for name,row in steam_rows.items()}}
    return dict(result='PASS_LOCAL_PAIR_PREFLIGHT',normalized_plan=normalized,
        plan_path=str(plan_path),plan_sha256=plan_identity['sha256'],
        profiles_blob_sha256=[hashlib.sha256(bytes(p)).hexdigest() for p in profiles],
        files=dict(first=identity1,second=identity2),steam_files=steam_rows,**components,
        game_checks_pending=True,no_execute_authority=True,game_access=False,claims_created=False,
        files_staged=False,native_load_permitted=False,archive_content_semantics_verified=False,
        pending=['fresh process incarnation and prior-attempt exclusion','actual planning/source fingerprints',
                 'actual loaded Steam modules and storage bindings','two native loads and complete retirement'])


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path)
    for name in ('helper','pair'):
        parser.add_argument('--'+name+'-build',type=Path);parser.add_argument('--'+name+'-sha256')
    args=parser.parse_args(argv)
    if args.plan is None:parser.print_help();return 0
    result=preflight(args.plan,helper_build=args.helper_build,helper_sha256=args.helper_sha256,
                     pair_build=args.pair_build,pair_sha256=args.pair_sha256)
    print(json.dumps(result,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())

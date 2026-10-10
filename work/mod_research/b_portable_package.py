"""Build the narrow B portable pilot with its pinned pure-Python PE dependency.

No downloads, interpreter, game files, Steam modules, saves, keys or claims are
included. Native producer approvals remain required. Receipt bytes remain
unchanged producer evidence, not successful execution on a recipient computer.
Default help is inert; output directory and zip must both be new.
"""
from copy import deepcopy
from pathlib import Path,PurePosixPath
import argparse,base64,csv,hashlib,io,json,stat

import b_portable_release_export as collector
from portable_release import Release,write_bundle,archive,relative,need

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
DEFAULT_DEPS=ROOT.parent/'mod_research/python_deps'
DIST='pefile-2024.8.26.dist-info'
RECORD_SHA='205c7f87f390aa481931feb76e7b83fca76f9accbb03e4f7fc0e7fbbff5e1e77'
PYTHON_FILES={'pefile.py','peutils.py','ordlookup/__init__.py','ordlookup/oleaut32.py','ordlookup/ws2_32.py','ordlookup/wsock32.py'}
METADATA_FILES={DIST+'/'+n for n in ('INSTALLER','LICENSE','METADATA','RECORD','REQUESTED','WHEEL','top_level.txt')}
EXPECTED=PYTHON_FILES|METADATA_FILES
IGNORED_PYC={'__pycache__/pefile.cpython-311.pyc','__pycache__/peutils.cpython-311.pyc',
    *(f'ordlookup/__pycache__/{n}.cpython-311.pyc' for n in ('__init__','oleaut32','ws2_32','wsock32'))}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def _file(root,name):
    relative('deps/'+name);path=root.joinpath(*PurePosixPath(name).parts)
    current=root
    for part in PurePosixPath(name).parts:
        current=current/part;info=current.lstat()
        need(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&0x400,'Dependency reparse path refused')
    need(path.resolve(strict=True).is_relative_to(root) and path.is_file(),'Dependency file escapes input root')
    return path


def collect_dependencies(directory=DEFAULT_DEPS):
    """Use pinned distribution RECORD, not a recursive site-packages copy."""
    root=Path(directory).resolve(strict=True)
    record=_file(root,DIST+'/RECORD');raw=record.read_bytes()
    need(sha(raw)==RECORD_SHA,'Unexpected pefile distribution RECORD')
    rows={};ignored=set();assets=[]
    for row in csv.reader(io.StringIO(raw.decode('utf-8'))):
        need(len(row)==3,'Malformed pefile RECORD row');name,digest,size=row
        need(name not in rows and name not in ignored,'Duplicate dependency record path')
        if name in IGNORED_PYC:
            need(digest==size=='','Unexpected compiled cache record');ignored.add(name);continue
        need(name in EXPECTED,'Unreviewed distribution file');rows[name]=(digest,size)
    need(set(rows)==EXPECTED and ignored==IGNORED_PYC,'Incomplete pefile distribution manifest')
    for name,(digest,size) in sorted(rows.items()):
        p=_file(root,name);data=p.read_bytes();actual=sha(data)
        if name==DIST+'/RECORD':need(digest==size=='' and actual==RECORD_SHA,'RECORD self identity differs')
        else:
            need(size.isdecimal() and int(size)==len(data) and digest.startswith('sha256='),'Dependency size or digest missing')
            expected=base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode('ascii')
            need(digest=='sha256='+expected,'Dependency bytes differ from distribution RECORD: '+name)
        assets.append(dict(source=p,path='deps/'+name,sha256=actual,role='dependency'))
    metadata=_file(root,DIST+'/METADATA').read_text(encoding='utf-8')
    need('\nName: pefile\n' in metadata and '\nVersion: 2024.8.26\n' in metadata and '\nLicense: MIT\n' in metadata,
         'Pinned dependency identity differs')
    return dict(assets=assets,metadata=dict(distribution='pefile',version='2024.8.26',license='MIT',
        producer_record_sha256=RECORD_SHA,record='deps/'+DIST+'/RECORD',license_file='deps/'+DIST+'/LICENSE',
        file_count=len(assets),python_only=True,downloaded=False))


def assemble(spec,*,destination,zip_path,python_deps=DEFAULT_DEPS):
    destination=Path(destination);zip_path=Path(zip_path)
    need(not destination.exists() and not zip_path.exists(),'Package output directory and zip must both be fresh')
    need(not zip_path.resolve().is_relative_to(destination.resolve()),'Zip must be outside the package directory')
    selected=collector.collect(spec,extra_sources=[HERE/'b_portable_guest.py',HERE/'b_portable_approval.py'])
    deps=collect_dependencies(python_deps);metadata=deepcopy(selected['metadata'])
    # Preserve the conservative all-branches AST inventory from the collector.
    # These extra packages belong to dormant research/A-server branches; the B
    # recipient entry does not enable those branches or claim they are bundled.
    metadata['bundled_dependencies']=[deps['metadata']]
    metadata['recipient_runtime']=dict(entry='repo/work/mod_research/b_portable_guest.py',
        python='CPython 3.11+ Windows x64, supplied by recipient',interpreter_bundled=False,
        enabled_external_modules=['pefile','peutils','ordlookup'],
        inactive_branch_external_modules=['capstone','cryptography','unicorn'],
        default_help_inert=True,requires_separate_trusted_manifest_sha256=True,
        requires_fresh_local_configuration=True,keys_included=False,game_access=False,
        recipient_native_execution_verified=False)
    made=write_bundle(destination,[*selected['assets'],*deps['assets']],metadata)
    release=Release(made['root'],made['manifest_sha256']);zip_path.parent.mkdir(parents=True,exist_ok=True)
    packed=archive(release,zip_path)
    return dict(result='B_PORTABLE_PACKAGE_CREATED',**made,archive=packed,
        dependencies=deps['metadata'],game_access=False,native_installed=False,
        recipient_native_execution_verified=False,requires_fresh_local_configuration=True)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--spec',type=Path)
    parser.add_argument('--output',type=Path);parser.add_argument('--zip',type=Path);parser.add_argument('--python-deps',type=Path,default=DEFAULT_DEPS)
    args=parser.parse_args(argv)
    if args.spec is None and args.output is None and args.zip is None:parser.print_help();return 0
    if any(x is None for x in (args.spec,args.output,args.zip)):parser.error('--spec, --output and --zip required together')
    result=assemble(json.loads(args.spec.read_text(encoding='utf-8-sig')),destination=args.output,zip_path=args.zip,python_deps=args.python_deps)
    print(json.dumps(result,ensure_ascii=False));return 0


if __name__=='__main__':raise SystemExit(main())

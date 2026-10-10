"""Collect an approved B release without game files or machine credentials.

Only explicit build receipts and the repository's reviewed sources are inputs.
The four original result.json files are producer provenance, never proof that a
different computer has installed or executed anything. No record is rebased or
rewritten. This collector never opens a game, Steam module, save, key or claim.
The bundle writer checks every selected byte again before copying it.
"""
from pathlib import Path
import argparse,ast,hashlib,json,sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT.parent/'mod_research/python_deps'),str(ROOT/'outputs/san14-link')]
from b_remote_session import REQUIRED_SOURCES,approved_builds
from b_reward_native_port import NativeBuild,approved_build
from player_input_lease_bootstrap_port import Build as InputBuild,approved as approve_input
from b_warm_rules_factory import RulesBuild

SCHEMA='san14.b-portable-export.v1'
KIND='san14.b-portable-assets.v1'
SOURCE_SUFFIXES={'.py','.cpp','.h','.asm','.inc','.cmd'}
EXTERNAL_MODULES={'capstone','cryptography','pefile','unicorn'}
FIELDS={'schema','pair','helper','reward','input','rules'}
DYNAMIC_SOURCES={'checkpoint_live_capture.py':'checkpoint-coverage-hex.py'}


def need(ok,message):
    if not ok:raise ValueError(message)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def _absolute(value):
    need(type(value) is str and Path(value).is_absolute(),'Explicit absolute source path required')
    return Path(value).resolve(strict=True)
def _digest(value):
    need(type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value),'Exact SHA256 required')
    return value


def validate_spec(value):
    need(type(value) is dict and set(value)==FIELDS and value['schema']==SCHEMA,'Exact B export build specification required')
    result={}
    for name in ('pair','helper','reward','input'):
        row=value[name];field='result' if name in ('pair','helper') else 'run'
        need(type(row) is dict and set(row)=={field,'sha256'},'Exact component input required: '+name)
        path=_absolute(row[field]);digest=_digest(row['sha256'])
        record=path if field=='result' else path/'result.json'
        need(record.is_file() and record.name=='result.json' and sha(record)==digest,'Producer receipt identity differs: '+name)
        result[name]=dict(path=path,record=record,sha256=digest)
    row=value['rules'];need(type(row) is dict and set(row)=={'stage','publisher'},'Exact rules paths required')
    result['rules']={name:_absolute(row[name]) for name in ('stage','publisher')}
    return result


def _source(path):
    p=Path(path).resolve(strict=True)
    need(p.is_relative_to(ROOT) and p.suffix in SOURCE_SUFFIXES and p.is_file(),'Only repository source files are exportable')
    # Only the existing executable-source trees, never fixtures/saves, .local,
    # configs, keys, raw archives or arbitrary repository resources.
    need(p.is_relative_to(HERE) or p.is_relative_to(ROOT/'outputs/san14-link'),'Source lies outside reviewed source trees')
    return p


def python_closure(seeds):
    """Static all-branches import closure; no importing legacy tools to scan them.

    Keep the one established file-loader dependency explicitly, and reject new
    unresolved dynamic imports. Inclusion does not invoke diagnostic functions.
    """
    directories=(HERE,ROOT/'outputs/san14-link');index={}
    for directory in directories:
        for p in directory.glob('*.py'):index.setdefault(p.stem,[]).append(p)
    pending=[_source(p) for p in seeds];seen={};external=set();dynamic=[]
    while pending:
        p=pending.pop();need(p.suffix=='.py','Python dependency seed required')
        if p in seen:continue
        raw=p.read_bytes();seen[p]=hashlib.sha256(raw).hexdigest()
        tree=ast.parse(raw.decode('utf-8-sig'),filename=str(p))
        imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):imports.extend(a.name.split('.')[0] for a in node.names)
            elif isinstance(node,ast.ImportFrom):
                need(node.level==0,'Unreviewed relative import in B runtime')
                if node.module:imports.append(node.module.split('.')[0])
            elif isinstance(node,ast.Call):
                if isinstance(node.func,ast.Name) and node.func.id=='__import__':
                    need(node.args and isinstance(node.args[0],ast.Constant) and type(node.args[0].value) is str,
                         'Unresolved dynamic module import')
                    imports.append(node.args[0].value.split('.')[0])
                elif isinstance(node.func,ast.Attribute) and node.func.attr in ('import_module','spec_from_file_location','run_path'):
                    wanted=DYNAMIC_SOURCES.get(p.name)
                    need(node.func.attr=='spec_from_file_location' and wanted is not None and len(node.args)==2 and
                         isinstance(node.args[1],ast.BinOp) and isinstance(node.args[1].op,ast.Div) and
                         isinstance(node.args[1].left,ast.Name) and node.args[1].left.id=='ROOT' and
                         isinstance(node.args[1].right,ast.Constant) and node.args[1].right.value==wanted,
                         'Unreviewed dynamic source import: '+p.name)
                    target=_source(p.parent/wanted);pending.append(target)
                    dynamic.append(dict(source='repo/'+p.relative_to(ROOT).as_posix(),line=node.lineno,
                                        target='repo/'+target.relative_to(ROOT).as_posix()))
        for name in imports:
            if name in index:
                need(len(index[name])==1,'Ambiguous flat Python module: '+name);pending.append(_source(index[name][0]))
            elif name not in sys.stdlib_module_names:
                need(name in EXTERNAL_MODULES,'Unreviewed external Python dependency: '+name);external.add(name)
    return seen,sorted(external),dynamic


def collect(spec,*,extra_sources=()):
    """Return selected assets/metadata for portable_release.write_bundle.

    extra_sources is a trusted local caller's explicit repository Python entry
    list; its transitive source closure is still validated. No config field can
    request arbitrary copied files. External Python wheels are a separate step.
    """
    s=validate_spec(spec)
    pair,helper=approved_builds(s['pair']['path'],s['pair']['sha256'],s['helper']['path'],s['helper']['sha256'])
    reward=approved_build(NativeBuild(s['reward']['path'],s['reward']['sha256']))
    input_path,input_sha=approve_input(InputBuild(s['input']['path'],s['input']['sha256']))
    rules=RulesBuild(s['rules']['stage'],s['rules']['publisher']);rules.check()
    records={name:json.loads(v['record'].read_text(encoding='utf-8-sig')) for name,v in s.items() if name!='rules'}
    assets={};source_pins={};components={}
    def add(source,path,expected,role):
        source=Path(source).resolve(strict=True);need(sha(source)==expected,'Selected export file changed')
        row=dict(source=source,path=path,sha256=expected,role=role)
        old=assets.setdefault(path,row);need(old==row,'Conflicting portable asset path')
        return path
    def source_asset(p,expected):
        p=_source(p);rel='repo/'+p.relative_to(ROOT).as_posix()
        add(p,rel,expected,'source');old=source_pins.setdefault(rel,expected);need(old==expected,'Source hash conflict')
        return rel
    # Preserve every original self-authored source required by native approval,
    # without copying generated/native dump/private/fixture binary closures.
    for name,record in records.items():
        component_sources={}
        for source,expected in record['sources'].items():
            p=Path(source);rel=source_asset(p if p.is_absolute() else HERE/p,expected)
            need(rel not in component_sources,'Duplicate original component source')
            component_sources[rel]=expected
        v=s[name];rel=add(v['record'],'native/'+name+'/result.json',v['sha256'],'provenance')
        components[name]=dict(producer_provenance=rel,producer_result_sha256=v['sha256'],
                              source_pins=dict(sorted(component_sources.items())),
                              producer_approval_verified=True,recipient_native_execution_verified=False)
    def native(name,path,digest,basename):
        p=Path(path);need(p.name==basename,'Unexpected approved native component: '+name)
        return add(p,'native/'+name+'/'+basename,digest,'native')
    for name,value,basename in (('pair',pair,'checkpoint_complete_live_owner_v2.dll'),('helper',helper,'coordinator.dll')):
        row=value['production_dll'];components[name].update(family=value['family'],
            production_dll=native(name,row['path'],row['sha256'],basename),production_sha256=row['sha256'])
    need([p.name for p in reward['dependencies']]==['checkpoint_planning_hold.dll'],'Unexpected B reward DLL dependency set')
    components['reward'].update(family='san14.b-reward-owner.v1',
        production_dll=native('reward',reward['dll'],reward['sha256'],'b_reward_owner.dll'),production_sha256=reward['sha256'],
        dependencies=[dict(path=native('reward',p,sha(p),'checkpoint_planning_hold.dll'),sha256=sha(p)) for p in reward['dependencies']])
    components['input'].update(family='san14.player-input-lease-bootstrap.v1',
        production_dll=native('input',input_path,input_sha,'player_input_lease_bootstrap.dll'),production_sha256=input_sha)
    components['rules']=dict(stage=native('rules',rules.stage,rules.stage_sha,'production.dll'),
        publisher=native('rules',rules.publisher,rules.publisher_sha,'publisher-production.exe'),
        stage_sha256=rules.stage_sha,publisher_sha256=rules.publisher_sha,
        fixed_rules_build_verified=True,recipient_native_execution_verified=False)
    seeds=[HERE/'b_simple_remote_guest.py',HERE/'b_portable_release_export.py',*(HERE/n for n in REQUIRED_SOURCES),*extra_sources]
    runtime,external,dynamic=python_closure(seeds)
    for p,h in runtime.items():source_asset(p,h)
    # Last reread makes collection fail on mixed source/result/native versions;
    # the writer is additionally required to recheck before copying.
    for row in assets.values():need(sha(row['source'])==row['sha256'],'Export input drifted during approval')
    metadata=dict(kind=KIND,entry='repo/work/mod_research/b_simple_remote_guest.py',components=components,
        source_pins=dict(sorted(source_pins.items())),runtime_sources=sorted('repo/'+p.relative_to(ROOT).as_posix() for p in runtime),
        python_paths=['repo/work/mod_research','repo/outputs/san14-link'],dynamic_sources=dynamic,
        external_dependencies=dict(python='CPython 3.10+ Windows x64',modules=external,bundled=False),
        producer_approval=dict(pair_helper='b_remote_session.approved_builds',reward='b_reward_native_port.approved_build',
            input='player_input_lease_bootstrap_port.approved',rules='b_warm_rules_factory.RulesBuild.check'),
        producer_provenance_only=True,recipient_native_execution_verified=False,
        game_access=False,steam_access=False,save_access=False,keys_included=False,claims_included=False,
        install_permission=False,two_real_clients_verified=False)
    return dict(assets=[assets[k] for k in sorted(assets)],metadata=metadata)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--spec',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args(argv)
    if args.spec is None and args.output is None:parser.print_help();return 0
    if args.spec is None or args.output is None:parser.error('--spec and --output required together')
    selection=collect(json.loads(args.spec.read_text(encoding='utf-8-sig')))
    from portable_release import write_bundle
    result=write_bundle(args.output,selection['assets'],selection['metadata'])
    print(json.dumps(dict(result='B_RELEASE_EXPORTED',**result,native_installed=False),default=str));return 0


if __name__=='__main__':raise SystemExit(main())

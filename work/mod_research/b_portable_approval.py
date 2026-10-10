"""Explicit, process-exclusive file approval bindings for a selected B release.

These are producer-verified-release views, not re-execution of historical native
tests on the recipient. The original result bytes stay unchanged. No filesystem
API, process function, live module approval, claim, Steam or native ABI check is
replaced. Enter only around the retained B check/Runner lifetime; never around
the producer collector. Runtime records and persistent claim roots are supplied
separately by the local entry, outside this immutable release.
"""
from copy import deepcopy
from pathlib import Path
import sys
import threading

from portable_release import Release,need,sha,hex_digest
import b_remote_session as session
import b_observed_start as startup
import b_reward_runner as runner
import b_simple_remote_guest as guest
import b_warm_coordinator as coordinator
import b_reward_native_port as reward
import player_input_lease_bootstrap_port as inputs

FAMILIES={'pair':'san14.b-warm-refresh-pair.v1','helper':'san14.b-warm-coordinator.v1',
          'reward':'san14.b-reward-owner.v1','input':'san14.player-input-lease-bootstrap.v1'}
NAMES={'pair':'checkpoint_complete_live_owner_v2.dll','helper':'coordinator.dll',
       'reward':'b_reward_owner.dll','input':'player_input_lease_bootstrap.dll'}
_EXCLUSIVE=threading.Lock()
# Include the star-imported alias on b_reward_runner, even though its current
# run() calls startup.preflight whose globals remain b_observed_start.
_BINDINGS=((session,'verify_sources','sources'),(startup,'verify_sources','sources'),
           (runner,'verify_sources','sources'),(guest,'verify_sources','sources'),
           (coordinator,'approved_component','component'),(reward,'approved_build','reward'),
           (inputs,'approved','input'))
_ORIGINALS=tuple((module,name,getattr(module,name)) for module,name,_ in _BINDINGS)


class FileApprovalBindings:
    def __init__(self,release):
        need(type(release) is Release,'Exact selected Release required')
        self.release=release;self._active=False;self._used=False;self._installed=[]
        self._meta=release.metadata
        need(self._meta.get('kind')=='san14.b-portable-assets.v1' and
             self._meta.get('producer_provenance_only') is True and
             self._meta.get('recipient_native_execution_verified') is False,
             'Explicit producer-only B release metadata required')
        self._assets={row['path']:row for row in release.manifest['files']}
        pins=self._meta.get('source_pins')
        need(type(pins) is dict and pins,'Full portable source closure required')
        self._pins={};self._python_names={}
        for name,digest in pins.items():
            need(type(name) is str and name.startswith(('repo/work/mod_research/','repo/outputs/san14-link/'))
                 and hex_digest(digest),'Canonical reviewed source path required')
            path=self._asset(name,digest,'source');self._pins[str(path)]=digest
            if path.suffix=='.py':
                key=path.name.casefold()
                need(key not in self._python_names or self._python_names[key]==path,
                     'Ambiguous portable Python source filename: '+path.name)
                self._python_names[key]=path
        components=self._meta.get('components')
        need(type(components) is dict and set(components)=={'pair','helper','reward','input','rules'},
             'Exact B native component set required')
        self._components={}
        for name,family in FAMILIES.items():
            row=components[name]
            need(type(row) is dict and row.get('family')==family and
                 row.get('producer_approval_verified') is True and row.get('recipient_native_execution_verified') is False,
                 'Producer component approval missing: '+name)
            record=self._asset(row['producer_provenance'],row['producer_result_sha256'],'provenance')
            dll=self._asset(row['production_dll'],row['production_sha256'],'native')
            need(record.name=='result.json' and dll.name==NAMES[name] and dll.parent==record.parent,
                 'Component record and runtime DLL must occupy their own native directory')
            from portable_release import strict_json
            original=strict_json(record.read_bytes())
            need(type(original) is dict and original.get('result')=='PASS','Original producer receipt is not successful')
            subset=row.get('source_pins')
            need(type(subset) is dict and subset,'Component-specific source membership required: '+name)
            local={}
            for source,digest in subset.items():
                need(pins.get(source)==digest,'Component source differs from selected closure')
                local[str(self._asset(source,digest,'source'))]=digest
            dependencies=[]
            declared=row.get('dependencies',[])
            need(type(declared) is list,'Explicit component dependencies required')
            for dep in declared:
                need(type(dep) is dict and set(dep)=={'path','sha256'},'Exact native dependency record required')
                p=self._asset(dep['path'],dep['sha256'],'native')
                need(p.parent==dll.parent and p!=dll,'Native dependency must belong to its component')
                dependencies.append((p,dep['sha256']))
            need([p.name for p,_ in dependencies]==(['checkpoint_planning_hold.dll'] if name=='reward' else []),
                 'Unexpected runtime dependency set')
            if name in ('pair','helper'):
                need(original.get('family')==family and original.get('inputs_unchanged') is True,
                     'Producer component family or stability differs')
            else:need(original.get('game_access') is False,'Recipient must not mistake producer tests for live evidence')
            if name=='pair':need(original.get('refresh_factory_pair_passed') is True,'Actual producer pair proof absent')
            self._components[name]=dict(metadata=deepcopy(row),record=record,dll=dll,sources=local,
                                        original=original,dependencies=dependencies)
        # This comparison retains actual per-component membership, rather than
        # replacing both maps with the whole bundle (which would be vacuous).
        pair,helper=self._components['pair'],self._components['helper']
        for name,digest in helper['sources'].items():
            if Path(name).suffix in ('.h','.cpp'):
                need(pair['sources'].get(name)==digest,'Pair and helper do not share the approved native handover source')

    def _asset(self,name,digest,role):
        need(hex_digest(digest) and name in self._assets,'Missing selected asset')
        row=self._assets[name]
        need(row['role']==role and row['sha256']==digest,'Asset role or digest differs')
        return self.release.resolve(name)

    @property
    def source_pins(self):return deepcopy(self._pins)

    def _loaded(self):
        # Require the code actually executing, not a copied pin sheet, to come
        # from this release. External Python packages remain separately declared.
        local_root=self.release.root/'repo'
        for module in (sys.modules[__name__],*(m for m,_,_ in _BINDINGS)):
            path=Path(module.__file__).resolve(strict=True)
            need(path.is_relative_to(local_root) and self._pins.get(str(path))==sha(path.read_bytes()),
                 'Approval target is not the selected release code: '+module.__name__)
        for module in list(sys.modules.values()):
            value=getattr(module,'__file__',None)
            if not value:continue
            path=Path(value).resolve()
            expected=self._python_names.get(path.name.casefold())
            if expected is not None:
                # A genuine stdlib package submodule may share a leaf filename.
                # Its canonical stdlib name AND interpreter library location
                # must both agree; a foreign flat project import is not exempt.
                top=getattr(module,'__name__','').split('.')[0]
                stdlib=(top in sys.stdlib_module_names and
                        path.is_relative_to(Path(sys.base_prefix).resolve()/'Lib') and
                        'site-packages' not in path.parts)
                if not stdlib:
                    need(path==expected and self._pins.get(str(path))==sha(path.read_bytes()),
                         'Foreign imported project source: '+str(path))
            if path.is_relative_to(local_root) and path.suffix=='.py':
                need(self._pins.get(str(path))==sha(path.read_bytes()),'Unpinned imported release module: '+str(path))

    def __enter__(self):
        need(not self._used,'Approval binding lifetime cannot be replayed')
        need(_EXCLUSIVE.acquire(blocking=False),'Another portable approval lifetime is active')
        try:
            self.release.verify_all();self._loaded()
            for module,name,original in _ORIGINALS:
                need(getattr(module,name) is original,'Unexpected prior approval binding: '+module.__name__+'.'+name)
            methods={'sources':self.verify_sources,'component':self.approved_component,
                     'reward':self.approved_reward,'input':self.approved_input}
            for module,name,kind in _BINDINGS:
                replacement=methods[kind];original=getattr(module,name)
                setattr(module,name,replacement);self._installed.append((module,name,original,replacement))
            self._used=True;self._active=True
            return self
        except BaseException:
            for module,name,original,_ in reversed(self._installed):setattr(module,name,original)
            self._installed=[];_EXCLUSIVE.release();raise

    def __exit__(self,kind,value,tb):
        changed=[]
        try:
            for module,name,original,replacement in reversed(self._installed):
                if getattr(module,name) is not replacement:changed.append(module.__name__+'.'+name)
                setattr(module,name,original)
        finally:
            self._installed=[];self._active=False;_EXCLUSIVE.release()
        if changed:
            if value is not None:value.portable_binding_changed=changed
            else:raise ValueError('Approval binding was modified during use: '+', '.join(changed))
        return False

    def _check(self):
        need(self._active,'File approval is available only within its explicit binding lifetime')
        for module,name,_,replacement in self._installed:
            need(getattr(module,name) is replacement,'Portable approval binding changed')
        self.release.verify_all();self._loaded()

    def verify_sources(self,pins):
        self._check()
        need(type(pins) is dict and pins==self._pins,'Current source manifest differs from the complete selected release')
        for name in session.REQUIRED_SOURCES:
            need(str(Path(session.__file__).resolve().parent/name) in pins,'Required session source absent: '+name)

    def _component(self,path,digest,name):
        self._check();component=self._components[name];row=component['metadata']
        need(type(digest) is str and digest==row['producer_result_sha256'] and
             Path(path).resolve(strict=True)==component['record'],
             'Component does not belong to this selected release: '+name)
        return component

    def approved_component(self,path,digest,family):
        need(family in (FAMILIES['pair'],FAMILIES['helper']),'Only retained B pair/helper component approvals are bound')
        name=next(k for k in ('pair','helper') if FAMILIES[k]==family)
        c=self._component(path,digest,name);m=c['metadata']
        result=dict(family=family,result='PASS',inputs_unchanged=True,
            sources=deepcopy(c['sources']),binaries={str(c['dll']):m['production_sha256']},
            production_dll=dict(path=str(c['dll']),sha256=m['production_sha256']),
            approval_kind='producer_verified_release',producer_result_sha256=digest,
            producer_provenance=str(c['record']),recipient_native_execution_verified=False,
            private_archive_revalidated=False,install_permission=False)
        if name=='pair':result['refresh_factory_pair_passed']=True
        return result

    def approved_reward(self,build):
        need(type(build) is reward.NativeBuild,'Exact retained B NativeBuild required')
        c=self._component(Path(build.run)/'result.json',build.result_sha256,'reward');m=c['metadata']
        return dict(dll=c['dll'],sha256=m['production_sha256'],dependencies=[p for p,_ in c['dependencies']],
            record_sha256=build.result_sha256,approval_kind='producer_verified_release',
            recipient_native_execution_verified=False,private_archive_revalidated=False,install_permission=False)

    def approved_input(self,build):
        need(type(build) is inputs.Build,'Exact retained input bootstrap Build required')
        c=self._component(Path(build.run)/'result.json',build.sha256,'input')
        # Frozen call signature is a pair. The enclosing context's status carries
        # its producer-only meaning; no native completion/permission is returned.
        return c['dll'],c['metadata']['production_sha256']

    def status(self):
        return dict(active=self._active,approval_kind='producer_verified_release',
            manifest_sha256=self.release.manifest_sha256,
            bindings=[module.__name__+'.'+name for module,name,_ in _BINDINGS],
            recipient_native_execution_verified=False,private_archive_revalidated=False,
            process_checks_replaced=False,claims_replaced=False,install_permission=False)

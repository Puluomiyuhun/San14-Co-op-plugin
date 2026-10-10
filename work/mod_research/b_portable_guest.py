"""Relocatable B pilot launcher. Default/help is inert; --verify is files only.

Run with Python 3.11+ on 64-bit Windows, using -B. Pass the release SHA-256
received from the producer separately from the archive. Local configuration
contains this computer's current process/window/save identities and invitation;
it never inherits the producer's process, claims, keys or native completion.
"""
import sys
sys.dont_write_bytecode = True
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import secrets
from portable_release import Release, need

LOCAL_SCHEMA = 'san14.b-portable-local.v1'
GENERATED = {'pair_build', 'helper_build', 'rules_build', 'source_manifest', 'records'}


def activate_paths(release):
    """Only import the selected release, never an already imported other copy."""
    need(type(release) is Release and release.metadata.get('kind') == 'san14.b-portable-assets.v1', 'Approved B release required')
    here = Path(__file__).resolve()
    need(release.resolve('repo/work/mod_research/b_portable_guest.py') == here,
         'Run the launcher from the selected release, not another checkout')
    repo = release.root/'repo'
    for module in list(sys.modules.values()):
        path = getattr(module, '__file__', None)
        if path and Path(path).name in ('b_simple_remote_guest.py', 'b_remote_session.py', 'b_warm_start.py'):
            need(Path(path).resolve().is_relative_to(repo), 'Another runtime copy is already imported')
    sys.path[:0] = [str(repo/'work/mod_research'), str(repo/'outputs/san14-link'), str(release.root/'deps')]


def local_state_root():
    value = os.environ.get('LOCALAPPDATA')
    need(value and Path(value).is_absolute(), 'Windows LOCALAPPDATA required for persistent process claims')
    return (Path(value)/'San14Coop'/'state').resolve()


@contextmanager
def state_binding():
    import b_warm_start
    before = b_warm_start.PRIVATE
    root = local_state_root()
    b_warm_start.PRIVATE = root
    try:
        yield root
    finally:
        b_warm_start.PRIVATE = before


def verify(release):
    release.verify_all()
    activate_paths(release)
    from b_portable_approval import FileApprovalBindings
    from b_reward_native_port import NativeBuild
    from player_input_lease_bootstrap_port import Build
    from b_warm_rules_factory import RulesBuild
    # Resolve aliases *inside* the explicit approval binding, just as dynamic
    # Session/Runner checks will do during the eventual live operation.
    with FileApprovalBindings(release) as binding:
        import b_remote_session, b_reward_native_port, player_input_lease_bootstrap_port
        c = release.metadata['components']
        b_remote_session.verify_sources(binding.source_pins)
        b_remote_session.approved_builds(release.resolve(c['pair']['producer_provenance']),c['pair']['producer_result_sha256'],
                                        release.resolve(c['helper']['producer_provenance']),c['helper']['producer_result_sha256'])
        b_reward_native_port.approved_build(NativeBuild(release.resolve(c['reward']['producer_provenance']).parent,c['reward']['producer_result_sha256']))
        player_input_lease_bootstrap_port.approved(Build(release.resolve(c['input']['producer_provenance']).parent,c['input']['producer_result_sha256']))
        RulesBuild(release.resolve(c['rules']['stage']),release.resolve(c['rules']['publisher'])).check()
    return dict(result='PASS_PORTABLE_FILES',approval_kind='producer_verified_release',manifest_sha256=release.manifest_sha256,
                game_access=False,network_opened=False,recipient_native_execution_verified=False,
                live_configuration_still_required=True,persistent_claims_root=str(local_state_root()))


def materialize(release, local, binding):
    """Replace only distribution fields; all machine identities are local input."""
    import b_observed_start
    need(type(local) is dict and set(local) == {'schema','network','local','window','report_key_path','cut_key_path'} and
         local['schema'] == LOCAL_SCHEMA, 'Exact local portable configuration required')
    machine = local['local']
    need(type(machine) is dict and set(machine) == b_observed_start.LOCAL_KEYS - GENERATED,
         'Local configuration must supply all current machine fields and no producer build paths')
    # Preserve old no-replay checks in a stable machine directory independent
    # of archive location. No claim is created or erased while checking files.
    state = local_state_root()
    folder = state/'source-manifests';folder.mkdir(parents=True,exist_ok=True)
    relocation = hashlib.sha256(str(release.root).encode('utf-8')).hexdigest()[:16]
    path = folder/(release.manifest_sha256+'-'+relocation+'.json')
    manifest = dict(result='PASS',inputs_unchanged=True,sources=binding.source_pins,
                    approval_kind='producer_verified_release',release_sha256=release.manifest_sha256,
                    recipient_native_execution_verified=False)
    raw = (json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode()
    if path.exists():
        need(path.read_bytes() == raw, 'Existing local source manifest changed')
    else:
        with path.open('xb') as stream:stream.write(raw)
    c = release.metadata['components']
    v = dict(machine)
    v.update(records=str(state/'runs'/secrets.token_hex(16)),source_manifest=dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest()),
             rules_build=dict(stage=str(release.resolve(c['rules']['stage'])),publisher=str(release.resolve(c['rules']['publisher']))))
    for name in ('pair','helper'):
        v[name+'_build'] = dict(path=str(release.resolve(c[name]['producer_provenance'])),sha256=c[name]['producer_result_sha256'])
    config = dict(schema='san14.b-simple-remote-guest.v1',startup=dict(schema='san14.b-observed-start.v1',network=local['network'],local=v),
                  window=local['window'],report_key_path=local['report_key_path'],cut_key_path=local['cut_key_path'])
    for name in ('reward','input'):
        config[name+'_build'] = dict(run=str(release.resolve(c[name]['producer_provenance']).parent),sha256=c[name]['producer_result_sha256'])
    return config


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--verify',action='store_true');modes.add_argument('--check',action='store_true');modes.add_argument('--execute',action='store_true')
    parser.add_argument('--release-root',type=Path);parser.add_argument('--release-sha256');parser.add_argument('--local-config',type=Path)
    parser.add_argument('--no-game-input',action='store_true')
    args = parser.parse_args(argv)
    if not(args.verify or args.check or args.execute):parser.print_help();return 0
    if not args.release_root or not args.release_sha256:parser.error('Explicit release root and trusted digest required')
    if (args.check or args.execute) and args.local_config is None:parser.error('--local-config required')
    if args.execute and not args.no_game_input:parser.error('--execute requires --no-game-input')
    try:
        release = Release(args.release_root,args.release_sha256)
        report = verify(release)
        if args.verify:
            print(json.dumps(report,ensure_ascii=False));return 0
        from b_portable_approval import FileApprovalBindings
        import b_simple_remote_guest
        local = json.loads(args.local_config.read_text(encoding='utf-8-sig'))
        with state_binding(), FileApprovalBindings(release) as binding:
            config = materialize(release,local,binding)
            if args.check:print(json.dumps(b_simple_remote_guest.check(config),ensure_ascii=False));return 0
            b_simple_remote_guest.run(config,no_game_input=True)
        return 0
    except Exception as exc:
        print(json.dumps(dict(result='PORTABLE_CHECK_OR_RUN_FAILED',error_type=type(exc).__name__,
                              automatic_retry=False,game_cleanup_claimed=False)))
        return 1


if __name__ == '__main__':raise SystemExit(main())

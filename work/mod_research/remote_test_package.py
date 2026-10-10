"""Successor bundle: retained B runtime plus separately invoked preparation tools.

No game, keys, saves, claims or interpreter are exported. The network probe
client is stdlib-only; its server runs on A where cryptography is available.
Default help is inert, output directory and archive must be fresh.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path

import b_portable_release_export as collector
from b_portable_package import collect_dependencies, DEFAULT_DEPS
from portable_release import Release, write_bundle, archive, need

HERE = Path(__file__).resolve().parent


def assemble(spec, *, destination, zip_path, python_deps=DEFAULT_DEPS):
    destination, zip_path = Path(destination), Path(zip_path)
    need(not destination.exists() and not zip_path.exists(), 'Fresh package and archive required')
    need(not zip_path.resolve().is_relative_to(destination.resolve()), 'Archive must be outside package directory')
    selected = collector.collect(spec, extra_sources=[HERE/'remote_test_tools.py', HERE/'b_portable_approval.py'])
    dependencies = collect_dependencies(python_deps)
    metadata = deepcopy(selected['metadata'])
    metadata['bundled_dependencies'] = [dependencies['metadata']]
    metadata['recipient_runtime'] = dict(entry='repo/work/mod_research/b_portable_guest.py',
        python='CPython 3.11+ Windows x64, supplied by recipient', interpreter_bundled=False,
        requires_fresh_local_configuration=True, recipient_native_execution_verified=False)
    metadata['preparation_tools'] = dict(entry='repo/work/mod_research/remote_test_tools.py',
        keys='remote_test_keys.py', network='remote_link_probe.py', local_config='b_guest_local_setup.py',
        environment='remote_test_environment.py',
        default_help_inert=True, network_server_requires_unbundled_cryptography=True,
        network_probe_does_not_join_game_room=True, capture_requires_explicit_flag=True,
        no_automatic_game_launch=True, no_automatic_native_install=True)
    made = write_bundle(destination, [*selected['assets'], *dependencies['assets']], metadata)
    release = Release(made['root'], made['manifest_sha256'])
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    return dict(result='REMOTE_TEST_TOOLS_PACKAGE_CREATED', **made, archive=archive(release, zip_path),
                game_access=False, native_installed=False, recipient_native_execution_verified=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', type=Path); parser.add_argument('--output', type=Path)
    parser.add_argument('--zip', type=Path)
    args = parser.parse_args(argv)
    if args.spec is args.output is args.zip is None:
        parser.print_help(); return 0
    if None in (args.spec, args.output, args.zip): parser.error('--spec, --output and --zip required together')
    result = assemble(json.loads(args.spec.read_text(encoding='utf-8-sig')), destination=args.output, zip_path=args.zip)
    print(json.dumps(result, ensure_ascii=False)); return 0


if __name__ == '__main__':
    raise SystemExit(main())

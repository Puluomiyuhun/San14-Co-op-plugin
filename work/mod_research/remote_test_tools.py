"""Verified portable preparation tools; this entry never starts the co-op runner.

Select a release and its separately received SHA256, then --tool keys, network,
environment, or prepare-b. Put tool-specific arguments after --. Default help is inert.
prepare-b only accesses a game when explicitly given --capture by the user.
"""
import sys
sys.dont_write_bytecode = True
import argparse
from pathlib import Path

from portable_release import Release, need
from b_portable_guest import verify

ENTRIES = {'keys': 'remote_test_keys.py', 'network': 'remote_link_probe.py',
           'environment': 'remote_test_environment.py', 'prepare-b': 'b_guest_local_setup.py'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-root', type=Path)
    parser.add_argument('--release-sha256')
    parser.add_argument('--tool', choices=sorted(ENTRIES))
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.tool is None:
        parser.print_help(); return 0
    if not args.release_root or not args.release_sha256:
        parser.error('Selected release and separately received SHA256 required')
    release = Release(args.release_root, args.release_sha256)
    need(release.resolve('repo/work/mod_research/remote_test_tools.py') == Path(__file__).resolve(),
         'Run the tools entry from the selected release')
    verify(release)
    if args.tool == 'keys':
        import remote_test_keys as selected
    elif args.tool == 'network':
        import remote_link_probe as selected
    elif args.tool == 'environment':
        import remote_test_environment as selected
    else:
        import b_guest_local_setup as selected
    need(Path(selected.__file__).resolve() == release.resolve('repo/work/mod_research/'+ENTRIES[args.tool]),
         'Preparation tool comes from another installation')
    forwarded = args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments
    return selected.main(forwarded)


if __name__ == '__main__':
    raise SystemExit(main())

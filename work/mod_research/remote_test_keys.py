"""Prepare the three separate shared keys for the external-console pilot.

Default help is inert. create/export/import operate only on explicitly supplied
fresh local directories outside Git. Transfer directories contain secrets and
must be sent privately; this tool never uploads them. Output contains public
fingerprints and configuration paths only. No game or network access.
"""
import argparse
import json
from pathlib import Path
import secrets

import b_warm_adapter_key as keys

SCHEMA = 'san14.remote-test-key-set.v1'
NAMES = ('adapter', 'report', 'cut')


def need(ok, message):
    if not ok:
        raise ValueError(message)


def _new_folder(value):
    path = Path(value)
    need(path.is_absolute(), 'Absolute local output directory required')
    keys.Native().path(path/'adapter.key')
    need(not path.exists() and not path.is_symlink(), 'New output directory required')
    parent = path.parent.resolve(strict=True)
    need(not any((p/'.git').exists() for p in (parent, *parent.parents)), 'Key folders must be outside Git')
    destination = parent/path.name
    destination.mkdir(exist_ok=False)
    return destination


def _load(folder, *, transferred=False):
    folder = Path(folder).resolve(strict=True)
    doc = json.loads((folder/'key-set.json').read_text(encoding='utf-8'))
    need(type(doc) is dict and set(doc) == {'schema', 'set_id', 'fingerprints'} and doc['schema'] == SCHEMA,
         'Exact key-set manifest required')
    need(type(doc['set_id']) is str and len(doc['set_id']) == 32 and
         all(c in '0123456789abcdef' for c in doc['set_id']), 'Key-set identity required')
    need(type(doc['fingerprints']) is dict and set(doc['fingerprints']) == set(NAMES), 'Three distinct key roles required')
    native = keys.Native()
    values = {name: native.read(folder/(name+'.key'), private=not transferred) for name in NAMES}
    actual = {name: keys.public(value)['fingerprint'] for name, value in values.items()}
    need(actual == doc['fingerprints'] and len(set(actual.values())) == 3, 'Shared key roles or fingerprints differ')
    return doc, values


def _write(destination, doc, values):
    folder = _new_folder(destination)
    native = keys.Native()
    for name in NAMES:
        native.write_new(folder/(name+'.key'), values[name])
    # The manifest is public: no key bytes, file hashes, invitation or credentials.
    with (folder/'key-set.json').open('x', encoding='utf-8') as stream:
        json.dump(doc, stream, indent=2); stream.write('\n')
    return inspect(folder)


def create(destination):
    values = {name: secrets.token_bytes(32) for name in NAMES}
    fingerprints = {name: keys.public(value)['fingerprint'] for name, value in values.items()}
    need(len(set(fingerprints.values())) == 3, 'Independent random keys required')
    return _write(destination, dict(schema=SCHEMA, set_id=secrets.token_hex(16), fingerprints=fingerprints), values)


def export_set(source, destination):
    doc, values = _load(source)
    result = _write(destination, doc, values)
    result['contains_shared_secrets'] = True
    result['private_transfer_required'] = True
    return result


def import_set(source, destination):
    # A copied file may have the sender's ACL. Validate the entire set before
    # creating new files protected for this recipient. Never rewrite the source.
    doc, values = _load(source, transferred=True)
    return _write(destination, doc, values)


def inspect(folder):
    folder = Path(folder).resolve(strict=True)
    doc, _ = _load(folder)
    paths = {name: str(folder/(name+'.key')) for name in NAMES}
    return dict(result='PASS_LOCAL_KEY_SET', **doc,
                a_config_fields=dict(adapter_key_path=paths['adapter'], reward_report_key_path=paths['report'],
                                     guest_cut_key_path=paths['cut']),
                b_config_fields=dict(adapter_key_path=paths['adapter'], report_key_path=paths['report'], cut_key_path=paths['cut']),
                network_opened=False, game_access=False, secret_disclosed=False,
                remote_key_pairing_verified=False)


def compare_peer(folder, peer_manifest):
    local, _ = _load(folder)
    peer = json.loads(Path(peer_manifest).read_text(encoding='utf-8'))
    need(type(peer) is dict and set(peer) == set(local) and peer['schema'] == SCHEMA,
         'Exact peer public key-set manifest required')
    need(peer == local, 'Peer key set or role fingerprints differ')
    return dict(result='PASS_KEY_SET_PAIRING', set_id=local['set_id'], fingerprints=local['fingerprints'],
                peer_manifest_matches=True, live_peer_checked=False, game_access=False, network_opened=False,
                secret_disclosed=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action')
    sub.add_parser('create').add_argument('--output', type=Path, required=True)
    sub.add_parser('check').add_argument('--folder', type=Path, required=True)
    compare = sub.add_parser('compare'); compare.add_argument('--folder', type=Path, required=True)
    compare.add_argument('--peer-manifest', type=Path, required=True)
    for name in ('export', 'import'):
        p = sub.add_parser(name); p.add_argument('--source', type=Path, required=True)
        p.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.action is None:
        parser.print_help(); return 0
    try:
        if args.action == 'create': result = create(args.output)
        elif args.action == 'check': result = inspect(args.folder)
        elif args.action == 'compare': result = compare_peer(args.folder, args.peer_manifest)
        elif args.action == 'export': result = export_set(args.source, args.output)
        else: result = import_set(args.source, args.output)
        print(json.dumps(result, ensure_ascii=False)); return 0
    except Exception as exc:
        print(json.dumps(dict(result='KEY_SET_REFUSED', error_type=type(exc).__name__, secret_disclosed=False)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

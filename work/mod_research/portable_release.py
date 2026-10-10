"""Content-pinned portable files, not a live-game permit or build revalidation.

The producer approves native builds before packaging. A recipient explicitly
selects the manifest digest over a trusted channel; a hash stored beside a
download is not independent authentication. Runtime identities remain local.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

SCHEMA = 'san14.portable-release.v1'
MANIFEST = 'release.json'
ROLES = {'source', 'native', 'provenance', 'dependency'}
RESERVED = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(10)), *(f'LPT{i}' for i in range(10))}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def hex_digest(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def relative(value):
    need(type(value) is str and value and len(value) <= 230 and '\\' not in value, 'Canonical relative POSIX path required')
    p = PurePosixPath(value)
    need(not p.is_absolute() and str(p) == value and all(x not in ('.', '..', '') for x in p.parts), 'Path escapes release')
    for part in p.parts:
        need(not any(ord(c) < 32 or c in '<>:"|?*' for c in part) and not part.endswith((' ', '.')) and
             part.split('.')[0].upper() not in RESERVED, 'Unsupported Windows path')
    need(len(p.parts) >= 2 and p.parts[0] != MANIFEST, 'Assets require a managed top-level directory')
    return p


def regular(path):
    info = path.lstat()
    need(stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode) and
         not getattr(info, 'st_file_attributes', 0) & 0x400, 'Regular non-reparse file required: '+str(path))


def inside(root, name):
    p = relative(name)
    target = root.joinpath(*p.parts)
    # Refuse directory junctions and symlinks, even when they lead back inside.
    for current in (target, *list(target.parents)[:len(p.parts)-1]):
        info = current.lstat()
        need(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400, 'Reparse path in release')
    need(target.resolve(strict=True).is_relative_to(root), 'Resolved path escapes release')
    regular(target)
    return target


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'Duplicate manifest key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs)


class Release:
    def __init__(self, root, expected_sha256):
        need(hex_digest(expected_sha256), 'Explicit expected release SHA-256 required')
        self.root = Path(root).resolve(strict=True)
        manifest = self.root / MANIFEST
        regular(manifest)
        raw = manifest.read_bytes()
        need(sha(raw) == expected_sha256, 'Release manifest identity changed')
        value = strict_json(raw)
        need(type(value) is dict and set(value) == {'schema', 'files', 'metadata'} and value['schema'] == SCHEMA and
             type(value['metadata']) is dict and type(value['files']) is list and 1 <= len(value['files']) <= 20000, 'Malformed release manifest')
        self._manifest = value
        self.manifest_sha256 = expected_sha256
        self._rows = {}
        folded = set()
        for row in value['files']:
            need(type(row) is dict and set(row) == {'path', 'sha256', 'size', 'role'}, 'Malformed asset row')
            relative(row['path'])
            need(hex_digest(row['sha256']) and type(row['size']) is int and 0 <= row['size'] <= 256*1024*1024 and
                 row['role'] in ROLES and row['path'].casefold() not in folded, 'Invalid or colliding asset')
            folded.add(row['path'].casefold())
            self._rows[row['path']] = row
        self.verify_all()

    @property
    def metadata(self):
        return deepcopy(self._manifest['metadata'])

    @property
    def manifest(self):
        return deepcopy(self._manifest)

    def resolve(self, name):
        need(name in self._rows, 'File is not in the selected release')
        path = inside(self.root, name)
        row = self._rows[name]
        raw = path.read_bytes()
        need(len(raw) == row['size'] and sha(raw) == row['sha256'], 'Release asset changed: '+name)
        return path

    def verify_all(self):
        need(sha((self.root/MANIFEST).read_bytes()) == self.manifest_sha256, 'Release manifest changed after selection')
        for name in self._rows:
            self.resolve(name)
        # Runtime records must live outside managed asset directories. Launch
        # with -B to keep Python bytecode caches outside the immutable release.
        expected = set(self._rows)
        for top in {PurePosixPath(n).parts[0] for n in expected}:
            for current, directories, filenames in os.walk(self.root/top, followlinks=False):
                for name in directories:
                    p = Path(current)/name
                    info = p.lstat()
                    need(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400, 'Reparse directory in release')
                for name in filenames:
                    p = Path(current)/name
                    need(p.relative_to(self.root).as_posix() in expected, 'Unlisted file in managed release directory')
        return dict(result='PASS_RELEASE_FILES',file_count=len(self._rows),manifest_sha256=self.manifest_sha256,
                    approval_kind='producer_verified_release',local_game_verified=False,native_permission=False)


def write_bundle(destination, assets, metadata):
    destination = Path(destination)
    need(not destination.exists() and type(metadata) is dict, 'Fresh destination and explicit release metadata required')
    rows, seen = [], set()
    copied = list(assets)
    need(1 <= len(copied) <= 20000, 'Bounded nonempty asset list required')
    for asset in copied:
        need(type(asset) is dict and set(asset) == {'source', 'path', 'sha256', 'role'}, 'Exact export asset fields required')
        relative(asset['path'])
        need(hex_digest(asset['sha256']) and asset['role'] in ROLES and asset['path'].casefold() not in seen, 'Asset collision or invalid digest')
        seen.add(asset['path'].casefold())
    destination.mkdir(parents=True, exist_ok=False)
    for asset in copied:
        source = Path(asset['source']); regular(source)
        raw = source.read_bytes()
        need(len(raw) <= 256*1024*1024 and sha(raw) == asset['sha256'], 'Producer asset drift: '+str(source))
        target = destination.joinpath(*relative(asset['path']).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as out:
            out.write(raw)
        rows.append(dict(path=asset['path'],sha256=asset['sha256'],size=len(raw),role=asset['role']))
    value = dict(schema=SCHEMA, files=sorted(rows,key=lambda r:r['path']), metadata=deepcopy(metadata))
    raw = (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')
    with (destination/MANIFEST).open('xb') as out:
        out.write(raw)
    digest = sha(raw)
    Release(destination,digest)
    return dict(root=str(destination.resolve()),manifest_sha256=digest,file_count=len(rows))


def archive(release, output):
    need(type(release) is Release, 'Verified release required')
    release.verify_all()
    output = Path(output)
    need(not output.exists() and not output.resolve().is_relative_to(release.root), 'Fresh archive outside release required')
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as packed:
        for name in [MANIFEST,*sorted(release._rows)]:
            data = (release.root/name).read_bytes()
            packed.writestr(name,data)
    return dict(path=str(output.resolve()),sha256=sha(output.read_bytes()),manifest_sha256=release.manifest_sha256)

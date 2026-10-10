"""Local Python capability check; no game/process discovery, network or install.

Default help is inert. --role B checks the client environment; --role A also
generates, signs and verifies a certificate entirely in memory. Passing checks
does not authorize native installation or establish connectivity/game readiness.
"""
import argparse
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import struct
import sys
sys.dont_write_bytecode=True

SCHEMA='san14.remote-test-environment.v1'
REQUIREMENTS={'windows_python_x64':'CPython 3.11+ on 64-bit Windows',
    'stdlib_tls':'Working ssl TLS 1.2+ client context and memory BIO',
    'stdlib_sqlite':'Working sqlite3 in-memory transaction',
    'stdlib_ctypes':'Working ctypes local memory buffer operations',
    'pefile':'Importable pefile PE parser and its package dependencies',
    'certificate_signing':'Importable cryptography with RSA-2048 SHA-256 certificate signing and verification'}


def _module(name):
    # Explicit lazy imports retain the static portable-source closure. B never
    # enters the certificate branches; the test seam is not an import service.
    if name=='ssl':
        import ssl
        return ssl
    if name=='sqlite3':
        import sqlite3
        return sqlite3
    if name=='ctypes':
        import ctypes
        return ctypes
    if name=='pefile':
        import pefile
        return pefile
    if name=='cryptography':
        import cryptography
        return cryptography
    if name=='cryptography.x509':
        from cryptography import x509
        return x509
    if name=='cryptography.hazmat.primitives.hashes':
        from cryptography.hazmat.primitives import hashes
        return hashes
    if name=='cryptography.hazmat.primitives.asymmetric.rsa':
        from cryptography.hazmat.primitives.asymmetric import rsa
        return rsa
    if name=='cryptography.hazmat.primitives.asymmetric.padding':
        from cryptography.hazmat.primitives.asymmetric import padding
        return padding
    if name=='cryptography.x509.oid':
        from cryptography.x509 import oid
        return oid
    raise ValueError('Unsupported environment module')


def _facts():
    return dict(platform=sys.platform,python=list(sys.version_info[:3]),pointer_bits=struct.calcsize('P')*8,
                implementation=sys.implementation.name)


def _require(ok,message):
    if not ok:raise ValueError(message)


def _platform():
    facts=_facts()
    _require(facts['platform']=='win32' and facts['pointer_bits']==64 and
             tuple(facts['python'])>=(3,11,0) and facts['implementation']=='cpython',
             'CPython 3.11+ on 64-bit Windows required')
    return facts


def _tls():
    ssl=_module('ssl')
    _require(ssl.HAS_TLSv1_2,'TLS 1.2 support required')
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version=ssl.TLSVersion.TLSv1_2
    incoming,outgoing=ssl.MemoryBIO(),ssl.MemoryBIO()
    connection=context.wrap_bio(incoming,outgoing,server_hostname='environment.invalid')
    _require(connection.context is context and context.check_hostname and
             context.verify_mode==ssl.CERT_REQUIRED,'Verified TLS client context unavailable')
    return dict(provider=ssl.OPENSSL_VERSION,minimum_tls='1.2',memory_bio_created=True,
                certificate_store_loaded=False,handshake_executed=False)


def _sqlite():
    sqlite=_module('sqlite3')
    database=sqlite.connect(':memory:')
    try:
        database.execute('CREATE TABLE check_value (value INTEGER NOT NULL)')
        database.execute('INSERT INTO check_value VALUES (?)',(37,));database.commit()
        _require(database.execute('SELECT value FROM check_value').fetchall()==[(37,)],'Memory database mismatch')
    finally:database.close()
    return dict(version=sqlite.sqlite_version,in_memory_transaction=True)


def _ctypes():
    ctypes=_module('ctypes')
    raw=b'owned-environment-buffer';buffer=ctypes.create_string_buffer(len(raw))
    ctypes.memmove(buffer,raw,len(raw))
    _require(ctypes.string_at(buffer,len(raw))==raw,'Local ctypes memory operation failed')
    return dict(local_buffer_verified=True,foreign_process_opened=False)


def _pefile():
    pefile=_module('pefile')
    _require(callable(pefile.PE),'PE parser unavailable')
    return dict(version=str(getattr(pefile,'__version__','unknown')),import_available=True,
                file_parsed=False)


def _certificate():
    package=_module('cryptography');x509=_module('cryptography.x509')
    hashes=_module('cryptography.hazmat.primitives.hashes')
    rsa=_module('cryptography.hazmat.primitives.asymmetric.rsa')
    padding=_module('cryptography.hazmat.primitives.asymmetric.padding')
    oid=_module('cryptography.x509.oid')
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(oid.NameOID.COMMON_NAME,'SAN14 owned environment check')])
    now=datetime.now(timezone.utc)
    certificate=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1))
        .not_valid_after(now+timedelta(minutes=5)).sign(key,hashes.SHA256()))
    key.public_key().verify(certificate.signature,certificate.tbs_certificate_bytes,
                            padding.PKCS1v15(),certificate.signature_hash_algorithm)
    _require(len(certificate.fingerprint(hashes.SHA256()))==32,'Certificate digest unavailable')
    return dict(version=str(package.__version__),rsa_bits=2048,certificate_signed=True,
                signature_verified=True,key_exported=False,certificate_written=False)


def check(role):
    """Return independent local capability results; never open network/game files."""
    if role not in ('A','B'):raise ValueError('Role must be A or B')
    probes=[('windows_python_x64',_platform),('stdlib_tls',_tls),('stdlib_sqlite',_sqlite),
            ('stdlib_ctypes',_ctypes),('pefile',_pefile)]
    if role=='A':probes.append(('certificate_signing',_certificate))
    rows=[]
    for name,probe in probes:
        try:rows.append(dict(name=name,requirement=REQUIREMENTS[name],passed=True,detail=probe()))
        except Exception as exc:
            rows.append(dict(name=name,requirement=REQUIREMENTS[name],passed=False,error_type=type(exc).__name__,
                             missing_dependency=getattr(exc,'name',None) if isinstance(exc,ImportError) else None))
    return dict(schema=SCHEMA,role=role,result='PASS_ENVIRONMENT' if all(r['passed'] for r in rows) else 'ENVIRONMENT_NOT_READY',
        checks=rows,scope='Local interpreter/dependency capability only; not connectivity, native approval or game readiness',
        game_access=False,process_discovery=False,registry_scan=False,network_opened=False,
        application_files_written=False,dependencies_installed=False,native_install_permission=False,
        real_clients_verified=False)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--role',choices=('A','B'))
    args=parser.parse_args(argv)
    if args.role is None:parser.print_help();return 0
    # The portable tools entry sets its selected release paths. Standalone use
    # follows the established repository/private-dependency layout as well.
    here=Path(__file__).resolve().parent;root=here.parents[1]
    for path in (root.parent/'deps',root.parent/'mod_research/python_deps'):
        if path.is_dir():sys.path.append(str(path))
    result=check(args.role);print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['result']=='PASS_ENVIRONMENT' else 1


if __name__=='__main__':raise SystemExit(main())

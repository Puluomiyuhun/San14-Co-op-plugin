"""TLS transport for room selection only. Native game execution is unavailable."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import socket
import socketserver
import ssl
import threading
from room_session import Room, RoomError, canonical

MAX_PACKET = 65536


def read_packet(stream):
    data = stream.readline(MAX_PACKET + 1)
    if not data:
        raise EOFError()
    if len(data) > MAX_PACKET or not data.endswith(b'\n'):
        raise RoomError('Packet too large or incomplete')
    value = json.loads(data)
    if type(value) is not dict:
        raise RoomError('Expected object')
    return value


def write_packet(stream, value):
    data = canonical(value) + b'\n'
    if len(data) > MAX_PACKET:
        raise RoomError('Response too large')
    stream.write(data)
    stream.flush()


def make_certificate(folder):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'SAN14 research room')])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=5))
            .not_valid_after(now + timedelta(days=2)).sign(key, hashes.SHA256()))
    key_path, cert_path = folder / 'room-key.pem', folder / 'room-cert.pem'
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return cert_path, key_path, cert.fingerprint(hashes.SHA256()).hex()


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        connection = secrets.token_hex(16)
        player = None
        self.connection.settimeout(30)
        try:
            greeting = self.server.room.authenticate(read_packet(self.rfile), connection)
            player = greeting['player_id']
            write_packet(self.wfile, {'ok': True, **greeting})
            while True:
                request = read_packet(self.rfile)
                write_packet(self.wfile, self.server.room.handle(player, connection, request))
        except (RoomError, ValueError, TypeError) as e:
            try:
                write_packet(self.wfile, {'ok': False, 'error': str(e), 'applied_to_game': False})
            except OSError:
                pass
        except (EOFError, OSError):
            pass
        finally:
            if player is not None:
                self.server.room.disconnect(player, connection)


class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, address, room, cert_path, key_path):
        self.room = room
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.minimum_version = ssl.TLSVersion.TLSv1_2
        self.context.load_cert_chain(str(cert_path), str(key_path))
        super().__init__(address, Handler)

    def get_request(self):
        sock, address = super().get_request()
        sock.settimeout(3)
        try:
            return self.context.wrap_socket(sock, server_side=True), address
        except Exception:
            sock.close()
            raise


class Client:
    def __init__(self, host, port, fingerprint, greeting):
        self.socket = None
        self.stream = None
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        # Authenticate the exact pinned room certificate BEFORE sending secrets.
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        raw = socket.create_connection((host, port), timeout=5)
        try:
            self.socket = context.wrap_socket(raw, server_hostname=host)
            actual = hashlib.sha256(self.socket.getpeercert(binary_form=True)).hexdigest()
            if not hmac.compare_digest(actual, fingerprint):
                raise RoomError('Room certificate fingerprint mismatch')
            self.stream = self.socket.makefile('rwb')
            response = self.request(greeting)
            if not response.get('ok'):
                raise RoomError(response.get('error', 'Authentication failed'))
            self.player_id = response['player_id']
            self.resume_token = response['resume_token']
            self.state = response['state']
        except Exception:
            raw.close()
            self.close()
            raise

    def request(self, value):
        write_packet(self.stream, value)
        response = read_packet(self.stream)
        if 'state' in response:
            self.state = response['state']
        return response

    def close(self):
        if self.socket is not None:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        if self.stream is not None:
            self.stream.close()
            self.stream = None
        if self.socket is not None:
            self.socket.close()
            self.socket = None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--private-state', type=Path, required=True)
    parser.add_argument('--lifetime', type=int, default=120)
    args = parser.parse_args()
    if not 5 <= args.lifetime <= 600:
        parser.error('Research listener lifetime must be 5..600 seconds')
    room = Room(json.loads(args.manifest.read_text(encoding='utf-8')))
    cert, key, fingerprint = make_certificate(args.private_state)
    # Current runner deliberately stays local until the native adapter exists.
    with Server(('127.0.0.1', 0), room, cert, key) as server:
        config = {'host': '127.0.0.1', 'port': server.server_address[1], 'fingerprint': fingerprint,
                  'invite': room.invite, 'host_token': room.host_token, 'profile': room.manifest['profile']}
        target = args.private_state / 'connection.json'
        temporary = target.with_suffix('.tmp')
        temporary.write_text(json.dumps(config), encoding='utf-8')
        temporary.replace(target)
        timer = threading.Timer(args.lifetime, server.shutdown)
        timer.daemon = True
        timer.start()
        try:
            server.serve_forever(poll_interval=.1)
        finally:
            timer.cancel()


if __name__ == '__main__':
    main()

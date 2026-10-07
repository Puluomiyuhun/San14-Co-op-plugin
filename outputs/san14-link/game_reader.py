"""Version-locked, read-only live SAN14 snapshot; not a multiplayer game adapter."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import time
from readonly_probe import Memory, find_game_pid

SUPPORTED_SHA256 = "42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025"
DATA_POINTER_RVA = 0x1FCA1E0
STATE_MANAGER_RVA = 0x19E7310


class GameReader:
    def __init__(self, pid=None):
        self.pid = pid if pid is not None else find_game_pid()
        self.memory = Memory(self.pid)
        try:
            self.sha256 = hashlib.sha256(self.memory.path.read_bytes()).hexdigest()
            if self.sha256 != SUPPORTED_SHA256:
                raise RuntimeError("Unsupported game executable fingerprint; no field addresses used")
        except Exception:
            self.memory.close()
            raise

    def close(self):
        self.memory.close()

    def pointer(self, address):
        value = struct.unpack("<Q", self.memory.read(address, 8))[0]
        if not 0x10000 <= value < 0x7FFFFFFFFFFF or value % 8:
            raise RuntimeError("Invalid object pointer; game may be loading or closing")
        return value

    def require_type(self, address, name):
        m = self.memory
        vtable = self.pointer(address)
        if not m.base <= vtable < m.base + m.image_size:
            raise RuntimeError("Object vtable is outside the game module")
        locator = self.pointer(vtable - 8)
        if not m.base <= locator < m.base + m.image_size - 24:
            raise RuntimeError("Invalid RTTI locator")
        signature, _, _, descriptor, _, self_rva = struct.unpack("<6I", m.read(locator, 24))
        if signature != 1 or self_rva != locator - m.base or descriptor >= m.image_size - 160:
            raise RuntimeError("Unexpected RTTI metadata")
        actual = m.read(m.base + descriptor + 16, 128).split(b"\0")[0].decode("ascii")
        if actual != f".?AV{name}@@":
            raise RuntimeError(f"Expected {name}, got {actual}")

    def state_objects(self):
        """Return checked (name, address) pairs for local readers only."""
        m = self.memory
        manager = m.base + STATE_MANAGER_RVA
        count = struct.unpack("<Q", m.read(manager + 0x10, 8))[0]
        if not 1 <= count <= 64:
            raise RuntimeError("Game state stack is not ready")
        array = self.pointer(manager + 0x20)
        data = m.read(array, count * 8)
        objects = []
        for address in struct.unpack("<" + "Q" * count, data):
            if not 0x10000 <= address < 0x7FFFFFFFFFFF or address % 8:
                raise RuntimeError("Invalid state object pointer")
            name = m.read(address + 0x70, 96).split(b"\0")[0].decode("ascii")
            if not name.startswith("C") or not all(c.isalnum() or c in "_<>:, " for c in name):
                raise RuntimeError("Unexpected state name")
            objects.append((name, address))
        if (m.read(manager + 0x10, 8) != struct.pack("<Q", count)
                or self.pointer(manager + 0x20) != array
                or m.read(array, count * 8) != data):
            raise RuntimeError("Game state stack changed during sampling")
        return objects

    def states(self):
        return [name for name, _ in self.state_objects()]

    def snapshot(self):
        m = self.memory
        for _ in range(3):
            root = self.pointer(m.base + DATA_POINTER_RVA)
            self.require_type(root, "CSan14Data")
            world = self.pointer(root + 0x85130)
            self.require_type(world, "CWorldData")
            before = m.read(world + 0x34, 8)
            year, month, day = struct.unpack_from("<HBB", before)
            # Game accessor 0x2F21E0 reads a byte; +0x3B is a separate field.
            force_id = before[6]
            if not (1 <= year <= 9999 and 1 <= month <= 12 and 1 <= day <= 30 and force_id <= 51):
                raise RuntimeError("World not ready or fields out of supported range")
            phase_before = self.states()
            force = self.pointer(root + 0xDCA0 + force_id * 8)
            self.require_type(force, "CForceData")
            ruler_id = struct.unpack("<H", m.read(force + 0x10, 2))[0]
            if ruler_id >= 6000:
                raise RuntimeError("Ruler id out of supported range")
            person = self.pointer(root + 0x148 + ruler_id * 8)
            self.require_type(person, "CPersonData")
            record = m.read(person + 0x10, 0x30)
            if struct.unpack_from("<H", record)[0] != ruler_id:
                raise RuntimeError("Person id disagrees with table index")
            surname = record[2:20].decode("utf-16le").split("\0")[0]
            given = record[20:38].decode("utf-16le").split("\0")[0]
            if not surname and not given:
                raise RuntimeError("Empty ruler name")
            after = m.read(world + 0x34, 8)
            phase_after = self.states()
            if before != after or phase_before != phase_after or root != self.pointer(m.base + DATA_POINTER_RVA):
                continue
            # Sample consistency checks, not a full-game atomic snapshot.
            return {"mode": "read-only-live-game", "pid": self.pid,
                    "exe_sha256": self.sha256,
                    "date": {"year": year, "month": month, "day": day,
                             "period": "上旬" if day <= 10 else "中旬" if day <= 20 else "下旬"},
                    "player": {"force_id": force_id, "ruler_id": ruler_id, "ruler_name": surname + given},
                    "state_stack": phase_after,
                    "in_player_strategy": "CUserStrategyState" in phase_after,
                    "validation": "RTTI + bounds + repeated date/root/state reads",
                    "multiplayer_connected": False}
        raise RuntimeError("Game changed during sampling; retry at a stable map screen")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--samples", type=int, default=1)
    parser.add_argument("--interval", type=float, default=1)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 1 <= args.samples <= 3600 or not 0.1 <= args.interval <= 60:
        parser.error("samples: 1..3600; interval: 0.1..60 seconds")
    reader = GameReader(args.pid)
    try:
        snapshots = []
        for n in range(args.samples):
            snapshot = reader.snapshot()
            snapshots.append(snapshot)
            print(json.dumps(snapshot, ensure_ascii=False, indent=2), flush=True)
            if n + 1 < args.samples:
                time.sleep(args.interval)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(snapshots, ensure_ascii=False, indent=2), encoding="utf-8")
    finally:
        reader.close()


if __name__ == "__main__":
    main()

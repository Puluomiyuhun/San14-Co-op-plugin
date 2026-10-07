"""Read a partial, unsubmitted sortie draft. Never submits or writes game memory."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

from game_reader import GameReader, DATA_POINTER_RVA

MAKE_STATE = "CStrategyUnitMakeState"
TARGET_STATE = "CStrategyUnitTargetState"
CITY_TABLE = 0xDAA8
PERSON_TABLE = 0x148
FORMATION_TABLE = 0x76B58
TACTICS_TABLE = 0x76C00
DRAFT_SIZE = 0x94
COMMAND_SIZE = 0x68


def pointer_vector(memory, address, limit=64):
    header = memory.read(address, 24)
    start, end, capacity = struct.unpack("<QQQ", header)
    if start == end == capacity == 0:
        return header, b"", ()
    if not (0x10000 <= start <= end <= capacity < 0x7FFFFFFFFFFF
            and all(value % 8 == 0 for value in (start, end, capacity))
            and (capacity - start) // 8 <= limit):
        raise RuntimeError("Invalid draft vector; refusing to follow pointers")
    raw = memory.read(start, end - start) if end != start else b""
    pointers = struct.unpack("<" + "Q" * (len(raw) // 8), raw)
    if any(not 0x10000 <= p < 0x7FFFFFFFFFFF or p % 8 for p in pointers):
        raise RuntimeError("Invalid draft entry pointer")
    return header, raw, pointers


def decode_partial_unit(data):
    if len(data) not in (DRAFT_SIZE, COMMAND_SIZE):
        raise RuntimeError("Unexpected sortie draft size")
    officer_id, _, soldiers = struct.unpack_from("<III", data)
    if not 0 <= officer_id < 6000 or not 1 <= soldiers <= 65535:
        raise RuntimeError("Draft is incomplete or values are out of range")
    return {"officer_id": officer_id, "soldiers": soldiers}


def text_name(data):
    return data.decode("utf-16le").split("\0", 1)[0]


class SortieReader(GameReader):
    def city_record(self, root, city_id):
        if not 0 <= city_id <= 51:
            raise RuntimeError("City id out of supported range")
        address = self.pointer(root + CITY_TABLE + city_id * 8)
        self.require_type(address, "CCityData")
        record = self.memory.read(address + 0x10, 10)
        if struct.unpack_from("<H", record)[0] != city_id:
            raise RuntimeError("City id disagrees with table index")
        name = text_name(record[2:10])
        if not name:
            raise RuntimeError("City name is empty")
        return address, record, {"id": city_id, "name": name}

    def sortie_snapshot(self):
        m = self.memory
        before = self.snapshot()
        states = self.state_objects()
        result = {
            "schema": "san14.sortie-draft.v1",
            "mode": "read-only-live-game",
            "exe_sha256": self.sha256,
            "date": before["date"],
            "player": before["player"],
            "state_stack": [name for name, _ in states],
            "draft_available": False,
            "submitted": False,
            "replay_supported": False,
            "multiplayer_connected": False,
        }
        if not states or states[-1][0] not in (MAKE_STATE, TARGET_STATE):
            result["reason"] = "Open the unit composition or destination selection screen"
            return result
        if "CUserStrategyState" not in result["state_stack"]:
            raise RuntimeError("Not in the player's planning phase")
        targeting = states[-1][0] == TARGET_STATE
        make_index = -2 if targeting else -1
        if len(states) < 2 or states[make_index][0] != MAKE_STATE:
            raise RuntimeError("Unsupported sortie state layout")
        state = states[make_index][1]
        self.require_type(state, MAKE_STATE)
        root = self.pointer(m.base + DATA_POINTER_RVA)
        self.require_type(root, "CSan14Data")
        city = self.pointer(state + 0x4B8)
        self.require_type(city, "CCityData")
        city_id = struct.unpack("<H", m.read(city + 0x10, 2))[0]
        checked_city, city_record, source_city = self.city_record(root, city_id)
        if checked_city != city:
            raise RuntimeError("Source city does not match the city table")
        vector_address = state + 0x4C0
        header, vector, pointers = pointer_vector(m, vector_address)
        if not pointers:
            raise RuntimeError("Select an officer and troops before reading")
        raw_units = [m.read(p, DRAFT_SIZE) for p in pointers]
        command_units = [raw[:COMMAND_SIZE] for raw in raw_units]
        target_checks = []
        if targeting:
            target_state = states[-1][1]
            self.require_type(target_state, TARGET_STATE)
            target_mode = m.read(target_state + 0x538, 4)
            if struct.unpack("<I", target_mode)[0] != 0:
                raise RuntimeError("Only the observed new-sortie destination mode is supported")
            target_vector_address = target_state + 0x540
            target_header, target_vector, target_pointers = pointer_vector(m, target_vector_address)
            if len(target_pointers) != len(pointers):
                raise RuntimeError("Composition and destination draft counts disagree")
            target_raw = [m.read(p, COMMAND_SIZE + 4) for p in target_pointers]
            command_units = []
            for make_raw, raw in zip(raw_units, target_raw):
                if struct.unpack_from("<I", raw)[0] != 0 or raw[4:24] != make_raw[:20]:
                    raise RuntimeError("Destination draft does not match the original unit")
                command_units.append(raw[4:])
            target_checks.extend([(target_state + 0x538, target_mode),
                                  (target_vector_address, target_header)])
            if target_vector:
                target_checks.append((struct.unpack_from("<Q", target_header)[0], target_vector))
            target_checks.extend(zip(target_pointers, target_raw))
        units = []
        person_records = []
        data_checks = []
        for raw in command_units:
            unit = decode_partial_unit(raw)
            person = self.pointer(root + PERSON_TABLE + unit["officer_id"] * 8)
            self.require_type(person, "CPersonData")
            record = m.read(person + 0x10, 38)
            if struct.unpack_from("<H", record)[0] != unit["officer_id"]:
                raise RuntimeError("Officer id disagrees with the person table")
            unit["officer_name"] = text_name(record[2:20]) + text_name(record[20:38])
            if not unit["officer_name"]:
                raise RuntimeError("Officer name is empty")
            person_records.append((person, record))
            for label, offset in (("formation", 0xC), ("naval_formation", 0x10)):
                formation_id = struct.unpack_from("<I", raw, offset)[0]
                if not 1 <= formation_id <= 20:
                    raise RuntimeError("Formation id out of supported range")
                formation = self.pointer(root + FORMATION_TABLE + formation_id * 8)
                self.require_type(formation, "CFormationData")
                formation_name_raw = m.read(formation + 0x10, 6)
                formation_name = text_name(formation_name_raw)
                if not formation_name:
                    raise RuntimeError("Formation name is empty")
                unit[label] = {"id": formation_id, "name": formation_name}
                data_checks.append((formation + 0x10, formation_name_raw))
            unit["tactics"] = []
            # Three uint32 ids become three bytes at generated unit +0x1D.
            for slot, tactic_id in enumerate(struct.unpack_from("<3I", raw, 0x14), start=1):
                if not 0 <= tactic_id <= 200:
                    raise RuntimeError("Tactic id out of supported range")
                tactic = self.pointer(root + TACTICS_TABLE + tactic_id * 8)
                self.require_type(tactic, "CTacticsData")
                name_raw = m.read(tactic + 0x10, 10)
                name = text_name(name_raw)
                if not name:
                    raise RuntimeError("Tactic name is empty")
                unit["tactics"].append({"slot": slot, "id": tactic_id,
                                       "name": name, "selected": tactic_id != 0})
                data_checks.append((tactic + 0x10, name_raw))
            if targeting:
                target_type, target_id = struct.unpack_from("<II", raw, 0x38)
                if target_type == 255:
                    unit["destination"] = None
                elif target_type == 5:
                    destination, destination_raw, destination_name = self.city_record(root, target_id)
                    unit["destination"] = {"kind": "city", **destination_name}
                    data_checks.append((destination + 0x10, destination_raw))
                else:
                    raise RuntimeError(f"Destination type {target_type} is not yet supported")
            units.append(unit)
        after = self.snapshot()
        if (before != after or states != self.state_objects()
                or root != self.pointer(m.base + DATA_POINTER_RVA)
                or city != self.pointer(state + 0x4B8)
                or city_record != m.read(city + 0x10, 10)
                or pointer_vector(m, vector_address) != (header, vector, pointers)
                or raw_units != [m.read(p, DRAFT_SIZE) for p in pointers]
                or any(record != m.read(p + 0x10, 38) for p, record in person_records)
                or any(raw != m.read(p, len(raw)) for p, raw in target_checks + data_checks)):
            raise RuntimeError("Draft changed during sampling; stop editing and retry")
        partial = {"source_city": source_city, "units": units}
        canonical = json.dumps(partial, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        result.update({
            "draft_available": True,
            "draft_stage": "destination-selection" if targeting else "unit-composition",
            "partial_order": partial,
            "partial_order_sha256": hashlib.sha256(canonical).hexdigest(),
            "missing_fields": ([] if targeting and all(u.get("destination") for u in units)
                               else ["destination"]) + ["behavior_settings"],
            "validation": "exe fingerprint + RTTI + table identity + repeated state/vector/content reads",
        })
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    reader = None
    try:
        reader = SortieReader(args.pid)
        result = reader.sortie_snapshot()
        encoded = json.dumps(result, ensure_ascii=False, indent=2)
        print(encoded)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded + "\n", encoding="utf-8")
        return 0 if result["draft_available"] else 2
    except (RuntimeError, OSError, UnicodeError) as error:
        encoded = json.dumps({"error": str(error), "mode": "read-only-live-game",
                              "draft_available": False}, ensure_ascii=False, indent=2)
        print(encoded)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded + "\n", encoding="utf-8")
        return 1
    finally:
        if reader:
            reader.close()


if __name__ == "__main__":
    raise SystemExit(main())

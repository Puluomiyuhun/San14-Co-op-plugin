"""Archive the one passing push export and parse its header entirely offline.

No game process APIs, native calls, source-save writes or legacy report writes.
The copied parser executes in Unicorn with a byte-buffer stream primitive.
"""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import struct
import sys
import types

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "python_deps"), str(ROOT)]
RUN = ROOT / "checkpoint_push_runs/20261006-203111-687580"
SOURCE = Path(r"C:\Program Files (x86)\Steam\userdata\391007908\872410\remote\mppush01.s14")
EXPECTED = "88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def isolated_definitions(filename, module_name):
    # Both legacy scripts run fixtures/write reports after this exact delimiter.
    # Import only the reviewed definitions; never execute their fixture drivers.
    path = ROOT / filename
    source = path.read_text(encoding="utf8")
    assert source.count("\ncases=[]\n") == 1
    module = types.ModuleType(module_name)
    module.__file__ = str(path)
    exec(compile(source.split("\ncases=[]\n", 1)[0], str(path), "exec"), module.__dict__)
    return module


def main():
    result_bytes = (RUN / "result.json").read_bytes()
    result = json.loads(result_bytes)
    assert result["result"] == "PASS" and result["native_save_complete"] is True
    assert result["completion_evidence"]["complete"] is True
    assert result["file"]["sha256"] == EXPECTED
    a = SOURCE.stat()
    payload = SOURCE.read_bytes()
    b = SOURCE.stat()
    assert a.st_size == b.st_size == len(payload) == result["file"]["size"] == 274880
    assert a.st_mtime_ns == b.st_mtime_ns == result["file"]["mtime_ns"]
    assert sha(payload) == EXPECTED

    # Keep the failed-export header report and its fixture reports immutable.
    protected = [ROOT / name for name in (
        "private_checkpoint_metadata_shadow.json", "private_checkpoint_load_shadow.json",
        "private_checkpoint_metadata_new_file.json", "private_checkpoint_exported_forensics.s14",
        "checkpoint_push_once.intent")]
    original = {str(p): sha(p.read_bytes()) for p in protected}
    native = isolated_definitions("private_checkpoint_load_shadow.py", "private_checkpoint_load_shadow")
    assert "private_checkpoint_load_shadow" not in sys.modules
    sys.modules["private_checkpoint_load_shadow"] = native
    try:
        parser = isolated_definitions("private_checkpoint_metadata_shadow.py", "push_header_parser")
        parsed = parser.parser(payload, True)
    finally:
        del sys.modules["private_checkpoint_load_shadow"]
    header = bytes.fromhex(parsed["header_hex"])
    date = {"year": struct.unpack_from("<H", header, 0xE2)[0], "month": header[0xE4], "day": header[0xE5]}
    assert date == {"year": 203, "month": 8, "day": 11}
    assert parsed["bytes_consumed"] == 294 and not parsed["global_writes"]
    ruler_marker = "张鲁".encode("utf-16-le")
    ruler_offsets = [i for i in range(len(header)) if header.startswith(ruler_marker, i)]
    assert header[0x10:0x16] == ruler_marker + bytes(2)
    assert original == {str(p): sha(p.read_bytes()) for p in protected}

    destination = ROOT / "checkpoint_push_archives" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    destination.mkdir(parents=True, exist_ok=False)
    saved = destination / SOURCE.name
    with saved.open("xb") as f:
        f.write(payload)
    assert sha(saved.read_bytes()) == EXPECTED
    # Recheck the source after offline parsing; no claim of future immutability.
    assert sha(SOURCE.read_bytes()) == EXPECTED
    report = {
        "schema": "san14.checkpoint-push-archive.v1", "result": "PASS",
        "created": datetime.now().astimezone().isoformat(),
        "source": str(SOURCE), "archive": str(saved), "filename": SOURCE.name,
        "size": len(payload), "sha256": EXPECTED,
        "source_mtime_ns": b.st_mtime_ns,
        "export_result": str(RUN / "result.json"), "export_result_sha256": sha(result_bytes),
        "file_format_version": struct.unpack_from("<I", payload)[0],
        "date": date, "ruler_name": "张鲁", "ruler_name_metadata_offset": "0x10",
        "ruler_text_occurrences": ruler_offsets,
        "header_bytes_consumed": parsed["bytes_consumed"],
        "raw_header_prefix_sha256": sha(payload[:294]),
        "parsed_header_sha256": sha(header), "parsed_header_hex": header.hex(),
        "native_parser_success": True, "copied_native_global_writes": parsed["global_writes"],
        "stream_read_calls": parsed["read_calls"],
        "protected_evidence_unchanged": original,
        "passing_bounded_A_export": True,
        "game_process_access": False, "native_full_file_identity_verified": False,
        "full_world_verified": False, "load_authorized": False,
        "scope": "Real passing A export copied byte-for-byte. Captured native header parser executes offline in Unicorn; only raw stream Read is replaced by these file bytes. No native Steam read, B attachment, metadata registration, or world deserialization is performed.",
    }
    with (destination / "result.json").open("x", encoding="utf8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({k: report[k] for k in ("result", "archive", "size", "sha256", "date", "ruler_name", "native_full_file_identity_verified")}, ensure_ascii=False))
    print(destination / "result.json")


if __name__ == "__main__":
    main()

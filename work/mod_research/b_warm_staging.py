"""Slot 63 file staging only. Default plan is read-only; never loads the game.

An explicit local overwrite authorization is NOT a native no-readers permit.
The future coordinator must hold that independent engine lifetime boundary.
"""
from pathlib import Path
from contextlib import ExitStack
from datetime import datetime, timezone
import argparse, ctypes as C, hashlib, json, os, re, sys, time
from ctypes import wintypes as W

NAME = "svdexccSC03.s14"
SLOT = 63
MAX_BYTES = 16 * 1024 * 1024
INVALID = C.c_void_p(-1).value
K = None


class Refused(RuntimeError):
    pass


def need(value, text):
    if not value:
        raise Refused(text)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def kernel():
    global K
    if K is None:
        need(os.name == "nt", "Windows local filesystem required")
        K = C.WinDLL("kernel32", use_last_error=True)
        K.CreateFileW.argtypes = [W.LPCWSTR, W.DWORD, W.DWORD, C.c_void_p, W.DWORD, W.DWORD, W.HANDLE]
        K.CreateFileW.restype = W.HANDLE
        K.CloseHandle.argtypes = [W.HANDLE]
        K.GetDriveTypeW.argtypes = [W.LPCWSTR]
        K.GetDriveTypeW.restype = W.UINT
        K.GetFileInformationByHandle.argtypes = [W.HANDLE, C.c_void_p]
        K.ReadFile.argtypes = [W.HANDLE, C.c_void_p, W.DWORD, C.POINTER(W.DWORD), C.c_void_p]
        K.SetFilePointerEx.argtypes = [W.HANDLE, C.c_longlong, C.c_void_p, W.DWORD]
        K.ReplaceFileW.argtypes = [W.LPCWSTR, W.LPCWSTR, W.LPCWSTR, W.DWORD, C.c_void_p, C.c_void_p]
    return K


class Info(C.Structure):
    _fields_ = [("attributes", W.DWORD), ("created", W.FILETIME), ("accessed", W.FILETIME),
                ("modified", W.FILETIME), ("volume", W.DWORD), ("sizeHigh", W.DWORD),
                ("sizeLow", W.DWORD), ("links", W.DWORD), ("indexHigh", W.DWORD), ("indexLow", W.DWORD)]


class Handle:
    def __init__(self, path, *, share=1, directory=False, create=False):
        self.path = Path(path)
        self.value = kernel().CreateFileW(str(path), 0x80 if directory else 0x80000000,
                                         share, None, 1 if create else 3,
                                         0x00200000 | (0x02000000 if directory else 0), None)
        if self.value == INVALID:
            raise C.WinError(C.get_last_error())
        try:
            info = self.info()
            need(not info.attributes & 0x400, "Reparse handle rejected")
            need(bool(info.attributes & 0x10) == directory, "Wrong file kind")
            if not directory:
                need(info.links == 1, "Hardlinked file rejected")
        except BaseException:
            self.close()
            raise

    def info(self):
        value = Info()
        if not kernel().GetFileInformationByHandle(self.value, C.byref(value)):
            raise C.WinError(C.get_last_error())
        return value

    def close(self):
        if self.value != INVALID:
            kernel().CloseHandle(self.value)
            self.value = INVALID

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def snapshot(self):
        before = self.info()
        n = (before.sizeHigh << 32) | before.sizeLow
        need(0 < n <= MAX_BYTES, "File size out of bounds")
        need(kernel().SetFilePointerEx(self.value, 0, None, 0), "Seek failed")
        buf = C.create_string_buffer(n)
        read = W.DWORD()
        if not kernel().ReadFile(self.value, buf, n, C.byref(read), None):
            raise C.WinError(C.get_last_error())
        after = self.info()
        need(read.value == n and identity(before) == identity(after), "File changed while reading")
        raw = bytes(buf.raw[:n])
        return {"size": n, "sha256": digest(raw), "file_id": identity(after)}, raw


def identity(info):
    return [info.volume, info.indexHigh, info.indexLow, info.sizeHigh, info.sizeLow,
            info.modified.dwHighDateTime, info.modified.dwLowDateTime]


def clean_path(raw):
    path = Path(raw)
    need(path.is_absolute() and path.drive and not str(path).startswith("\\\\"), "Explicit local absolute path required")
    need(".." not in path.parts and not any(":" in part for part in path.parts[1:]), "Traversal or alternate stream rejected")
    need(not str(path).startswith("\\\\?"), "Device paths rejected")
    need(kernel().GetDriveTypeW(path.anchor) == 3, "Fixed local drive required")
    need(not any(part.endswith((" ", ".")) for part in path.parts[1:]), "Trailing Windows aliases rejected")
    return path


def pin_parents(stack, path, *, include=False):
    # Deny deletion/renaming of every directory ancestor while paths are used.
    dirs = list(reversed(path.parents)) + ([path] if include else [])
    for directory in dirs:
        stack.enter_context(Handle(directory, share=1, directory=True))


def read_file(path, share=1):
    with ExitStack() as stack:
        pin_parents(stack, path)
        return stack.enter_context(Handle(path, share=share)).snapshot()


def plan(source, target_directory, source_sha256, source_size):
    source = clean_path(source)
    target_directory = clean_path(target_directory)
    need(re.fullmatch(r"[0-9a-f]{64}", source_sha256 or "") and type(source_size) is int and 0 < source_size <= MAX_BYTES, "Expected source identity required")
    target = target_directory / NAME
    need(source != target, "Source and target must differ")
    with ExitStack() as stack:
        pin_parents(stack, source)
        pin_parents(stack, target_directory, include=True)
        actual, _ = stack.enter_context(Handle(source)).snapshot()
        need(actual["sha256"] == source_sha256 and actual["size"] == source_size, "Source hash/size mismatch")
        # First version only overwrites an existing, exactly backed-up target.
        previous, _ = stack.enter_context(Handle(target)).snapshot()
        need(actual["file_id"][:3] != previous["file_id"][:3], "Aliased source/target rejected")
        return {"schema": "san14.b-warm-staging-plan.v1", "slot": SLOT, "filename": NAME,
                "source": str(source), "target": str(target), "source_identity": actual,
                "previous_identity": previous, "engine_exclusion_proven": False, "load_permitted": False}


def save_new(path, raw):
    with Path(path).open("xb") as out:
        need(out.write(raw) == len(raw), "Short write")
        out.flush()
        os.fsync(out.fileno())


def authorize(permit_path, permit_sha256, proposed):
    actual, raw = read_file(clean_path(permit_path))
    need(actual["sha256"] == permit_sha256, "Local authorization hash mismatch")
    item = json.loads(raw)
    need(set(item) == {"schema", "nonce", "plan_sha256", "expires_unix", "retirement_reference", "retirement_sha256"}, "Authorization fields mismatch")
    need(item["schema"] == "san14.local-file-overwrite-authorization.v1" and
         re.fullmatch(r"[0-9a-f]{32}", item["nonce"] or "") and
         item["plan_sha256"] == digest(canonical(proposed)), "Authorization scope mismatch")
    need(type(item["expires_unix"]) is int and time.time() < item["expires_unix"] <= time.time() + 600, "Authorization expired or unbounded")
    evidence, _ = read_file(clean_path(item["retirement_reference"]))
    need(evidence["sha256"] == item["retirement_sha256"], "Retirement reference changed")
    # Opaque evidence is pinned, never promoted to native retirement/no-readers truth.
    return item


def apply(proposed, permit_path, permit_sha256, records_directory):
    need(proposed.get("schema") == "san14.b-warm-staging-plan.v1" and proposed.get("slot") == SLOT and proposed.get("filename") == NAME, "Wrong slot mapping")
    source = clean_path(proposed["source"])
    target = clean_path(proposed["target"])
    records = clean_path(records_directory)
    need(target.name == NAME and records != target.parent, "Dedicated existing records directory required")
    auth = authorize(permit_path, permit_sha256, proposed)
    nonce = auth["nonce"]
    backup = records / (nonce + ".previous.s14")
    intent = records / (nonce + ".intent.json")
    result_path = records / (nonce + ".result.json")
    temporary = target.parent / (".b-warm-" + nonce + ".staging")
    result = {"schema": "san14.b-warm-staging-result.v1", "result": "REFUSED", "replaced": False,
              "slot": SLOT, "target": str(target), "backup": str(backup), "plan_sha256": digest(canonical(proposed)),
              "engine_exclusion_proven": False, "load_permitted": False}
    entered = False
    with ExitStack() as stack:
        pin_parents(stack, records, include=True)
        pin_parents(stack, target.parent, include=True)
        pin_parents(stack, source)
        # A persistent lock name is harmless; its open handle is the exclusive lock.
        lock = target.parent / ".b-warm-staging.lock"
        if not os.path.lexists(lock):
            try:
                save_new(lock, b"san14-file-staging-lock-v1\n")
            except FileExistsError:
                pass
        stack.enter_context(Handle(lock, share=0))
        need(not any(os.path.lexists(p) for p in (backup, intent, result_path, temporary)), "One-shot transaction already exists")
        try:
            with Handle(source) as src, Handle(target, share=5) as old:
                current_source, raw = src.snapshot()
                previous, old_raw = old.snapshot()
                need(current_source == proposed["source_identity"] and previous == proposed["previous_identity"], "Plan stale: source/target changed")
                need(old.info().volume == stack.enter_context(Handle(records, directory=True, share=1)).info().volume, "Backup must be on target volume")
                save_new(intent, canonical({"plan": proposed, "authorization": auth, "permit_sha256": permit_sha256}))
                entered = True
                save_new(temporary, raw)
                staged, staged_raw = read_file(temporary)
                need(staged_raw == raw and staged["sha256"] == current_source["sha256"], "Staged bytes differ")
                # Keep an independently verified old-byte archive before any replacement.
                archive = records / (nonce + ".verified-old.s14")
                save_new(archive, old_raw)
                archived, archived_raw = read_file(archive)
                need(archived_raw == old_raw and archived["sha256"] == previous["sha256"], "Pre-replacement backup mismatch")
                # Target is still opened denying writes. READ/DELETE sharing is
                # required by ReplaceFile; no-readers must come from the coordinator.
                # External name swaps remain postchecked.
                need(old.snapshot()[0] == previous, "Target changed after backup")
                if not kernel().ReplaceFileW(str(target), str(temporary), str(backup), 0, None, None):
                    raise C.WinError(C.get_last_error())
                result["replaced"] = True
            # The API supplies the actual displaced file, never just a claimed backup.
            displaced, displaced_raw = read_file(backup)
            final, final_raw = read_file(target)
            need(displaced == previous and displaced_raw == old_raw, "Concurrent target name change: actual displaced identity differs")
            need(final_raw == raw and final["sha256"] == current_source["sha256"] and final["size"] == current_source["size"], "Final target differs")
            result.update(result="STAGED", target_identity=final, previous_identity=displaced,
                          source_identity=current_source, backup_byte_verified=True,
                          retirement_reference=auth["retirement_reference"], retirement_sha256=auth["retirement_sha256"])
        except BaseException as error:
            result.update(result="UNKNOWN_NO_RETRY" if entered else "REFUSED", error=repr(error))
        if entered:
            save_new(result_path, canonical(result))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--source-sha256")
    parser.add_argument("--source-size", type=int)
    parser.add_argument("--target-directory", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--permit", type=Path)
    parser.add_argument("--permit-sha256")
    parser.add_argument("--records-directory", type=Path)
    args = parser.parse_args(argv)
    if not args.source:
        parser.print_help()
        return 0
    need(args.target_directory and args.source_sha256 and args.source_size, "Explicit source identity and target directory required")
    value = plan(args.source, args.target_directory, args.source_sha256, args.source_size)
    if args.apply:
        need(args.permit and args.permit_sha256 and args.records_directory, "Explicit local authorization and records directory required")
        value = apply(value, args.permit, args.permit_sha256, args.records_directory)
    print(json.dumps(value, indent=2))
    return 0 if value.get("result", "STAGED") == "STAGED" else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Offline developer check: allowlisted protocol tests, local loopback only.

No game-process access, live-script discovery, downloads, compiler execution,
private-fixture content reads, or external network requests. Python 3.10+.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys
import traceback
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "outputs" / "san14-link"
DEFAULT_PRIVATE_FILES = {
    "runtime_image": "game-runtime-image.bin",
    "runtime_pdata": "runtime-pdata.bin",
}
sys.dont_write_bytecode = True


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dependency_status(name: str, baseline: dict) -> dict:
    result = {"recorded_version": baseline.get(name), "installed_version": None}
    try:
        module = importlib.import_module(name)
        # Check a little beyond package metadata; these operations are local.
        if name == "capstone":
            engine = module.Cs(module.CS_ARCH_X86, module.CS_MODE_64)
            if next(engine.disasm(b"\x90", 0)).mnemonic != "nop":
                raise RuntimeError("capstone could not decode a local NOP")
        elif name == "pefile":
            if not callable(module.PE):
                raise RuntimeError("pefile.PE is unavailable")
        elif name == "cryptography":
            importlib.import_module("cryptography.x509")
            importlib.import_module("cryptography.hazmat.primitives.asymmetric.rsa")
        try:
            result["installed_version"] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result["installed_version"] = getattr(module, "__version__", None)
        result["status"] = "AVAILABLE"
        result["module_path"] = str(Path(module.__file__).resolve()) if module.__file__ else None
        result["matches_recorded_version"] = (
            result["installed_version"] == baseline[name] if baseline.get(name) else None
        )
    except ModuleNotFoundError as error:
        result.update(status="MISSING", error=str(error))
    except Exception as error:
        result.update(status="BROKEN", error=f"{type(error).__name__}: {error}")
    return result


def compiler_status(vcvars: str | None) -> dict:
    result = {
        "windows": os.name == "nt",
        "python_bits": struct.calcsize("P") * 8,
        "machine": platform.machine(),
        "path_tools": {tool: shutil.which(tool) for tool in ("cl.exe", "ml64.exe", "link.exe")},
        "installations": [],
        "compiler_executed": False,
    }
    candidates = []
    if vcvars:
        candidates.append(Path(vcvars).expanduser().resolve())
    if os.name == "nt":
        for variable in ("ProgramFiles", "ProgramFiles(x86)"):
            location = os.environ.get(variable)
            if location:
                candidates.extend((Path(location) / "Microsoft Visual Studio").glob(
                    "*/*/VC/Auxiliary/Build/vcvars64.bat"))
    seen = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if str(candidate) in seen:
            continue
        seen.add(str(candidate))
        toolchains = []
        if candidate.is_file():
            vc = candidate.parent.parent.parent
            for compiler in (vc / "Tools" / "MSVC").glob("*/bin/Hostx64/x64/cl.exe"):
                toolchains.append({"cl": str(compiler), "ml64": str(compiler.with_name("ml64.exe")),
                                   "link": str(compiler.with_name("link.exe")),
                                   "complete": all(compiler.with_name(name).is_file()
                                                   for name in ("cl.exe", "ml64.exe", "link.exe"))})
        result["installations"].append({"vcvars64": str(candidate), "exists": candidate.is_file(),
                                         "x64_toolchains": toolchains})
    result["status"] = (
        "NOT_WINDOWS" if os.name != "nt" else
        "FOUND_NOT_COMPILED" if all(result["path_tools"].values()) or
        any(t["complete"] for i in result["installations"] for t in i["x64_toolchains"]) else
        "MISSING_OR_NOT_DISCOVERED"
    )
    return result


def private_paths(config_path: str | None, root_arg: str | None) -> dict:
    paths = DEFAULT_PRIVATE_FILES
    origin = "not configured"
    root_text = root_arg or os.environ.get("SAN14_PRIVATE_FIXTURE_ROOT")
    anchor = Path.cwd()
    if config_path:
        config = Path(config_path).expanduser().resolve()
        value = json.loads(config.read_text(encoding="utf-8-sig"))
        if not isinstance(value, dict) or set(value) != {"schema", "root", "files"} or value["schema"] != "san14.private-fixtures.v1":
            raise ValueError("Unsupported private fixture config; see tools/private-fixtures.example.json")
        root_text, paths = value["root"], value["files"]
        anchor = config.parent
        origin = str(config)
    elif root_text:
        origin = "--fixture-root" if root_arg else "SAN14_PRIVATE_FIXTURE_ROOT"
    if not root_text:
        return {"status": "NOT_CONFIGURED", "content_read": False,
                "note": "Optional for these protocol tests. Required inputs vary by archived native harness."}
    if not isinstance(root_text, str) or not isinstance(paths, dict):
        raise ValueError("Fixture root must be a string and files must be an object")
    root = Path(root_text).expanduser()
    root = (root if root.is_absolute() else anchor / root).resolve()
    files = {}
    for label, relative in paths.items():
        if not isinstance(label, str) or not isinstance(relative, str) or not relative:
            raise ValueError("Private file names and relative paths must be nonempty strings")
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Private file paths must stay beneath their configured root")
        path = (root / path).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Private fixture path escapes its configured root")
        files[label] = {"path": str(path), "exists": path.is_file(),
                        "bytes": path.stat().st_size if path.is_file() else None}
    return {"status": "PRESENT_METADATA_ONLY" if root.is_dir() and all(v["exists"] for v in files.values()) else "MISSING_INPUTS",
            "origin": origin, "root": str(root), "root_exists": root.is_dir(), "files": files,
            "content_read": False, "automatically_wires_legacy_scripts": False,
            "note": "Only path metadata was checked; no fixture compatibility or native test pass is asserted."}


def worker(output: Path, tls: bool) -> int:
    """Allowlist avoids importing top-level research scripts with live effects."""
    sys.path.insert(0, str(PROTOCOL))
    suites = unittest.TestSuite()
    modules = ["test_protocol", "test_timeline_protocol"]
    for name in modules:
        suites.addTests(unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(name)))
    expected = suites.countTestCases()
    with (output / "protocol-unittest.txt").open("w", encoding="utf-8") as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suites)
    report = {"modules": modules, "tests_discovered": expected, "tests_run": result.testsRun,
              "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
              "successful": result.wasSuccessful(), "transport": "real TCP on ephemeral 127.0.0.1 ports"}
    save(output / "protocol-result.json", report)
    tls_report = {"status": "SKIPPED", "reason": "cryptography unavailable or --skip-tls supplied"}
    if tls:
        try:
            # This named module imports only room_transport and room_session.
            # Override its scratch/output path without changing original source.
            room_test = importlib.import_module("run_room_selftest")
            room_test.SCRATCH = output / "tls-private"
            manifest = {"profile": {"protocol": "san14.room.v1", "game_sha256": "a"*64,
                        "adapter_contract": "research-no-native-room-adapter.v1", "checkpoint_sha256": "b"*64,
                        "rules_sha256": "c"*64},
                        "forces": [{"id": 12, "name": "Synthetic A", "main_district_id": 11},
                                   {"id": 2, "name": "Synthetic B", "main_district_id": 2}],
                        "source": {"fixture": "synthetic catalog; no native game state"}}
            manifest_path = output / "synthetic-room-manifest.json"
            save(manifest_path, manifest)
            sys.argv = [str(PROTOCOL / "run_room_selftest.py"), "--manifest", str(manifest_path),
                        "--output", str(output / "room-tls-result.json")]
            room_test.main()
            data = json.loads((output / "room-tls-result.json").read_text(encoding="utf-8"))
            tls_report = {"status": data["result"], "checks": data["check_count"],
                          "note": "Named checks from original lobby selftest; not extra unittest test cases."}
        except Exception:
            (output / "room-tls-error.txt").write_text(traceback.format_exc(), encoding="utf-8")
            tls_report = {"status": "FAILED", "error_log": "room-tls-error.txt"}
    save(output / "worker-result.json", {"protocol": report, "room_tls": tls_report})
    return 0 if result.wasSuccessful() and tls_report["status"] != "FAILED" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", help="Results directory; default .local/dev-check/<timestamp>")
    parser.add_argument("--deps-dir", help="Optional existing private Python dependency directory; never installed/copied")
    parser.add_argument("--vcvars64", help="Optional existing Visual Studio vcvars64.bat path; never executed")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--config", help="Private fixture path config JSON (optional)")
    group.add_argument("--fixture-root", help="Private fixture directory (optional); overrides environment variable")
    parser.add_argument("--skip-tls", action="store_true", help="Only TCP unittests; report TLS as skipped")
    parser.add_argument("--strict-env", action="store_true", help="Exit 3 if required development dependencies or Windows x64 MSVC are missing")
    parser.add_argument("--worker-output", help=argparse.SUPPRESS)
    parser.add_argument("--worker-tls", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error("Python 3.10 or newer is required")
    if args.worker_output:
        return worker(Path(args.worker_output).resolve(), args.worker_tls)
    if args.deps_dir:
        deps = Path(args.deps_dir).expanduser().resolve()
        if not deps.is_dir():
            parser.error("--deps-dir does not exist or is not a directory")
        sys.path.insert(0, str(deps))
    try:
        fixtures = private_paths(args.config, args.fixture_root)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    output = (Path(args.output_dir).expanduser().resolve() if args.output_dir else
              ROOT / ".local" / "dev-check" / datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    output.mkdir(parents=True, exist_ok=True)
    baseline = json.loads((ROOT / "tools" / "dependency-baseline.json").read_text(encoding="utf-8"))["recorded_versions"]
    dependencies = {name: dependency_status(name, baseline) for name in ("capstone", "pefile", "cryptography")}
    compiler = compiler_status(args.vcvars64)
    environment = {"python": sys.version, "executable": sys.executable, "platform": platform.platform(),
                   "repo_root": str(ROOT), "dependencies": dependencies, "native_toolchain": compiler,
                   "private_fixtures": fixtures, "native_tests_run": False}
    save(output / "environment.json", environment)
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    if args.deps_dir:
        env["PYTHONPATH"] = str(deps) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker-output", str(output)]
    if not args.skip_tls and dependencies["cryptography"]["status"] == "AVAILABLE":
        command.append("--worker-tls")
    with (output / "worker.log").open("wb") as log:
        child = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    result_file = output / "worker-result.json"
    tests = json.loads(result_file.read_text(encoding="utf-8")) if result_file.is_file() else {
        "protocol": {"successful": False, "error": "Worker did not finish; inspect worker.log"},
        "room_tls": {"status": "NOT_RUN"}}
    env_ok = (all(d["status"] == "AVAILABLE" for d in dependencies.values()) and compiler["windows"] and
              compiler["python_bits"] == 64 and compiler["machine"].lower() in ("amd64", "x86_64") and
              compiler["status"] == "FOUND_NOT_COMPILED")
    summary = {"created": datetime.now(timezone.utc).isoformat(),
               "protocol_status": "PASS" if child.returncode == 0 else "FAIL", **tests,
               "development_environment": "AVAILABLE_NOT_NATIVE_VALIDATED" if env_ok else "INCOMPLETE",
               "game_access": False, "internet_access": False, "local_loopback_allowed": True,
               "native_tests_run": False, "output_directory": str(output)}
    save(output / "summary.json", summary)
    print(f"Protocol: {summary['protocol_status']}; unittest cases run: {tests['protocol'].get('tests_run', 'unknown')}")
    print(f"Lobby TLS: {tests['room_tls']['status']}; named checks: {tests['room_tls'].get('checks', 'not run')}")
    for name, data in dependencies.items():
        print(f"{name}: {data['status']} ({data.get('installed_version') or 'version unavailable'})")
    print(f"Windows/MSVC: {compiler['status']}; private inputs: {fixtures['status']}")
    print(f"No native/gameplay verification. Report: {output / 'summary.json'}")
    if child.returncode:
        return 1
    return 3 if args.strict_env and not env_ok else 0


if __name__ == "__main__":
    raise SystemExit(main())

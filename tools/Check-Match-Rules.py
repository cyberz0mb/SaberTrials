"""Build and run native Match Rules checks without starting the game."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def tree(path):
    return {p.relative_to(path).as_posix(): sha(p) for p in sorted(Path(path).rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts}


def candidate(out, headers):
    source_path, build_path = out / "source-receipt.json", out / "build.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    built = json.loads(build_path.read_text(encoding="utf-8"))
    if built["source"] != sha(source_path):
        raise ValueError("The compiled modules do not match the current source receipt.")
    if tree(headers) != source["inputs"]:
        raise ValueError("Match Rules source changed; refresh and rebuild the candidate.")
    for role in ("frontend", "game"):
        if tree(out / role) != source["sources"][role]:
            raise ValueError(role + " source changed after the candidate was staged.")
    if tree(out / "menus") != source["menus"]:
        raise ValueError("Candidate menus changed after they were staged.")
    files = {name: out / ("build-game" if name.startswith("jamp") else "build-frontend") / "Release" / name
             for name in ("uix86_64.dll", "cgamex86_64.dll", "jampgamex86_64.dll")}
    files.update({p.relative_to(out / "menus").as_posix(): p for p in (out / "menus").rglob("*.menu")})
    package="zzzzzzzzzzzzzzzz_sabertrials_match_rules.pk3"
    files[package]=out/package
    with ZipFile(out/package) as archive:
        menus={p.relative_to(out/"menus").as_posix():p for p in (out/"menus").rglob("*.menu")}
        if set(archive.namelist())!=set(menus) or len(archive.namelist())!=len(menus) or archive.testzip() is not None:
            raise ValueError("Match Rules pure-compatible menu package has invalid members.")
        for name,path in menus.items():
            if archive.read(name)!=path.read_bytes():raise ValueError("Packed menu differs: "+name)
    if built["files"] != {name: sha(path) for name, path in files.items()}:
        raise ValueError("Compiled modules or menus do not match the current build receipt.")
    return {"source_sha256": sha(source_path), "build_sha256": sha(build_path),
            "module_sha256": {name: sha(path) for name, path in files.items() if name.endswith(".dll")}}


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=root / "dist/match-rules-01")
    parser.add_argument("--build-dir", type=Path, default=root / "dist/match-rules-checks/native")
    parser.add_argument("--header-dir", type=Path, default=root / "development-source/match-rules")
    parser.add_argument("--native-only", action="store_true", help="Run contract checks without certifying a compiled game candidate")
    args = parser.parse_args()
    build = args.build_dir.resolve()
    out, headers = args.out.resolve(), args.header_dir.resolve()
    if not args.native_only:
        (out / "verification.json").unlink(missing_ok=True)
    (build / "verification.json").unlink(missing_ok=True)
    evidence = None if args.native_only else candidate(out, headers)
    if not (root / "tests/match-rules/server_policy.cpp").is_file():
        raise ValueError("The independent server policy tests are missing.")
    test_sources = tree(root / "tests/match-rules")
    native_inputs = {name: sha(headers / name) for name in ("st_match_rules.h", "st_match_server_policy.h")}
    commands = [["cmake", "-S", str(root / "tests/match-rules"), "-B", str(build),
                 "-DST_MATCH_RULES=" + str(headers)]]
    if os.name == "nt" and not (build / "CMakeCache.txt").exists():
        commands[0] += ["-A", "x64"]
    commands += [["cmake", "--build", str(build), "--config", "Release"],
                 ["ctest", "--test-dir", str(build), "-C", "Release", "--output-on-failure",
                  "--output-junit", str(build / "results.xml")]]
    build.mkdir(parents=True, exist_ok=True)
    with (build / "check.log").open("w", encoding="utf-8") as log:
        for command in commands:
            process = subprocess.run(command, cwd=root, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
            print(process.stdout, end="", flush=True)
            log.write(process.stdout)
            log.flush()
            if process.returncode:
                return process.returncode
    results = ET.parse(build / "results.xml").getroot()
    cases = list(results.iter("testcase"))
    names={case.attrib.get("name") for case in cases}
    if len(cases) < 7 or not {"match_rules_ui_transactions","match_rules_server_adapter"}.issubset(names) or any(list(case.iter("failure")) or list(case.iter("skipped")) for case in cases):
        raise ValueError("The complete native contract and server policy suite did not pass.")
    if tree(root / "tests/match-rules") != test_sources or native_inputs != {
            name: sha(headers / name) for name in native_inputs}:
        raise ValueError("Native test source changed during verification; rerun the checks.")
    tests = {"count": len(cases), "names": [case.attrib["name"] for case in cases],
             "results_sha256": sha(build / "results.xml"),
             "log_sha256": sha(build / "Testing/Temporary/LastTest.log"),
             "test_source_sha256": test_sources, "header_sha256": native_inputs,
             "checker_sha256": sha(Path(__file__)),
             "executable_sha256": {name: sha(build / "Release" / (name + ".exe")) if os.name == "nt"
                                   else sha(build / name) for name in ("match_rules_core", "match_rules_server_policy")},
             "game_launched": False}
    if not args.native_only:
        if candidate(out, headers) != evidence:
            raise ValueError("Candidate changed while tests were running; rerun verification.")
        (out / "verification.json").write_text(json.dumps({
            "passed": True, **evidence, "tests": tests, "game_launched": False
        }, indent=2) + "\n", encoding="utf-8")
    (build / "verification.json").write_text(json.dumps({
        "passed": True, "kind": "native contract and server policy", "tests": tests,
        "game_launched": False, "header_directory": str(headers),
        "candidate_certified": not args.native_only
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError) as exc:
        print("Match Rules verification failed: " + str(exc), file=sys.stderr)
        sys.exit(1)

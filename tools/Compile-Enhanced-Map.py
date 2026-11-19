"""Compile a Jedi Academy map and validate the finished Classic or Enhanced BSP."""

import argparse
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist/enhanced-maps"


def compile_map(args):
    source = args.map.resolve(strict=True)
    if source.suffix.lower() != ".map" or not re.fullmatch(r"[a-zA-Z0-9_-]{1,48}", source.stem):
        raise ValueError("Use a .map source with a simple Jedi Academy map name")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    destination = output / (source.stem + ".bsp")
    env = os.environ.copy()
    if args.compiler_dlls:
        env["PATH"] = str(args.compiler_dlls.resolve(strict=True)) + os.pathsep + env["PATH"]
    common = [
        args.compiler.resolve(strict=True), "-game", "ja", "-fs_basepath", args.basepath.resolve(strict=True),
        "-threads", str(args.threads),
    ]
    for pakpath in args.pakpath:
        common.extend(("-fs_pakpath", pakpath.resolve(strict=True)))
    bsp_flags = ["-leaktest"]
    if args.profile == "enhanced":
        bsp_flags.extend(("-maxmapdrawsurfs", "262144"))
    if args.raw_faces:
        bsp_flags.append("-notjunc")
    else:
        bsp_flags.extend(("-meta", "-patchmeta"))
    results = {}
    stages = [("bsp", bsp_flags), ("vis", ["-vis"])]
    if not args.geometry_only:
        stages.append(("light", ["-light", "-fast"]))
    with tempfile.TemporaryDirectory(prefix="map-compile-", dir=output) as tmp:
        staged = Path(tmp) / source.name
        staged.write_bytes(source.read_bytes())
        for stage, flags in stages:
            log_path = output / f"{source.stem}-{stage}.log"
            started = time.perf_counter()
            with log_path.open("wb") as log:
                subprocess.run([*common, *flags, staged], stdout=log, stderr=subprocess.STDOUT,
                               env=env, timeout=args.timeout, check=True)
            log_text = log_path.read_text(encoding="utf-8", errors="replace")
            if "************ ERROR" in log_text or "LEAKED" in log_text:
                raise RuntimeError(f"{stage} failed. See {log_path}")
            results[stage] = round(time.perf_counter() - started, 3)
        bsp = staged.with_suffix(".bsp")
        with bsp.open("r+b") as stream:
            if stream.read(8) != b"RBSP" + struct.pack("<i", 1):
                raise ValueError("Compiler did not produce Jedi Academy RBSP 1")
            if args.profile == "enhanced":
                stream.seek(4)
                stream.write(struct.pack("<i", 2))
        subprocess.run([args.checker.resolve(strict=True), bsp], check=True)
        bsp.replace(destination)
    metadata = {"map": source.stem, "profile": args.profile, "bytes": destination.stat().st_size,
                "stage_seconds": results}
    (output / f"{source.stem}-compile.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map", type=Path)
    parser.add_argument("--profile", choices=("classic", "enhanced"), required=True)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--compiler-dlls", type=Path)
    parser.add_argument("--basepath", type=Path, default=ROOT.parent)
    parser.add_argument("--pakpath", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checker", type=Path, default=DIST / "build-check/Release/st-bsp-check.exe")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=900, help="Time limit per compiler stage in seconds")
    parser.add_argument("--raw-faces", action="store_true", help="Preserve unmerged faces for the stress fixture")
    parser.add_argument("--geometry-only", action="store_true", help="Build a BSP and PVS without baked lighting")
    compile_map(parser.parse_args())

"""Build a staged Saber Trials Enhanced Maps candidate from the local engine checkpoint."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist/enhanced-maps"
BASE = ROOT / "dist/mvp-cinematic-candidate-03"
AUTHORED = ROOT / "development-source/enhanced-maps"
DEPS = ROOT / "dist/handedness-baseline-06/deps"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def prepare():
    receipt = json.loads((BASE / "manifest.json").read_text(encoding="utf-8"))
    spec = importlib.util.spec_from_file_location("enhanced_map_overlay", AUTHORED / "overlay.py")
    overlay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(overlay)
    for role, apply in (("engine", overlay.apply), ("game", overlay.apply_bounds)):
        for name, digest in receipt["sources"][role].items():
            if sha(BASE / role / name) != digest:
                raise RuntimeError(f"{role} checkpoint drift at {name}")
        # Recopy on each run so edits always apply to known source text.
        shutil.copytree(BASE / role, OUT / role, dirs_exist_ok=True)
        apply(OUT / role)


def build_role(role, enabled, files):
    options = ("BuildMPEngine", "BuildMPDed", "BuildMPRdVanilla", "BuildMPRend2", "BuildMPGame",
               "BuildMPCGame", "BuildMPUI", "BuildSPEngine", "BuildSPGame", "BuildSPRdVanilla")
    folder = OUT / f"build-{role}"
    configure = ["cmake", "-S", str(OUT / role), "-B", str(folder),
                 "-G", "Visual Studio 18 2026", "-A", "x64", f"-DST_DEPS={DEPS}"]
    configure += [f"-D{key}={'ON' if key in enabled else 'OFF'}" for key in options]
    configure.append("-DST_STAFF_QA=OFF")
    with (OUT / f"build-{role}.log").open("w", encoding="utf-8") as log:
        subprocess.run(configure, stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(["cmake", "--build", str(folder), "--config", "Release", "--parallel", "8"],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    return {name: sha(folder / "Release" / name) for name in files}


def build():
    binaries = build_role(
        "engine", ("BuildMPEngine", "BuildMPDed", "BuildMPRdVanilla", "BuildMPRend2"),
        ("openjk.x86_64.exe", "openjkded.x86_64.exe", "rd-vanilla_x86_64.dll", "rd-rend2_x86_64.dll"))
    binaries.update(build_role("game", ("BuildMPGame",), ("jampgamex86_64.dll",)))
    manifest = {
        "engine_checkpoint_manifest": sha(BASE / "manifest.json"),
        "inputs": {file.name: sha(file) for file in sorted(AUTHORED.iterdir()) if file.is_file()},
        "binaries": binaries,
    }
    (OUT / "engine-build.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    prepare()
    if not args.prepare_only:
        build()

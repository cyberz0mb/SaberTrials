"""Build the Windows game, cgame, and UI for multi-team TFFA."""
import argparse
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "development-source/multiteam"
BASE = {
    "game": ROOT / "dist/bot-navigation-01/game",
    "frontend": ROOT / "dist/text-colors-01/frontend",
}
TARGETS = {
    "game": {"BuildMPGame": "jampgamex86_64"},
    "frontend": {"BuildMPCGame": "cgamex86_64", "BuildMPUI": "uix86_64"},
}
FLAGS = ("BuildMPEngine", "BuildMPDed", "BuildMPGame", "BuildMPCGame", "BuildMPUI",
         "BuildMPRdVanilla", "BuildMPRend2", "BuildSPEngine", "BuildSPGame", "BuildSPRdVanilla")


def prepare(role, out):
    target = out / role
    if not target.exists():
        shutil.copytree(BASE[role], target)
    patch = SOURCE / (role + ".patch")
    command = ["git", "apply", "--ignore-space-change", "--whitespace=nowarn",
               "--directory=" + target.relative_to(ROOT).as_posix()]
    applied = subprocess.run([*command, "--reverse", "--check", str(patch)], cwd=ROOT,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if applied.returncode:
        subprocess.run([*command, str(patch)], cwd=ROOT, check=True)
    shutil.copyfile(SOURCE / "st_tffa_teams.h", target / "codemp/game/st_tffa_teams.h")


def build(role, out):
    build_dir = out / ("build-" + role)
    options = [f"-D{flag}={'ON' if flag in TARGETS[role] else 'OFF'}" for flag in FLAGS]
    subprocess.run(["cmake", "-S", str(out / role), "-B", str(build_dir),
                    "-G", "Visual Studio 18 2026", "-A", "x64", *options], check=True)
    subprocess.run(["cmake", "--build", str(build_dir), "--config", "Release",
                    "--parallel", "6", "--target", *TARGETS[role].values()], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="multiteam-01", help="Build directory name under dist")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if Path(args.output).name != args.output or args.output in ("", ".", ".."):
        parser.error("--output must be a directory name")
    output = ROOT / "dist" / args.output
    for name in BASE:
        prepare(name, output)
        if not args.prepare_only:
            build(name, output)

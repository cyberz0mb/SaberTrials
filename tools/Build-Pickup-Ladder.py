"""Rebuild the two match formats on the combined Saber Trials Windows sources."""
import argparse
from pathlib import Path
import shutil
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED
import duel_privacy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "development-source/pug"
BASE = {"game": ROOT / "dist/match-rules-01/game",
        "frontend": ROOT / "dist/net/frontend",
        "engine": ROOT / "dist/net/engine"}
TARGETS = {"engine": {"BuildMPEngine": "openjk.x86_64", "BuildMPDed": "openjkded.x86_64"},
           "game": {"BuildMPGame": "jampgamex86_64"},
           "frontend": {"BuildMPUI": "uix86_64", "BuildMPCGame": "cgamex86_64"}}
OPTIONS = ("BuildMPEngine", "BuildMPDed", "BuildMPGame", "BuildMPCGame", "BuildMPUI", "BuildMPRdVanilla",
           "BuildMPRend2", "BuildSPEngine", "BuildSPGame", "BuildSPRdVanilla")
PACKAGE = "z_st_match_formats.pk3"


def prepare(output, role):
    tree = output / role
    if not tree.exists():
        shutil.copytree(BASE[role], tree)
    patch = SOURCE / (role + ".patch")
    apply = ["git", "apply", "--ignore-space-change", "--whitespace=nowarn",
             "--directory=" + tree.relative_to(ROOT).as_posix()]
    present = subprocess.run([*apply, "--check", "--reverse", patch], cwd=ROOT,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if present.returncode:
        subprocess.run([*apply, patch], cwd=ROOT, check=True)
    if role == "game":
        shutil.copyfile(SOURCE / "g_st_formats.inc", tree / "codemp/game/g_st_formats.inc")
    extra = SOURCE / role
    if extra.is_dir():
        shutil.copytree(extra, tree, dirs_exist_ok=True)
    if role == "game":
        duel_privacy.stage_server(tree)
    elif role == "frontend":
        duel_privacy.stage_client(tree)


def build(output, role):
    directory = output / ("build-" + role)
    configure = ["cmake", "-S", output / role, "-B", directory, "-G", "Visual Studio 18 2026",
                 "-A", "x64", "-DST_STAFF_QA=OFF", "-DST_DEPS=" + str(ROOT / "dist/handedness-baseline-06/deps")]
    configure += [f"-D{flag}={'ON' if flag in TARGETS[role] else 'OFF'}" for flag in OPTIONS]
    compile_cmd = ["cmake", "--build", directory, "--config", "Release", "--parallel", "5",
                   "--target", *TARGETS[role].values()]
    with (output / ("build-" + role + ".log")).open("w") as log:
        for command in (configure, compile_cmd):
            subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)


def package(output):
    menus = SOURCE / "menus"
    if not menus.is_dir():
        raise FileNotFoundError(menus)
    with ZipFile(output / PACKAGE, "w", ZIP_DEFLATED) as archive:
        for path in sorted(menus.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(menus).as_posix())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "build", "package", "all"])
    parser.add_argument("--role", choices=tuple(BASE))
    parser.add_argument("--output", default="pug-01", help="Directory name under dist")
    args = parser.parse_args()
    if not args.output or args.output in (".", "..") or Path(args.output).name != args.output:
        parser.error("output must be a directory name")
    output = ROOT / "dist" / args.output
    output.mkdir(exist_ok=True)
    for role in ([args.role] if args.role else BASE):
        if args.action in ("prepare", "all"):
            prepare(output, role)
        if args.action in ("build", "all"):
            build(output, role)
    if args.action in ("all", "package"):
        package(output)

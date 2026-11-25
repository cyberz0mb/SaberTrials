"""Build and install the menu alignment update over the active Saber Trials components."""
import argparse
from datetime import datetime
from importlib import import_module
from pathlib import Path
import shutil
import subprocess
import sys
from zipfile import ZIP_DEFLATED, ZipFile

sys.dont_write_bytecode = True
support = import_module("Build-Vulkan")
ROOT = support.ROOT
OUT = ROOT / "dist/menu-audit-20261123"
BASE = ROOT / "dist/menu-polish-20261123"
GAME = ROOT / "dist/pug-01"
PACKAGE = "zzzzzzzzzzzzzzzzzz_sabertrials_interface_audit.pk3"
UI = "uix86_64.dll"
GAME_DLL = "jampgamex86_64.dll"
CGAME_DLL = "cgamex86_64.dll"
SOURCE = ROOT / "development-source/menu-polish/interface_audit.py"
sys.path.insert(0, str(SOURCE.parent))
import interface_audit as layout


def sha(path):
    return support.sha(path) if path.is_file() else None


def targets():
    return {
        UI: OUT / "build/Release" / UI,
        "client/SaberTrialsUI.x86_64.dll": OUT / "build/Release" / UI,
        GAME_DLL: OUT / "game-build/Release" / GAME_DLL,
        CGAME_DLL: OUT / "cgame-build/Release" / CGAME_DLL,
        **{name: OUT / "menus" / name for name in layout.MENUS},
        PACKAGE: OUT / PACKAGE,
    }


def prepare():
    prior = support.read(ROOT / "dist/screenshot-menu-polish-install.json")
    recent = sorted((ROOT / "dist").glob("interface-audit-install-*.json"))
    current = recent[-1] if recent else ROOT / "dist/interface-audit-install.json"
    if current.is_file():
        installed = support.read(current)["after"]
        assert all(sha(ROOT / name) == digest for name, digest in installed.items())
        assert sha(BASE / "build/Release" / UI) == prior["after"][UI]
    else:
        assert sha(ROOT / UI) == sha(BASE / "build/Release" / UI) == prior["after"][UI]
        assert sha(ROOT / GAME_DLL) == sha(GAME / "build-game/Release" / GAME_DLL)
        assert sha(ROOT / CGAME_DLL) == sha(GAME / "build-frontend/Release" / CGAME_DLL)
    assert support.tree(BASE / "frontend") == support.read(BASE / "source.json")["sources"]
    OUT.mkdir(exist_ok=True)
    def copy_changed(source, target):
        src, dst = Path(source), Path(target)
        source_stat = src.stat()
        if dst.is_file():
            target_stat = dst.stat()
            if source_stat.st_size == target_stat.st_size and source_stat.st_mtime_ns == target_stat.st_mtime_ns:
                return str(dst)
        return shutil.copy2(src, dst)

    for source, target in ((BASE / "frontend", OUT / "frontend"), (GAME / "game", OUT / "game"),
                           (GAME / "frontend", OUT / "cgame")):
        shutil.copytree(source, target, dirs_exist_ok=True, copy_function=copy_changed)
    layout.patch_ui(OUT / "frontend")
    layout.patch_game(OUT / "game")
    layout.patch_cgame(OUT / "cgame")
    import_module("cosmetic_outfits").stage_cgame(OUT / "cgame")
    import_module("community_huds").stage_cgame(OUT / "cgame")
    layout.menus(ROOT, OUT / "menus")
    package_entries = {prefix + name: (OUT / "menus" / name).read_bytes()
                       for name in layout.MENUS for prefix in ("", "st_interface_audit/")}
    existing_pack = ROOT / PACKAGE
    package_matches = False
    if existing_pack.is_file():
        with ZipFile(existing_pack) as archive:
            package_matches = (len(archive.namelist()) == len(package_entries) and
                               set(archive.namelist()) == set(package_entries) and
                               all(archive.read(name) == data for name, data in package_entries.items()))
    if package_matches:
        shutil.copy2(existing_pack, OUT / PACKAGE)
    else:
        with ZipFile(OUT / PACKAGE, "w", ZIP_DEFLATED) as archive:
            for name, data in package_entries.items():
                archive.writestr(name, data)
    paths = [*ROOT.glob("*.pk3"), *ROOT.glob("*.dll"), *ROOT.joinpath("client").rglob("*"),
             *ROOT.joinpath("ui").rglob("*.menu")]
    previous = OUT / "audit-source.json"
    if previous.is_file():
        protected = {n: v for n, v in support.read(previous)["protected"].items() if n not in targets()}
    else:
        protected = {p.relative_to(ROOT).as_posix(): sha(p) for p in paths
                     if p.is_file() and p.relative_to(ROOT).as_posix() not in targets()}
    support.write(OUT / "audit-source.json", {
        "overlay": sha(SOURCE),
        **{name: support.tree(OUT / name) for name in ("frontend", "game", "cgame")},
        "menus": support.tree(OUT / "menus"), "package": sha(OUT / PACKAGE),
        "protected": protected, "before": {n: sha(ROOT / n) for n in targets()},
    })


def build(role):
    record = support.read(OUT / "audit-source.json")
    flags = import_module("Build-Adaptive-Network").FLAGS
    source_name, build_name, option, target = {
        "ui": ("frontend", "build", "BuildMPUI", "uix86_64"),
        "qa": ("frontend", "qa-build", "BuildMPUI", "uix86_64"),
        "game": ("game", "game-build", "BuildMPGame", "jampgamex86_64"),
        "cgame": ("cgame", "cgame-build", "BuildMPCGame", "cgamex86_64"),
    }[role]
    source, directory = OUT / source_name, OUT / build_name
    assert record[source.name] == support.tree(source)
    with (OUT / f"{role}-build.log").open("w") as log:
        configure = ["cmake", "-S", source, "-B", directory, "-G", "Visual Studio 18 2026", "-A", "x64",
                     "-DST_STAFF_QA=OFF", f"-DST_DEPS={ROOT / 'dist/handedness-baseline-06/deps'}",
                     *[f"-D{flag}={'ON' if flag == option else 'OFF'}" for flag in flags]]
        if role == "qa":
            configure += ["-DCMAKE_CXX_FLAGS=/DST_CONTROLS_QA"]
        subprocess.run(configure, stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(["cmake", "--build", directory, "--config", "Release", "--parallel", "5", "--target", target],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    support.write(OUT / f"{role}-artifact.json", {
        "tree": record[source_name], "dll": sha(directory / "Release" / (target + ".dll")),
    })
    print(f"Compiled {role}.")


def install():
    record = support.read(OUT / "audit-source.json")
    assert sha(SOURCE) == record["overlay"]
    assert sha(OUT / PACKAGE) == record["package"]
    for key in ("frontend", "game", "cgame", "menus"):
        assert support.tree(OUT / key) == record[key]
    helper = import_module("Install-Profile-Browser")
    helper.stopped()
    home, settings = helper.settings()
    files = targets()
    for name, digest in {**record["before"], **record["protected"]}.items():
        assert sha(ROOT / name) == digest, f"Installed file changed: {name}"
    for name in files:
        assert not (home / name).exists(), f"Profile override found: {name}"
    after = {name: sha(path) for name, path in files.items()}
    assert all(after.values())
    for role, source, filename in (("ui", "frontend", UI), ("game", "game", GAME_DLL),
                                   ("cgame", "cgame", CGAME_DLL)):
        assert support.read(OUT / f"{role}-artifact.json") == {"tree": record[source], "dll": after[filename]}
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = ROOT / "dist/backups" / f"interface-audit-{stamp}"
    receipt = ROOT / "dist" / f"interface-audit-install-{stamp}.json"
    changes = {name: path for name, path in files.items() if after[name] != record["before"][name]}
    unchanged = {name: digest for name, digest in after.items() if name not in changes}
    assert changes, "The audited build is already installed."
    import_module("Install-Handedness").install_transaction(
        ROOT, changes, {n: record["before"][n] for n in changes}, {n: after[n] for n in changes},
        {**record["protected"], **unchanged}, backup, receipt,
        dict(before=record["before"], after=after, protected=record["protected"], backup=str(backup),
             settings=settings, source=sha(OUT / "audit-source.json")))
    for name, digest in {**after, **record["protected"]}.items():
        assert sha(ROOT / name) == digest, name
    assert all(sha(Path(name)) == digest for name, digest in settings.items())
    print("Installed the updated assets and verified the protected files.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=("prepare", "ui", "game", "cgame", "qa", "install"))
    args = parser.parse_args()
    if args.step == "prepare":
        prepare()
    elif args.step == "install":
        install()
    else:
        build(args.step)

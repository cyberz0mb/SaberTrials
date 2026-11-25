"""Stage targeted menu fixes over the current compatibility frontend."""
import argparse
from datetime import datetime
from importlib import import_module
from pathlib import Path
import shutil
import subprocess
import sys
from zipfile import ZipFile, ZIP_DEFLATED

sys.dont_write_bytecode = True
support = import_module("Build-Vulkan")
compat = import_module("Build-Mod-Compatibility")
ROOT = support.ROOT
OUT = ROOT / "dist/menu-polish-20261123"
SOURCE = ROOT / "development-source/menu-polish/screenshot_layout.py"
BASE = compat.OUT / "frontend"
PACKAGE = "zzzzzzzzzzzzzzzzz_sabertrials_menu_polish.pk3"
DLL = "uix86_64.dll"
UI = (DLL, "client/SaberTrialsUI.x86_64.dll")
RATIONALE = ("ui_st_legacy.inc", "ui_st_rich.inc", "ui_st_saber_inspect.inc",
             "ui_st_workbench.inc", "ui_st_match_rules.inc", "menu_items.inc", "ui_shared.c")


def sha(path):
    return support.sha(path) if path.is_file() else None


def targets():
    overlay = support.module("screenshot_layout", SOURCE)
    return {
        **{n: OUT / "build/Release" / DLL for n in UI},
        **{n: OUT / "menus" / n for n in overlay.MENUS},
        PACKAGE: OUT / PACKAGE,
    }


def prepare():
    receipt = sorted((ROOT / "dist").glob("compat-install-*.json"))[-1]
    installed = support.read(receipt)
    for name in (*UI, compat.CLIENT):
        assert sha(ROOT / name) == installed["after"][name], f"Compatibility baseline changed: {name}"
    assert sha(compat.OUT / "ui-build/Release" / DLL) == installed["after"][DLL]
    assert not (ROOT / PACKAGE).exists(), "The menu polish package is already installed"
    OUT.mkdir(exist_ok=True)
    baseline = support.tree(BASE)

    def copy_changed(source, target):
        target = Path(target)
        if sha(Path(source)) != sha(target):
            shutil.copyfile(source, target)
        return str(target)

    shutil.copytree(BASE, OUT / "frontend", dirs_exist_ok=True, copy_function=copy_changed)
    assert support.tree(OUT / "frontend") == baseline, "Baseline source copy differs"
    overlay = support.module("screenshot_layout", SOURCE)
    overlay.patch_ui(OUT / "frontend")
    overlay.menus(ROOT, OUT / "menus")
    sources = support.tree(OUT / "frontend")
    assert set(sources) == set(baseline)
    assert {n for n in baseline if sources[n] != baseline[n]} == {"codemp/ui/" + n for n in RATIONALE}
    with ZipFile(OUT / PACKAGE, "w", ZIP_DEFLATED) as archive:
        for name in overlay.MENUS:
            archive.write(OUT / "menus" / name, name)
    change = targets()
    protected = {p.relative_to(ROOT).as_posix(): sha(p) for p in (
        *ROOT.glob("*.pk3"), *ROOT.glob("*.dll"), *ROOT.joinpath("client").rglob("*"),
        *ROOT.joinpath("ui").rglob("*.menu"))
        if p.is_file() and p.relative_to(ROOT).as_posix() not in change}
    support.write(OUT / "source.json", {
        "sources": sources, "overlay": sha(SOURCE), "pack": sha(OUT / PACKAGE),
        "menus": support.tree(OUT / "menus"), "protected": protected,
        "before": {n: sha(ROOT / n) for n in change},
        "baseline_receipt": receipt.name,
    })
    print("Staged seven menu files and a UI-only source patch.")


def validate_source():
    record = support.read(OUT / "source.json")
    assert record["overlay"] == sha(SOURCE)
    assert record["sources"] == support.tree(OUT / "frontend")
    assert record["menus"] == support.tree(OUT / "menus")
    assert record["pack"] == sha(OUT / PACKAGE)
    with ZipFile(OUT / PACKAGE) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == len(record["menus"])
        assert set(archive.namelist()) == set(record["menus"])
        for name in archive.namelist():
            assert archive.read(name) == (OUT / "menus" / name).read_bytes(), name
    return record


def build():
    validate_source()
    flags = import_module("Build-Adaptive-Network").FLAGS
    commands = (
        ["cmake", "-S", OUT / "frontend", "-B", OUT / "build", "-G", "Visual Studio 18 2026", "-A", "x64",
         "-DST_STAFF_QA=OFF", f"-DST_DEPS={ROOT / 'dist/handedness-baseline-06/deps'}",
         *[f"-D{flag}={'ON' if flag == 'BuildMPUI' else 'OFF'}" for flag in flags]],
        ["cmake", "--build", OUT / "build", "--config", "Release", "--parallel", "5", "--target", "uix86_64"],
    )
    with (OUT / "build.log").open("w") as log:
        for command in commands:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    support.write(OUT / "build.json", {"source": sha(OUT / "source.json"),
                                     "files": {n: sha(p) for n, p in targets().items()}})
    print("Compiled production UI.")


def install():
    record = validate_source()
    helper = import_module("Install-Profile-Browser")
    helper.stopped()
    home, settings = helper.settings()
    files = targets()
    for name, digest in {**record["before"], **record["protected"]}.items():
        assert sha(ROOT / name) == digest, f"Installed file changed: {name}"
    for name in files:
        assert not (home / name).exists(), f"Profile override found: {name}"
    after = {n: sha(p) for n, p in files.items()}
    assert support.read(OUT / "build.json") == {"source": sha(OUT / "source.json"), "files": after}
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = ROOT / "dist/backups" / f"menu-polish-{stamp}"
    receipt = ROOT / "dist/screenshot-menu-polish-install.json"
    import_module("Install-Handedness").install_transaction(
        ROOT, files, record["before"], after, record["protected"], backup, receipt,
        dict(before=record["before"], after=after, protected=record["protected"],
             backup=str(backup), settings=settings, source=sha(OUT / "source.json"),
             menu_build=sha(OUT / "build.json"), game_launched=False))
    for name, digest in {**after, **record["protected"]}.items():
        assert sha(ROOT / name) == digest, name
    assert all(sha(Path(name)) == digest for name, digest in settings.items())
    print("Installed menu polish and verified the UI, menu package, and saved settings.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "build", "install"))
    {"prepare": prepare, "build": build, "install": install}[parser.parse_args().action]()

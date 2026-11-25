"""Build an isolated anti-script client and dedicated server on the current Windows engine."""
import argparse
from importlib import import_module, util
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist/anti-script"
SOURCE = ROOT / "development-source"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def installed_baseline():
    installed = sha(ROOT/"client/SaberTrials.x86_64.exe")
    receipt = OUT/"baseline.json"
    current = OUT/"build/Release/openjk.x86_64.exe"
    if receipt.is_file() and current.is_file() and sha(current) == installed:
        return ROOT/json.loads(receipt.read_text())["source"]
    for binary in (ROOT/"dist").glob("*/build-engine/Release/openjk.x86_64.exe"):
        source = binary.parents[2]/"engine"
        if source.is_dir() and sha(binary) == installed:
            return source
    # Covers the first upgrade from an installed anti-script build, before
    # baseline receipts were recorded.
    for log in sorted((ROOT/"dist").glob("anti-script-install-*.json"), reverse=True):
        record = json.loads(log.read_text())
        if record["after"].get("client/SaberTrials.x86_64.exe") == installed:
            return ROOT/record["baseline"]
    raise ValueError("Supply --baseline with the engine source for the installed client.")


def prepare(baseline):
    tree = OUT / "engine"
    shutil.copytree(baseline, tree, dirs_exist_ok=True)
    mp = tree / "codemp"
    # The installed Vulkan engine predates the tournament account bridge.
    shutil.copytree(SOURCE / "accounts/codemp", mp, dirs_exist_ok=True)
    for name in ("st_event.h", "st_event_account_api.h"):
        shutil.copyfile(SOURCE / "bot-roles/codemp/game" / name, mp / "game" / name)
    cmake = tree / "CMakeLists.txt"
    content = cmake.read_text()
    if "SV_AccountCommand(" not in (mp / "server/sv_client.cpp").read_text():
        import_module("Build-Staff").account_hooks(tree)
        content = content.replace('PRIVATE "${MPDir}/server/sv_staff.cpp")',
            'PRIVATE "${MPDir}/server/sv_staff.cpp" "${MPDir}/server/sv_account.cpp")\n'
            '    target_include_directories(${st_target} PRIVATE "${MPDir}/game")')
        content = content.replace(" st_staff_core)", " st_staff_core st_account_core)")
    for role in ("staff", "accounts"):
        content, count = re.subn(r'add_subdirectory\("[^"]*development-source/'+role+r'"',
            'add_subdirectory("'+(SOURCE/role).as_posix()+'"', content)
        if count != 1:
            raise ValueError("Unable to locate "+role+" CMake dependency")
    cmake.write_text(content)
    spec = util.spec_from_file_location("anti_script_overlay", SOURCE/"anti-script/overlay.py")
    overlay = util.module_from_spec(spec)
    spec.loader.exec_module(overlay)
    overlay.apply(tree)
    (OUT/"baseline.json").write_text(json.dumps({"source":str(baseline.resolve().relative_to(ROOT)),
        "client":sha(ROOT/"client/SaberTrials.x86_64.exe"),"server":sha(ROOT/"client/openjkded.x86_64.exe")}))


def build():
    flags = ("BuildMPEngine","BuildMPDed","BuildMPGame","BuildMPCGame","BuildMPUI","BuildMPRdVanilla",
             "BuildMPRend2","BuildSPEngine","BuildSPGame","BuildSPRdVanilla")
    subprocess.run(["cmake","-S",OUT/"engine","-B",OUT/"build","-G","Visual Studio 18 2026","-A","x64",
        "-DST_DEPS="+str(ROOT/"dist/staff-deps"),"-DST_STAFF_QA=OFF",
        *[f"-D{f}={'ON' if f in flags[:2] else 'OFF'}" for f in flags]],check=True)
    subprocess.run(["cmake","--build",OUT/"build","--config","Release","--parallel","1",
                    "--target","openjk.x86_64","openjkded.x86_64"],check=True)

def install():
    binaries = {"client/SaberTrials.x86_64.exe":OUT/"build/Release/openjk.x86_64.exe",
                "client/openjkded.x86_64.exe":OUT/"build/Release/openjkded.x86_64.exe"}
    before = {name:sha(ROOT/name) for name in binaries}
    after = {name:sha(path) for name,path in binaries.items()}
    if before == after:
        print("Both engines are already installed.")
        return
    base = json.loads((OUT/"baseline.json").read_text())
    if before != dict(zip(binaries, (base["client"],base["server"]))):
        raise ValueError("Installed engine changed since preparation. Rebuild from the current source.")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = ROOT/"dist/backups"/("anti-script-"+stamp)
    state = ROOT/"dist"/("anti-script-install-"+stamp+".json")
    record = dict(before=before,after=after,backup=str(backup),baseline=base["source"],mode_default=0)
    import_module("Install-Handedness").install_transaction(ROOT,binaries,before,after,{},backup,state,record)
    print("Installed the client and dedicated server. Backup:", backup)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare","build","all","install"), default="all", nargs="?")
    parser.add_argument("--baseline", type=Path, help="Prepared source for the currently installed client")
    parser.add_argument("--install", action="store_true", help="Install both engines after a successful build")
    args = parser.parse_args()
    if args.action in ("all","prepare"):
        prepare(args.baseline or installed_baseline())
    if args.action in ("all","build"):
        build()
    if args.action == "install" or (args.install and args.action in ("all","build")):
        install()

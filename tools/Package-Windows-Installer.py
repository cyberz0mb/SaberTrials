"""Build the offline Windows installer from the published Full and Lite beta ZIPs."""
import argparse
import errno
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile
import zipfile

import beta_release


ROOT = beta_release.ROOT
RELEASE = ROOT / "dist/private-beta"
LAUNCHERS = {"SaberTrials.x86_64.exe", "SaberTrialsDed.x86_64.exe"}
ENGINE = "SaberTrials/client/SaberTrials.x86_64.exe"


def index(archive):
    files = {}
    seen = set()
    for info in archive.infolist():
        if info.is_dir():
            continue
        name = info.filename
        parts = name.split("/")
        if (any(part in ("", ".", "..") or any(c in part for c in '<>:"\\|?*{}') for part in parts)
                or not (parts[0] == "SaberTrials" or name in LAUNCHERS or name == "README.txt")
                or name.casefold() in seen):
            raise ValueError(f"Unexpected beta entry: {name}")
        seen.add(name.casefold())
        files[name] = info
    required = LAUNCHERS | {"README.txt", ENGINE, "SaberTrials/SaberTrialsDed.x86_64.exe"}
    if not required <= files.keys():
        raise ValueError(f"Missing beta files: {required - files.keys()}")
    return files


def file_line(source, target, component, flags="ignoreversion"):
    dest = PurePosixPath(target)
    directory = "{app}" if str(dest.parent) == "." else "{app}\\" + str(Path(dest.parent))
    return (f'Source: "{source}"; DestDir: "{directory}"; DestName: "{dest.name}"; '
            f'Components: {component}; Flags: {flags}')


def stage_archives(release, stage):
    with zipfile.ZipFile(release / beta_release.FULL) as full, zipfile.ZipFile(release / beta_release.LITE) as lite:
        all_files, lite_files = index(full), index(lite)
        if not lite_files.keys() <= all_files.keys():
            raise ValueError("Lite contains files missing from Full")
        beta_release.verify_engine(full.read(ENGINE))
        lines = []
        for name, info in all_files.items():
            if name == "README.txt":
                continue
            component = "game"
            if name in lite_files:
                other = lite_files[name]
                if (info.file_size, info.CRC) != (other.file_size, other.CRC):
                    raise ValueError(f"Edition mismatch: {name}")
            elif name.startswith("SaberTrials/client/translator/models/"):
                component = "languages"
            else:
                raise ValueError(f"Unexpected Full-only file: {name}")
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with full.open(info) as src, path.open("wb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
            flags = "ignoreversion"
            if name.endswith(".cfg") and (name.startswith("SaberTrials/server/") or name.count("/") == 1):
                flags += " onlyifdoesntexist uninsneveruninstall"
            lines.append(file_line(path, name, component, flags))
        for archive, edition, component in ((full, "Full", "languages"), (lite, "Lite", "not languages")):
            path = stage / (edition + "-README.txt")
            path.write_bytes(archive.read("README.txt"))
            lines.append(file_line(path, "SaberTrials/Windows-beta-README.txt", component))
        return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default="ISCC.exe", help="Inno Setup 7 compiler")
    parser.add_argument("--release", type=Path, default=RELEASE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--work", type=Path, help="Build scratch folder on a drive with space for both staging and output")
    args = parser.parse_args()
    release = args.release.resolve()
    output = (args.output or release / "Windows-Installers").resolve()
    output.mkdir(parents=True, exist_ok=True)
    if args.work:
        args.work.mkdir(parents=True, exist_ok=True)
    name = f"SaberTrials-Windows-{beta_release.VERSION}-Setup.exe"
    with tempfile.TemporaryDirectory(dir=args.work, prefix="st-setup-") as temp:
        stage = Path(temp).resolve()
        manifest = stage / "files.iss"
        manifest.write_text("\n".join(stage_archives(release, stage)), encoding="utf-8-sig")
        subprocess.run([args.compiler, "/Q", f"/DBetaVersion={beta_release.VERSION}",
                        f"/DBrandIcon={ROOT / 'assets/branding/SaberTrials.ico'}", f"/DFileList={manifest}",
                        "/O" + str(stage / "Build"), str(ROOT / "templates/windows/installer.iss")],
                       env={**os.environ, "TEMP": str(stage), "TMP": str(stage)}, check=True)
        candidate = stage / "Build" / name
        try:
            os.replace(candidate, output / name)
        except OSError as error:
            if error.errno != errno.EXDEV:
                raise
            # Cross-volume builds still publish only complete installers.
            with tempfile.NamedTemporaryFile(prefix=".st-setup-", suffix=".partial", dir=output, delete=False) as target:
                pending = Path(target.name)
            try:
                shutil.copyfile(candidate, pending)
                os.replace(pending, output / name)
            finally:
                pending.unlink(missing_ok=True)
    print(output / name)


if __name__ == "__main__":
    main()

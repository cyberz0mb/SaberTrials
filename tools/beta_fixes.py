"""Build Windows update ZIPs from the file lists of the distributed editions."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile

import beta_release


EDITIONS = ("Full", "Lite")
ARCHIVE = re.compile(r"SaberTrials-(Full|Lite)-(beta-\d+(?:\.\d+)+)\.zip")
ENGINE = "SaberTrials/client/SaberTrials.x86_64.exe"
LAUNCHERS = {"SaberTrials.x86_64.exe", "SaberTrialsDed.x86_64.exe"}
NOTE = "SaberTrials/docs/ZIP-update.txt"
DOWNLOAD_HINT = ("Returning Windows testers: in Fixes, choose the ZIP named for your installed beta. "
                 "Close Saber Trials and extract directly into Jedi Academy's GameData folder. "
                 "Use the complete edition for a first install.")


def version_number(version):
    if not re.fullmatch(r"beta-\d+(?:\.\d+)+", version):
        raise ValueError(f"Invalid beta version: {version}")
    return tuple(map(int, version[5:].split(".")))


def read_index(path):
    match = ARCHIVE.fullmatch(path.name)
    if not match:
        raise ValueError(f"Expected a versioned Full or Lite ZIP: {path}")
    edition, version = match.groups()
    files = {}
    seen = set()
    with ZipFile(path) as archive:
        header = archive.read("README.txt").decode("utf-8-sig").splitlines()[0]
        if header.split(" | ")[-1] != version:
            raise ValueError(f"Archive label disagrees with filename: {path}")
        for entry in archive.infolist():
            name = entry.filename
            if entry.is_dir() or name == "README.txt":
                continue
            parts = name.split("/")
            if (not (name in LAUNCHERS or parts[0] == "SaberTrials" and len(parts) > 1)
                    or any(p in ("", ".", "..") or p.endswith((" ", "."))
                           or re.search(r'[<>:"\\|?*\x00-\x1f]', p) for p in parts)
                    or name.casefold() in seen or name.casefold() == NOTE.casefold()):
                raise ValueError(f"Unexpected path in {path.name}: {name!r}")
            seen.add(name.casefold())
            files[name] = [entry.file_size, entry.CRC]
    if ENGINE not in files:
        raise ValueError(f"Missing game client in {path.name}")
    return version, edition, files


def current_indexes(full, lite):
    with ZipFile(lite) as archive:
        beta_release.verify_engine(archive.read(ENGINE))
    result = {}
    for path in (full, lite):
        version, edition, result_index = read_index(path)
        if version != beta_release.VERSION:
            raise ValueError(f"Expected {beta_release.VERSION}: {path}")
        result[edition] = result_index
    if set(result) != set(EDITIONS) or result["Lite"].get(ENGINE) != result["Full"].get(ENGINE):
        raise ValueError("Expected matching target Full and Lite clients")
    return result


def changed_files(previous, current):
    removed = previous.keys() - current.keys()
    if removed:
        raise ValueError(f"Extracting a ZIP cannot remove obsolete files: {sorted(removed)}")
    return {name for name, fingerprint in current.items() if previous.get(name) != fingerprint}


def make_fix(release, current, version, baselines):
    target = beta_release.VERSION
    if version_number(version) >= version_number(target):
        raise ValueError(f"Expected a beta older than {target}: {version}")
    changed = set()
    for ed in EDITIONS:
        if not baselines.get(ed):
            raise ValueError(f"Missing {ed} baseline for {version}")
        for previous in baselines[ed]:
            changed.update(changed_files(previous, current[ed]))
    # A ZIP for both editions must neither install Full-only models on Lite nor
    # overwrite editable settings already shipped by any supported baseline.
    for name in sorted(changed):
        if name not in current["Full"] or current["Full"][name] != current["Lite"].get(name):
            raise ValueError(f"{name} needs edition-specific delivery")
        if name.lower().endswith(".cfg") and any(name in old for group in baselines.values() for old in group):
            raise ValueError(f"{name} needs a configuration migration")
    folder = release / "Fixes"
    folder.mkdir(exist_ok=True)
    output = folder / f"SaberTrials-Windows-Fix-{version}-to-{target}.zip"
    note = (f"Saber Trials Windows update | {version} to {target}\r\n\r\n"
            "For an existing Windows Full or Lite installation of the starting version.\r\n"
            "Close the game and dedicated server. Extract the ZIP into Jedi Academy's GameData\r\n"
            "folder and replace the matching files. If you created a custom config using the\r\n"
            "same name as a new bundled preset, keep your own copy.\r\n"
            f"Start SaberTrials.x86_64.exe in GameData. The startup label should show {target}.\r\n"
            "Keep your installed language packs. A first install requires a complete edition.\r\n")
    with tempfile.TemporaryDirectory(dir=folder) as tmp:
        pending = Path(tmp) / output.name
        with ZipFile(release / beta_release.LITE) as source, ZipFile(pending, "w", ZIP_DEFLATED, compresslevel=6) as patch:
            for name in sorted(changed):
                with source.open(name) as src, patch.open(name, "w") as dest:
                    shutil.copyfileobj(src, dest, 1024 * 1024)
            patch.writestr(NOTE, note)
        with ZipFile(pending) as patch:
            actual = {i.filename: [i.file_size, i.CRC] for i in patch.infolist() if i.filename != NOTE}
            if actual.keys() != changed or patch.testzip():
                raise ValueError(f"Failed ZIP verification: {output.name}")
            for ed, copies in baselines.items():
                for previous in copies:
                    if previous | actual != current[ed]:
                        raise ValueError(f"Update does not reproduce {ed} {target}")
        os.replace(pending, output)
    print(f"{output.name}  {len(changed)} updated files  {output.stat().st_size / 1e6:.2f} MB", flush=True)
    return output


def record(release, current):
    history = release.parent / "beta-zip-history"
    folder = history / beta_release.VERSION
    folder.mkdir(parents=True, exist_ok=True)
    # A beta label may have multiple distributed revisions. Retain each index.
    data = json.dumps(current, sort_keys=True, separators=(",", ":")).encode("utf-8")
    target = folder / (hashlib.sha256(data).hexdigest() + ".json")
    with tempfile.TemporaryDirectory(dir=folder) as tmp:
        pending = Path(tmp) / target.name
        pending.write_bytes(data)
        os.replace(pending, target)


def prepare_next(full, stage):
    current = current_indexes(full, stage / beta_release.LITE)
    history = full.parent.parent / "beta-zip-history"
    older = [p for p in history.glob("beta-*") if p.is_dir() and version_number(p.name) < version_number(beta_release.VERSION)]
    if older:
        last = max(older, key=lambda p: version_number(p.name))
        previous = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(last.glob("*.json"))]
        make_fix(stage, current, last.name, {ed: [rev[ed] for rev in previous] for ed in EDITIONS})
    return current


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, default=beta_release.ROOT / "dist/private-beta")
    parser.add_argument("previous", type=Path, nargs="+", help="Earlier Full and Lite ZIPs, including any revisions")
    args = parser.parse_args()
    current = current_indexes(args.release / beta_release.FULL, args.release / beta_release.LITE)
    history = {}
    for path in args.previous:
        version, edition, index = read_index(path)
        history.setdefault(version, {}).setdefault(edition, []).append(index)
    for version, baselines in sorted(history.items(), key=lambda item: version_number(item[0])):
        make_fix(args.release, current, version, baselines)
    record(args.release, current)

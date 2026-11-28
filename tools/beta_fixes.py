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
# Windows betas actually distributed to testers. Building a ZIP does not add it here.
RELEASED_BASELINES = ("beta-1.11",)
FIRST_BETA = RELEASED_BASELINES[0]
FIX_NAME = "SaberTrials-Windows-Fix.zip"
ARCHIVE = re.compile(r"SaberTrials-(Full|Lite)-(beta-\d+(?:\.\d+)+)\.zip")
ENGINE = "SaberTrials/client/SaberTrials.x86_64.exe"
LAUNCHERS = {"SaberTrials.x86_64.exe", "SaberTrialsDed.x86_64.exe"}
NOTE = "SaberTrials/docs/ZIP-update.txt"
DOWNLOAD_HINT = (f"Updating from {', '.join(RELEASED_BASELINES)} (Windows Full or Lite): close Saber Trials "
                 f"and extract Fixes/{FIX_NAME} into GameData to update directly to {beta_release.VERSION}.")


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


def make_fix(release, current, baselines):
    target = beta_release.VERSION
    changed = set()
    for ed in EDITIONS:
        if not baselines.get(ed):
            raise ValueError(f"Missing {ed} baseline")
        for previous in baselines[ed]:
            changed.update(changed_files(previous, current[ed]))
    # Models added to Full can be installed individually by either edition.
    # Only omit them from the common update after checking their delivered ZIPs.
    optional = {}
    packs_used = []
    model_prefix = "SaberTrials/client/translator/models/"
    full_only = {n for n in changed if n in current["Full"] and n not in current["Lite"]}
    if full_only:
        for pack in sorted((release / "Language-Packs").glob("SaberTrials-Language-*.zip")):
            with ZipFile(pack) as archive:
                contents = {i.filename: [i.file_size, i.CRC] for i in archive.infolist()
                            if not i.is_dir() and i.filename != "README.txt"}
                if not (full_only & contents.keys()):
                    continue
                if (not all(n.startswith(model_prefix) and current["Full"].get(n) == sig
                            and n not in current["Lite"] for n, sig in contents.items()) or archive.testzip()):
                    raise ValueError(f"Invalid optional model delivery: {pack.name}")
                optional.update(contents)
                packs_used.append(pack.name)
    changed.difference_update(optional)
    # Unchanged presets introduced after 1.11 also belong in the cumulative ZIP.
    # An actual change to an existing default requires a separate migration.
    for name in sorted(changed):
        if name not in current["Full"] or current["Full"][name] != current["Lite"].get(name):
            raise ValueError(f"{name} needs edition-specific delivery")
        if name.lower().endswith(".cfg") and any(
            name in old and old[name] != current[ed][name]
            for ed in EDITIONS for old in baselines[ed]
        ):
            raise ValueError(f"{name} needs a configuration migration")
    folder = release / "Fixes"
    folder.mkdir(exist_ok=True)
    output = folder / FIX_NAME
    note = (f"Saber Trials Windows update to {target}\r\n\r\n"
            f"Apply once to an existing Windows Full or Lite installation of {', '.join(RELEASED_BASELINES)}.\r\n"
            "Close the game and dedicated server. Extract the ZIP into Jedi Academy's GameData\r\n"
            "folder and replace matching game files. Keep any tournament presets you edited.\r\n"
            f"Start SaberTrials.x86_64.exe in GameData. The startup label should show {target}.\r\n"
            "Keep your installed language packs. A first install requires a complete edition.\r\n")
    if packs_used:
        note += ("Menus and on-screen keyboards are included. For the additional offline chat models,\r\n"
                 "extract the desired files from Language-Packs into GameData. To match Full, add all of these:\r\n"
                 + "\r\n".join(packs_used) + "\r\n")
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
                    models = optional if ed == "Full" else {}
                    if previous | actual | models != current[ed]:
                        raise ValueError(f"Update does not reproduce {ed} {target}")
        os.replace(pending, output)
    print(f"{output.name}  {len(changed)} updated files  {output.stat().st_size / 1e6:.2f} MB", flush=True)
    return output


def record(release, current, version=None):
    history = release.parent / "beta-zip-history"
    folder = history / (version or beta_release.VERSION)
    folder.mkdir(parents=True, exist_ok=True)
    # A beta label may have multiple distributed revisions. Retain each index.
    data = json.dumps(current, sort_keys=True, separators=(",", ":")).encode("utf-8")
    target = folder / (hashlib.sha256(data).hexdigest() + ".json")
    with tempfile.TemporaryDirectory(dir=folder) as tmp:
        pending = Path(tmp) / target.name
        pending.write_bytes(data)
        os.replace(pending, target)


def cumulative_baselines(release):
    history = release.parent / "beta-zip-history"
    groups = {ed: [] for ed in EDITIONS}
    for version in RELEASED_BASELINES:
        if version_number(version) >= version_number(beta_release.VERSION):
            continue
        folder = history / version
        copies = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))]
        for ed in EDITIONS:
            indexes = [rev[ed] for rev in copies if ed in rev]
            if not indexes:
                raise ValueError(f"Missing {ed} index for {folder.name}")
            groups[ed].extend(indexes)
    return groups


def prepare_next(full, stage):
    current = current_indexes(full, stage / beta_release.LITE)
    if version_number(beta_release.VERSION) > version_number(FIRST_BETA):
        if (full.parent.parent / "beta-zip-history" / FIRST_BETA).is_dir():
            make_fix(stage, current, cumulative_baselines(full.parent))
        else:
            print(f"Full and Lite are ready. Import the {FIRST_BETA} and later indexes to generate the cumulative Fix.")
    return current


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, default=beta_release.ROOT / "dist/private-beta")
    parser.add_argument("previous", type=Path, nargs="*", help="Full and Lite ZIPs to index, starting at beta 1.11")
    args = parser.parse_args()
    current = current_indexes(args.release / beta_release.FULL, args.release / beta_release.LITE)
    for path in args.previous:
        version, edition, index = read_index(path)
        if version not in RELEASED_BASELINES or version_number(version) >= version_number(beta_release.VERSION):
            parser.error(f"{version} is not a released starting version for this Fix")
        record(args.release, {edition: index}, version)
    make_fix(args.release, current, cumulative_baselines(args.release))
    record(args.release, current)

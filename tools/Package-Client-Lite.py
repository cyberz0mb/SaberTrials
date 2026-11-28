"""Split the finished Windows client ZIP into Lite and optional offline chat packs."""
import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile
import beta_release


RELEASE = Path(__file__).resolve().parents[1] / "dist/private-beta"
TRANSLATOR = "SaberTrials/client/translator/"
MODELS = TRANSLATOR + "models/"
LITE = beta_release.LITE
LITE_LANGUAGES = ("en", "ru", "es", "fr", "pt", "pb")
GAME_GUIDE = """Enable Universal translator under Setup > Interface > Translation, choose
your reading language, and select Apply changes.

To add another language to Lite, close the game and extract its language ZIP
into Jedi Academy's GameData folder. Merge the SaberTrials folders when prompted."""


def pack_name(label):
    slug = label.replace("(", "").replace(")", "").replace(" ", "-")
    return f"SaberTrials-Language-{slug}.zip"


def write_zip(source, files, destination, readme=None):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        for info in files:
            with source.open(info) as original, archive.open(info.filename, "w") as output:
                shutil.copyfileobj(original, output, length=1024 * 1024)
        if readme is not None:
            archive.writestr("README.txt", readme)
    with zipfile.ZipFile(destination) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise ValueError(f"{destination.name} failed its CRC check on {bad}")
    print(f"{destination.name}  {destination.stat().st_size / 1e6:.1f} MB", flush=True)


def split(full):
    output = full.parent
    with zipfile.ZipFile(full) as source, tempfile.TemporaryDirectory(dir=output) as staging:
        stage = Path(staging)
        beta_release.verify_engine(source.read("SaberTrials/client/SaberTrials.x86_64.exe"))
        languages = json.loads(source.read(TRANSLATOR + "languages.json"))
        labels = {lang["code"]: lang["name"] for lang in languages}
        if "pt" in labels:
            labels["pt"] = "Portuguese (Portugal)"
        names = [labels[code] for code in LITE_LANGUAGES]
        included = ", ".join(names[:-1]) + ", and " + names[-1]
        included_text = f"includes offline chat translation for {included}."
        directions = {}
        packs = {code: [] for code in labels if code != "en"}
        for code in packs:
            for pair in (f"en-{code}", f"{code}-en"):
                directions[pair] = code
                manifest = json.loads(source.read(MODELS + pair + "/manifest.json"))
                if pair != f"{manifest['source']}-{manifest['target']}":
                    raise ValueError(f"Mismatched model manifest for {pair}")
                for name in manifest["files"]:
                    source.getinfo(MODELS + pair + "/" + name)
        core = []
        for info in source.infolist():
            if info.filename.startswith(MODELS):
                pair = info.filename[len(MODELS):].split("/", 1)[0]
                code = directions[pair]
                if code in LITE_LANGUAGES:
                    core.append(info)
                else:
                    packs[code].append(info)
            elif info.filename != "README.txt":
                core.append(info)

        original_readme = source.read("README.txt").decode("utf-8")
        readme = original_readme.rstrip() + "\n\nLite " + included_text + "\n\n" + GAME_GUIDE + "\n"
        write_zip(source, core, stage / LITE, readme)
        guide = [
            f"Saber Trials | Windows x64 multiplayer downloads | {beta_release.VERSION}", "",
            f"Full ({full.stat().st_size / 1e9:.2f} GB) includes the client and all offline chat language packs.",
            f"Lite ({(stage / LITE).stat().st_size / 1e9:.2f} GB) {included_text}",
            "Both editions require Jedi Academy.",
            f"Windows installer: run SaberTrials-Windows-{beta_release.VERSION}-Setup.exe and choose Lite or Full.",
            "Manual install: extract one edition's ZIP into GameData.",
            "Double-click SaberTrials.x86_64.exe to play or SaberTrialsDed.x86_64.exe to host.",
            "", GAME_GUIDE, "",
            "Optional language downloads for Lite", "",
        ]
        for code in sorted(packs.keys() - set(LITE_LANGUAGES), key=labels.get):
            label = labels[code]
            pack = stage / "Language-Packs" / pack_name(label)
            write_zip(source, packs[code], pack)
            guide.append(f"{label} - {pack.stat().st_size / 1e6:.0f} MB")
        (stage / "Patreon-Download-Guide.txt").write_text("\n".join(guide) + "\n", encoding="utf-8")
        (output / "Language-Packs").mkdir(exist_ok=True)
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                os.replace(path, output / path.relative_to(stage))
        # Older releases offered the now-bundled languages as separate downloads.
        for code in packs.keys() & set(LITE_LANGUAGES):
            (output / "Language-Packs" / pack_name(labels[code])).unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("full", nargs="?", type=Path, default=RELEASE / beta_release.FULL)
    split(parser.parse_args().full.resolve())

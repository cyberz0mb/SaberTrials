"""Stage the worldwide browser client/UI and Windows dedicated builds."""
import argparse
import csv
import gzip
from importlib import import_module, util
from ipaddress import IPv4Address
from pathlib import Path
import shutil
import struct
from urllib.request import urlopen
from zipfile import ZIP_DEFLATED, ZipFile

builder = import_module("Build-Translator")
ROOT = builder.ROOT
SOURCE = ROOT / "development-source/server-browser"
OUT = ROOT / "dist/server-browser-01"
builder.OUT = OUT
builder.RECEIPT = OUT / "source-receipt.json"
builder.ROLES["dedicated"] = ("engine", "BuildMPDed", "openjkded.x86_64", "client/openjkded.x86_64.exe")
BASES = ("engine", "frontend")
COUNTRY_REVISION = "335a7b77ede317e43caa70cfb358e7063eb1ed01"
COUNTRY_SHA256 = "95de6a930f2f2c2c92f200dcbcaf6d0b9e0e03f6bf60997c559b460465923650"


def default_country_csv():
    path = OUT / "server-country-ipv4.csv"
    if not path.exists():
        url = f"https://raw.githubusercontent.com/sapics/ip-location-db/{COUNTRY_REVISION}/server-country/server-country-ipv4.csv"
        with urlopen(url, timeout=30) as stream, path.with_suffix(".tmp").open("wb") as output:
            shutil.copyfileobj(stream, output)
        candidate = path.with_suffix(".tmp")
        if builder.sha(candidate) != COUNTRY_SHA256:
            raise ValueError("The pinned IPv4 download failed its checksum")
        candidate.replace(path)
    if builder.sha(path) != COUNTRY_SHA256:
        raise ValueError(f"The cached IPv4 file failed its checksum: {path}")
    return path

# UN M49 Americas split. Central America and the Caribbean are in North America.
COUNTRIES = (
    "AG AI AW BB BL BM BQ BS BZ CA CR CU CW DM DO GD GL GP GT HN HT JM KN KY LC MF MQ MS MX NI PA PM PR SV SX TC TT US VC VG VI",
    "AR BO BR CL CO EC FK GF GY PE PY SR UY VE",
    "AD AL AT AX BA BE BG BY CH CZ DE DK EE ES FI FO FR GB GG GI GR HR HU IE IM IS IT JE LI LT LU LV MC MD ME MK MT NL NO PL PT RO RS SE SI SJ SK SM UA VA XK",
    "RU",
    "AE AF AM AZ BD BH BN BT CN CY GE HK ID IL IN IQ IR JO JP KG KH KP KR KW KZ LA LB LK MM MN MO MV MY NP OM PH PK PS QA SA SG SY TH TJ TL TM TR TW UZ VN YE",
    "AS AU CC CK CX FJ FM GU HM KI MH MP NC NF NR NU NZ PF PG PN PW SB TK TO TV UM VU WF WS",
    "AO BF BI BJ BW CD CF CG CI CM CV DJ DZ EG EH ER ET GA GH GM GN GQ GW IO KE KM LR LS LY MA MG ML MR MU MW MZ NA NE NG RE RW SC SD SH SL SN SO SS ST SZ TD TF TG TN TZ UG YT ZA ZM ZW",
)


def regions(path):
    code_to_region = {code: index for index, row in enumerate(COUNTRIES, 1) for code in row.split()}
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", newline="") as stream:
        rows = sorted((int(IPv4Address(first)), int(IPv4Address(last)), code_to_region.get(code, 0))
                      for first, last, code in csv.reader(stream) if ":" not in first)
    merged = []
    for first, last, region in rows:
        if first > last or (merged and first <= merged[-1][1]):
            raise ValueError(f"Invalid or overlapping IPv4 ranges at {IPv4Address(first)}")
        if not region:
            continue
        if merged and merged[-1][1] + 1 == first and merged[-1][2] == region:
            merged[-1] = (merged[-1][0], last, region)
        else:
            merged.append((first, last, region))
    return b"".join(struct.pack(">IIB", *row) for row in merged)


def prepare(checkpoint, country_csv):
    OUT.mkdir(exist_ok=True)
    country_csv = country_csv or default_country_csv()
    overlay_spec = util.spec_from_file_location("server_browser_overlay", SOURCE / "overlay.py")
    overlay = util.module_from_spec(overlay_spec)
    overlay_spec.loader.exec_module(overlay)
    baseline = builder.read(checkpoint / "source-receipt.json")["sources"]
    for role in BASES:
        source = checkpoint / role
        if builder.tree(source) != baseline[role]:
            raise ValueError(f"{role} differs from the recorded checkpoint")
        staged = OUT / role
        shutil.copytree(source, staged, dirs_exist_ok=True)
        getattr(overlay, role)(staged)
    package = OUT / "zzzzzzzzzzzzzzz_sabertrials_browser.pk3"
    with ZipFile(package, "w", ZIP_DEFLATED) as archive:
        archive.write(ROOT / "ui/jamp/joinserver.menu", "ui/jamp/joinserver.menu")
        archive.writestr("ui/st-browser-regions.bin", regions(country_csv))
        archive.writestr("docs/st-browser-region-source.txt",
                         "IPv4 regional ranges derived from the ip-location-db server-country CSV (PDDL 1.0).\n"
                         f"Input SHA-256: {builder.sha(country_csv)}\n"
                         "https://github.com/sapics/ip-location-db/tree/main/server-country\n")
    builder.write(builder.RECEIPT, {
        "sources": {role: builder.tree(OUT / role) for role in BASES},
        "package": builder.sha(package),
        "country_csv": builder.sha(country_csv),
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "engine", "ui", "dedicated"))
    parser.add_argument("--checkpoint", type=Path, default=ROOT / "dist/emotes-01")
    parser.add_argument("--country-csv", type=Path)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.checkpoint, args.country_csv)
    else:
        builder.build(args.action)

"""Build the pinned, expanded-coordinate Q3Map2 using a Windows MSYS2 toolchain."""

import argparse
from pathlib import Path
import os
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist/enhanced-maps"
SOURCE = OUT / "netradiant"
REVISION = "68ecbed64b7be78741878c730279b5471d978c7c"
PATCH = ROOT / "development-source/enhanced-maps/q3map2.patch"


def build(msys):
    bash = msys.resolve(strict=True) / "usr/bin/bash.exe"
    OUT.mkdir(parents=True, exist_ok=True)
    if not SOURCE.exists():
        subprocess.run(["git", "clone", "--depth", "1", "--branch", "20260114",
                        "https://github.com/Garux/netradiant-custom.git", SOURCE], check=True)
    git = ["git", "-C", SOURCE]
    revision = subprocess.check_output([*git, "rev-parse", "HEAD"], text=True).strip()
    if revision != REVISION:
        raise RuntimeError(f"Unexpected NetRadiant revision {revision}")
    patched = subprocess.run([*git, "apply", "--reverse", "--check", PATCH], capture_output=True)
    if patched.returncode:
        subprocess.run([*git, "apply", PATCH], check=True)
    changed = subprocess.check_output([*git, "diff", "--name-only", "HEAD"], text=True).splitlines()
    if changed != ["tools/quake3/common/maxworld.h", "tools/quake3/q3map2/map.cpp"]:
        raise RuntimeError("The compiler source checkout has unrelated edits")

    # Use MSYS paths for package headers so spaces in the Jedi Academy path do
    # not become unquoted compiler arguments in the upstream Makefile.
    options = [
        "MAKEFILE_CONF=msys2-Makefile.conf", "DEPENDENCIES_CHECK=off",
        "DOWNLOAD_GAMEPACKS=no", "INSTALL_DLLS=no", "CXXFLAGS=-include cstdint",
        "CPPFLAGS_XML=-I/mingw64/include/libxml2",
        "CPPFLAGS_GLIB=-I/mingw64/include/glib-2.0 -I/mingw64/lib/glib-2.0/include",
        "CPPFLAGS_PNG=-I/mingw64/include/libpng16", "CPPFLAGS_JPEG=",
        "LIBS_XML=-lxml2", "LIBS_GLIB=-lglib-2.0", "LIBS_PNG=-lpng16",
        "LIBS_JPEG=-ljpeg", "LIBS_ZLIB=-lz", "LIBS_ASSIMP=-lassimp",
    ]
    env = {**os.environ, "MSYSTEM": "MINGW64", "CHERE_INVOKING": "1"}
    command = shlex.join(["make", *options, "-j8", "install/q3map2.exe"])
    with (OUT / "q3map2-build.log").open("wb") as log:
        subprocess.run([bash, "-lc", command], cwd=SOURCE, env=env, stdout=log,
                       stderr=subprocess.STDOUT, check=True)
    print(SOURCE / "install/q3map2.exe")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--msys", type=Path, default=OUT / "msys64")
    build(parser.parse_args().msys)

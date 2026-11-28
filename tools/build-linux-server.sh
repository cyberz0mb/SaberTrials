#!/bin/sh
# Run in the root of the source archive on x86_64 Linux. Never starts the game.
set -eu
export PATH="$HOME/.local/bin:$PATH"
root=$(pwd -P)
deps="$root/dist/staff-deps"
logs="$root/dist/linux-evidence"
mkdir -p "$logs"
python3 - <<'PY'
import hashlib,json,pathlib
root=pathlib.Path('dist/staff-deps')
lock=json.loads(pathlib.Path('development-source/staff/dependencies/lock.json').read_text())
for name in ('sodium','sqlite'):
    entry=lock[name]
    if hashlib.sha256((root/entry['archive']).read_bytes()).hexdigest()!=entry['sha256']:
        raise SystemExit('Pinned dependency checksum mismatch: '+name)
PY
if [ ! -f "$deps/sodium-linux/lib/libsodium.a" ]; then
 tar -xzf "$deps/sodium.tar.gz" -C "$deps"
 (cd "$deps/libsodium-stable" && ./configure --prefix="$deps/sodium-linux" --disable-shared --enable-static --with-pic && make -j3 && make install) > "$logs/sodium-build.log" 2>&1
fi
python3 -c 'import zipfile; zipfile.ZipFile("dist/staff-deps/sqlite.zip").extractall("dist/staff-deps")'
source="$root/dist/staff-work/OpenJK-1a6a643427aa347553e9073dac5570b33337c4d9"
for suite in linux accounts staff tournament server-browser anti-script; do
 set --
 if [ "$suite" = anti-script ]; then set -- "-DOPENJK_SOURCE=$source"; fi
 cmake -S "tests/$suite" "$@" -B "dist/linux-tests-$suite" -G Ninja -DCMAKE_BUILD_TYPE=Release > "$logs/$suite-configure.log" 2>&1
 cmake --build "dist/linux-tests-$suite" --parallel 3 > "$logs/$suite-build.log" 2>&1
 ctest --test-dir "dist/linux-tests-$suite" --output-on-failure > "$logs/$suite-test.log" 2>&1
 echo "$suite tests passed"
done
cmake -S tests/guard-native -B dist/linux-tests-guard -G Ninja -DCMAKE_BUILD_TYPE=Release \
 -DOPENJK_SOURCE="$source" > "$logs/guard-configure.log" 2>&1
cmake --build dist/linux-tests-guard > "$logs/guard-build.log" 2>&1
ctest --test-dir dist/linux-tests-guard --output-on-failure > "$logs/guard-test.log" 2>&1
python3 -m unittest discover -s tests -p test_guard_watch.py > "$logs/guard-watch-test.log" 2>&1
echo 'Guard tests passed'
cmake -S "$source" -B dist/linux-server-build -G Ninja -DCMAKE_BUILD_TYPE=Release \
 -DBuildMPDed=ON -DBuildMPGame=ON -DBuildMPEngine=OFF -DBuildMPCGame=OFF -DBuildMPUI=OFF \
 -DBuildMPRdVanilla=OFF -DBuildMPRend2=OFF -DBuildSPEngine=OFF -DBuildSPGame=OFF \
 -DBuildSPRdVanilla=OFF -DST_STAFF_QA=OFF > "$logs/server-configure.log" 2>&1
cmake --build dist/linux-server-build --parallel 3 > "$logs/server-build.log" 2>&1
echo 'Linux dedicated server and gameplay module compiled. No game was launched.'

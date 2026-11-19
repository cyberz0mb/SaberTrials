#!/bin/sh
# Place beside base/ and SaberTrials/. Use: ./start-sabertrials.sh [port]
# --check validates files/libraries without starting a game server.
set -eu
umask 077
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
check=false
if [ "${1:-}" = "--check" ]; then check=true; shift; fi
port=${1:-29070}
if [ "$#" -gt 0 ]; then shift; fi
case "$port" in ''|*[!0-9]*) echo 'Use a numeric server port, for example 29070.' >&2; exit 2;; esac
if [ "${#port}" -gt 5 ] || [ "$port" -lt 1 ] || [ "$port" -gt 65535 ]; then echo 'Port must be between 1 and 65535.' >&2; exit 2; fi
if [ "$(uname -m)" != 'x86_64' ]; then echo 'This package requires 64-bit Intel/AMD Linux.' >&2; exit 1; fi
for path in openjkded.x86_64 SaberTrials/jampgamex86_64.so SaberTrials/server.cfg.example base/assets0.pk3; do
 if [ ! -f "$root/$path" ]; then echo "Missing $path. Upload beside your existing base game folder." >&2; exit 1; fi
done
if [ ! -x "$root/openjkded.x86_64" ]; then echo 'Set openjkded.x86_64 permissions to 755 (executable).' >&2; exit 1; fi
if ! command -v ldd >/dev/null 2>&1; then echo 'The host must provide ldd for the dependency check.' >&2; exit 1; fi
for binary in "$root/openjkded.x86_64" "$root/SaberTrials/jampgamex86_64.so"; do
 if ! dependencies=$(ldd "$binary" 2>&1); then echo "$dependencies" >&2; exit 1; fi
 case "$dependencies" in *'not found'*) echo "$dependencies" >&2; echo 'Ask the host to install the missing Linux libraries.' >&2; exit 1;; esac
done
if [ "$check" = true ]; then echo "Files and libraries are ready for port $port. No game server was started."; exit 0; fi
if [ ! -f "$root/SaberTrials/server.cfg" ]; then cp "$root/SaberTrials/server.cfg.example" "$root/SaberTrials/server.cfg"; fi
cd "$root"
exec "$root/openjkded.x86_64" +set dedicated 2 +set net_port "$port" +set fs_basepath "$root" +set fs_homepath "$root" +set fs_game SaberTrials +exec server.cfg "$@"

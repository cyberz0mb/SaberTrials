"""Build both Windows GameData entry points for the release packager."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("SaberTrials.x86_64.exe", "SaberTrialsDed.x86_64.exe")


def build():
    output = ROOT / "dist/windows-launchers"
    subprocess.run(["cmake", "-S", ROOT / "development-source/windows-launchers",
                    "-B", output, "-A", "x64"], check=True)
    subprocess.run(["cmake", "--build", output, "--config", "Release"], check=True)
    return {name: output / "Release" / name for name in NAMES}


if __name__ == "__main__":
    build()

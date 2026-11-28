"""The public Windows beta identifier is shared by the engine and both downloads."""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "templates/windows/beta-version.txt").read_text().strip()
if not re.fullmatch(r"beta-[0-9]+(?:\.[0-9]+)+", VERSION):
    raise ValueError("Invalid Windows beta version")
FULL = f"SaberTrials-Full-{VERSION}.zip"
LITE = f"SaberTrials-Lite-{VERSION}.zip"
BUILD_LABEL = f"Saber Trials Windows {VERSION}"


def verify_engine(binary):
    if (BUILD_LABEL + "\n").encode("ascii") not in binary:
        raise ValueError(f"Rebuild the client for {VERSION} before packaging")

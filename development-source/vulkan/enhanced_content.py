"""Apply Vulkan content support to either a new or a restored engine checkpoint."""
from pathlib import Path
import subprocess


def apply(engine):
    patch = Path(__file__).with_name("enhanced-content.patch").resolve()
    command = ["git", "apply", "--unsafe-paths", "--ignore-space-change",
               "--directory=" + Path(engine).resolve().as_posix()]
    # A restored checkpoint may already contain the complete patch.
    if subprocess.run(command + ["--reverse", "--check", str(patch)],
                      capture_output=True).returncode == 0:
        return
    subprocess.run(command + [str(patch)], check=True)

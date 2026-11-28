from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import beta_fixes as fixes
import beta_release


class BetaFixTests(unittest.TestCase):
    def archives(self, directory, version, game):
        directory.mkdir(exist_ok=True)
        for edition in fixes.EDITIONS:
            name = f"SaberTrials-{edition}-{version}.zip"
            with ZipFile(directory / name, "w") as z:
                z.writestr("README.txt", f"Saber Trials | {version}\n")
                z.writestr(fixes.ENGINE, f"Saber Trials Windows {version}\n")
                z.writestr("SaberTrials/content.pk3", game)
                z.writestr("SaberTrials/server/host.cfg", "default")
                if edition == "Full":
                    z.writestr("SaberTrials/client/translator/models/optional", "language")

    def test_automatic_fix_includes_every_revision_and_skips_languages_and_configs(self):
        with tempfile.TemporaryDirectory() as tmp:
            release = Path(tmp) / "release"
            stage = Path(tmp) / "stage"
            for version, content in (("beta-1.1", "new"), ("beta-1.1", "old"), ("beta-1.2", "new")):
                full = f"SaberTrials-Full-{version}.zip"
                lite = f"SaberTrials-Lite-{version}.zip"
                self.archives(release, version, content)
                stage.mkdir(exist_ok=True)
                (stage / lite).write_bytes((release / lite).read_bytes())
                with patch.multiple(beta_release, VERSION=version, LITE=lite,
                                    BUILD_LABEL=f"Saber Trials Windows {version}"):
                    current = fixes.prepare_next(release / full, stage)
                    fixes.record(release, current)
            update, = (stage / "Fixes").glob("*.zip")
            with ZipFile(update) as z:
                self.assertEqual(set(z.namelist()), {fixes.ENGINE, "SaberTrials/content.pk3", fixes.NOTE})
                self.assertEqual(z.read("SaberTrials/content.pk3"), b"new")

    def test_extraction_cannot_remove_files(self):
        with self.assertRaisesRegex(ValueError, "obsolete"):
            fixes.changed_files({"removed": [1, 2]}, {})

    def test_custom_configuration_and_full_only_changes_require_separate_handling(self):
        previous = {ed: [{"host.cfg": [1, 1]}] for ed in fixes.EDITIONS}
        current = {ed: {"host.cfg": [2, 2]} for ed in fixes.EDITIONS}
        with self.assertRaisesRegex(ValueError, "configuration migration"):
            fixes.make_fix(Path(), current, "beta-0.1", previous)
        current = {ed: {"host.cfg": [1, 1]} for ed in fixes.EDITIONS}
        current["Full"]["language"] = [5, 6]
        with self.assertRaisesRegex(ValueError, "edition-specific"):
            fixes.make_fix(Path(), current, "beta-0.1", previous)


if __name__ == "__main__":
    unittest.main()

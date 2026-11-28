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
                if version != "beta-1.11":
                    z.writestr("SaberTrials/tournament-test.cfg", "public tournament preset")
                if version == "beta-1.12":
                    z.writestr("SaberTrials/menu.txt", "intermediate")
                else:
                    z.writestr("SaberTrials/menu.txt", "current")
                if edition == "Full":
                    z.writestr("SaberTrials/client/translator/models/optional", "language")

    def test_fix_uses_released_revisions_and_skips_internal_builds(self):
        with tempfile.TemporaryDirectory() as tmp:
            release = Path(tmp) / "release"
            stage = Path(tmp) / "stage"
            for version, content in (("beta-1.11", "old"), ("beta-1.11", "new"),
                                     ("beta-1.12", "new"), ("beta-1.13", "new"), ("beta-1.14", "new")):
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
            self.assertEqual(update.name, "SaberTrials-Windows-Fix.zip")
            with ZipFile(update) as z:
                self.assertEqual(set(z.namelist()), {fixes.ENGINE, "SaberTrials/content.pk3", fixes.NOTE,
                                                     "SaberTrials/tournament-test.cfg"})
                self.assertEqual(z.read("SaberTrials/content.pk3"), b"new")
                self.assertIn("beta-1.11", z.read(fixes.NOTE).decode())
            with patch.object(fixes, "RELEASED_BASELINES", ("beta-1.11", "beta-1.12")):
                copies = fixes.cumulative_baselines(release)
                self.assertTrue(any("SaberTrials/menu.txt" in fixes.changed_files(old, current["Full"])
                                    for old in copies["Full"]))

    def test_extraction_cannot_remove_files(self):
        with self.assertRaisesRegex(ValueError, "obsolete"):
            fixes.changed_files({"removed": [1, 2]}, {})

    def test_new_offline_models_use_verified_packs_and_stay_out_of_the_shared_fix(self):
        with tempfile.TemporaryDirectory() as tmp:
            release = Path(tmp)
            self.archives(release, "beta-1.11", "old")
            previous = {e: [fixes.read_index(release / f"SaberTrials-{e}-beta-1.11.zip")[2]]
                        for e in fixes.EDITIONS}
            self.archives(release, beta_release.VERSION, "new")
            model = "SaberTrials/client/translator/models/en-nl/model/model.bin"
            with ZipFile(release / beta_release.FULL, "a") as archive:
                archive.writestr(model, b"Dutch model")
            current = fixes.current_indexes(release / beta_release.FULL, release / beta_release.LITE)
            folder = release / "Language-Packs"
            folder.mkdir()
            pack = folder / "SaberTrials-Language-Dutch.zip"
            with ZipFile(pack, "w") as archive:
                archive.writestr(model, b"wrong contents")
            with self.assertRaisesRegex(ValueError, "Invalid optional model delivery"):
                fixes.make_fix(release, current, previous)
            with ZipFile(pack, "w") as archive:
                archive.writestr(model, b"Dutch model")
            with ZipFile(fixes.make_fix(release, current, previous)) as archive:
                self.assertNotIn(model, archive.namelist())
                self.assertIn(pack.name, archive.read(fixes.NOTE).decode())

    def test_custom_configuration_and_full_only_changes_require_separate_handling(self):
        previous = {ed: [{"host.cfg": [1, 1]}] for ed in fixes.EDITIONS}
        current = {ed: {"host.cfg": [2, 2]} for ed in fixes.EDITIONS}
        with self.assertRaisesRegex(ValueError, "configuration migration"):
            fixes.make_fix(Path(), current, previous)
        current = {ed: {"host.cfg": [1, 1]} for ed in fixes.EDITIONS}
        current["Full"]["language"] = [5, 6]
        with self.assertRaisesRegex(ValueError, "edition-specific"):
            fixes.make_fix(Path(), current, previous)


if __name__ == "__main__":
    unittest.main()

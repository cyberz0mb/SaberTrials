import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("combat_overlay", ROOT / "development-source/combat-controls/overlay.py")
combat = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(combat)


class CombatAnimationPriority(unittest.TestCase):
    def test_host_resolves_the_table_with_guard_poses(self):
        path = "models/players/_humanoid/animation.cfg"
        donors = b"BOTH_P1_S1_TR 10 3 -1 20\nBOTH_P6_S6_T_ 20 4 -1 20\nBOTH_P7_S7_T_ 30 5 -1 20\n"
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("zz_sabertrials_stances_v1", "zzz_sabertrials_hybrid_v1", "zz_sabertrials_styles_v1"):
                with ZipFile(root / (name + ".pk3"), "w") as archive:
                    archive.writestr(path, donors if name.endswith("styles_v1") else b"earlier animation table")
            with patch.object(combat, "ROOT", root):
                contract = combat.assets(root)
            # JKA's FS_PathCmp folds case to uppercase and searches packages in descending order.
            first = max(root.glob("*.pk3"), key=lambda p: p.name.upper())
            with ZipFile(first) as archive:
                animation = archive.read(path)
            self.assertTrue(animation.startswith(donors))
            self.assertEqual([g["first"] for g in contract["guards"]], [12, 23, 34])
            for guard in contract["guards"]:
                self.assertIn(f"{guard['name']} {guard['first']} 1 1 20".encode(), animation.splitlines())

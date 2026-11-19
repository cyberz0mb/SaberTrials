"""Asset preservation and mapping tests; no game process or installed-file writes."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def module():
    spec = importlib.util.spec_from_file_location('hybrid_animation', ROOT/'development-source/hybrid-styles/animation.py')
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class HybridAssets(unittest.TestCase):
    def test_append_only_and_deterministic(self):
        m = module()
        baseline = ROOT/'dist/stance-candidate-02/assets/zz_sabertrials_stances_v1.pk3'
        enums = ROOT/'dist/feint-candidate-01/game/codemp/game/anims.h'
        with tempfile.TemporaryDirectory(prefix='st-hybrid-assets-') as folder:
            out = Path(folder)
            manifest = m.generate(baseline, enums, out)
            first = (out/m.PACKAGE_NAME).read_bytes()
            self.assertEqual(manifest, m.generate(baseline, enums, out))
            self.assertEqual(first, (out/m.PACKAGE_NAME).read_bytes())
            with zipfile.ZipFile(baseline) as base, zipfile.ZipFile(out/m.PACKAGE_NAME) as new:
                cfg = base.read(m.PREFIX+'animation.cfg')
                self.assertTrue(new.read(m.PREFIX+'animation.cfg').startswith(cfg))
                self.assertLess(len(new.read(m.PREFIX+'animation.cfg')), m.PARSER_BUFFER_BYTES-1)
                # The unchanged rig/motion data stays in the stance dependency.
                self.assertNotIn(m.PREFIX+'_humanoid.gla', new.namelist())
                self.assertNotIn(m.PREFIX+'animevents.cfg', new.namelist())
            aliases = manifest['aliases']
            self.assertEqual(len(aliases), 231)
            self.assertEqual(len({a['name'] for a in aliases}), 231)
            self.assertEqual(len({a['id'] for a in aliases}), 231)
            self.assertEqual({a['style'] for a in aliases}, {4,5,6})
            for a in aliases:
                self.assertEqual(a['row'][:3], a['source_row'][:3])
                self.assertAlmostEqual(a['row'][3], a['source_row'][3]*a['rate'])
                self.assertLessEqual(abs(a['frame_lerp']), abs(a['source_frame_lerp']))
                self.assertLess(a['id'], 2048)
            self.assertEqual(manifest['original_count'], min(a['id'] for a in aliases))
            header = (out/'st_hybrid_anims.h').read_text()
            for name in ('STH_AnimForStyle','STH_OriginalAnim','STH_AnimStyle','STH_AnimationsValid','ST_HYBRID_ASSET_VERSION'):
                self.assertIn(name, header)

    def test_rejects_missing_source_motion(self):
        m = module()
        with tempfile.TemporaryDirectory(prefix='st-hybrid-assets-') as folder:
            p = Path(folder)/'broken.pk3'
            with zipfile.ZipFile(p, 'w') as z:
                z.writestr(m.PREFIX+'animation.cfg', '// no motions\n')
            with self.assertRaises(ValueError):
                m.generate(p, ROOT/'dist/feint-candidate-01/game/codemp/game/anims.h', Path(folder)/'output')

    def test_source_patch_preserves_old_ids(self):
        m = module()
        source = ROOT/'dist/feint-candidate-01/game'
        with tempfile.TemporaryDirectory(prefix='st-hybrid-assets-') as folder:
            out = Path(folder)
            manifest = m.generate(ROOT/'dist/stance-candidate-02/assets/zz_sabertrials_stances_v1.pk3', source/'codemp/game/anims.h', out/'assets')
            for name in ('codemp/game/anims.h','codemp/cgame/animtable.h','codemp/game/bg_public.h','codemp/game/st_direction_map.h','codemp/game/bg_panimate.c','codemp/ui/ui_main.c'):
                p = out/'tree'/name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes((source/name).read_bytes())
            old = m.enum_names((source/'codemp/game/anims.h').read_text())
            m.apply(out/'tree', out/'assets', manifest)
            new = m.enum_names((out/'tree/codemp/game/anims.h').read_text())
            self.assertEqual(new[:len(old)], old)
            self.assertEqual(new[len(old):], [a['name'] for a in manifest['aliases']])
            self.assertEqual((out/'tree/codemp/game/bg_public.h').read_text().count('#include "st_hybrid_anims.h"'), 1)
            self.assertIn('STH_AnimForStyle(hybridStyle, st_direction_normal_map[original-BOTH_A1_T__B_])',
                          (out/'tree/codemp/game/st_direction_map.h').read_text())
            self.assertIn('BGPAFtext[131072]', (out/'tree/codemp/game/bg_panimate.c').read_text())


if __name__ == '__main__':
    unittest.main()

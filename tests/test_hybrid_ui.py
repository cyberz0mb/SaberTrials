"""Hybrid UI regression checks; no client, renderer, map or server is launched."""
from pathlib import Path
import importlib.util
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'development-source/hybrid-styles'


def overlay():
    spec = importlib.util.spec_from_file_location('hybrid_ui_overlay', SOURCE / 'ui_overlay.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class HybridUI(unittest.TestCase):
    def test_menu_routes_are_in_named_saber_parents(self):
        with tempfile.TemporaryDirectory(prefix='st_hybrid_ui_') as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / 'dist/stance-candidate-02/menus', root / 'menus')
            mod = overlay()
            mod.apply_menus(root / 'menus')
            for file, parent, mode in [('saber.menu', 'saberMenu', 'Main'),
                                        ('ingame_saber.menu', 'ingame_saber', 'Game')]:
                text = (root / 'menus/ui/jamp' / file).read_text()
                page = mod.named_block(text, 'menuDef', parent)
                self.assertIn('name st_hybrid_options', page)
                self.assertIn('uiScript stHybridOpen' + mode, page)
                self.assertIn('st_stances_options', page)
                self.assertIn('stHybridCancel', mod.named_block(text, 'menuDef', 'st_hybrid_' + mode.lower()))
                stance = mod.named_block(text, 'menuDef', 'st_stances_' + mode.lower())
                self.assertIn('"Green" 3 "Purple" 4 "Orange" 5', stance)
                self.assertEqual(text.count('name st_hybrid_options'), 1)
            main = (root / 'menus/ui/jamp/saber.menu').read_text()
            self.assertNotIn('st_hybrid_options', mod.named_block(main, 'menuDef', 'st_handedness'))
            game = (root / 'menus/ui/jamp/ingame_saber.menu').read_text()
            parent = mod.named_block(game, 'menuDef', 'ingame_saber')
            self.assertIn('"Stances..." rect 15 228 180 22', parent)
            self.assertIn('"Combat styles..." rect 215 228 180 22', parent)

    def test_ui_and_hud_hooks(self):
        with tempfile.TemporaryDirectory(prefix='st_hybrid_ui_') as tmp:
            root = Path(tmp)
            mod = overlay()
            for kind in ('frontend', 'game'):
                target = root / kind
                for relative in mod.required_files(kind):
                    dest = target / relative
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(ROOT / 'dist/feint-candidate-01' / kind / relative, dest)
                mod.apply(target, kind)
            xcvar = (root / 'frontend/codemp/ui/ui_xcvar.h').read_text()
            self.assertIn('saberCombatStyle, "0", NULL, CVAR_ARCHIVE|CVAR_USERINFO', xcvar)
            self.assertIn('saberStyleLoadout, "", NULL, CVAR_ARCHIVE|CVAR_USERINFO', xcvar)
            for slot in range(1,4):
                self.assertIn(f'ui_saberStyleSlot{slot}, "{slot}", NULL, CVAR_INTERNAL', xcvar)
            stance = (root / 'frontend/codemp/ui/ui_st_stances.inc').read_text()
            self.assertIn('style<=5', stance)
            self.assertIn('STH_AnimForStyle(slot+1,attack)', stance)
            self.assertIn('STH_AnimationsValid', stance)
            self.assertIn('ST_HYBRID_ASSET_VERSION', stance)
            main = (root / 'frontend/codemp/ui/ui_main.c').read_text()
            self.assertIn('if(st_hybridKeepSaberDraft)return;', main)
            hud = (root / 'game/codemp/cgame/cg_draw.c').read_text()
            self.assertEqual(hud.count('ST_HybridHudLabel(cg.snap->ps.stHybrid.style'), 2)
            custom = (root / 'game/codemp/cgame/cg_sabertrials_hud.inc').read_text()
            self.assertIn('ST_HybridHudLabel(hybrid', custom)
            self.assertIn('ps->stHybrid.style', custom)

    def test_actual_ui_handler_with_mock_engine(self):
        """Compile and execute production menu code with deterministic engine stubs."""
        self.assertTrue((SOURCE / 'ui_st_hybrid.inc').is_file())
        with tempfile.TemporaryDirectory(prefix='st_hybrid_ui_native_') as tmp:
            temp = Path(tmp)
            harness = (SOURCE / 'ui_test_harness.cpp').read_text()
            harness = harness.replace('@FRAGMENT@', (SOURCE / 'ui_st_hybrid.inc').as_posix())
            (temp / 'test.cpp').write_text(harness)
            (temp / 'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.20)\nproject(hybrid_ui_test LANGUAGES CXX)\nadd_executable(hybrid_ui_test test.cpp)\ntarget_include_directories(hybrid_ui_test PRIVATE "' + SOURCE.as_posix() + '")\n')
            subprocess.run(['cmake', '-S', str(temp), '-B', str(temp / 'build'),
                            '-G', 'Visual Studio 18 2026', '-A', 'x64'], check=True, capture_output=True)
            subprocess.run(['cmake', '--build', str(temp / 'build'), '--config', 'Release'],
                           check=True, capture_output=True)
            subprocess.run([str(temp / 'build/Release/hybrid_ui_test.exe')], check=True)


if __name__ == '__main__':
    unittest.main()

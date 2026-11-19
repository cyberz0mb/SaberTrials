"""Regression for the native UI loader's first-wrapper stopping behavior."""
from pathlib import Path
import os
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path(os.environ.get('ST_MENU_ROOT', ROOT))


def loaded_menus(text):
    # Mirror UI_ParseMenu: Menu_New consumes its block; a remaining '}' ends
    # this file. Merely finding a menu name after that brace is insufficient.
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/|[{}]|[^\s{}]+', text, re.S)
    tokens = [t for t in tokens if not t.startswith(('//', '/*'))]
    menus = {}
    i = 0
    while i < len(tokens):
        if tokens[i] == '}':
            break
        if tokens[i] != 'menuDef':
            i += 1
            continue
        assert tokens[i+1] == '{'
        start, depth = i, 1
        i += 2
        while depth and i < len(tokens):
            depth += (tokens[i] == '{') - (tokens[i] == '}')
            i += 1
        assert depth == 0
        block = tokens[start:i]
        menus[block[block.index('name')+1].strip('"')] = ' '.join(block)
    return menus


class TournamentFrontend(unittest.TestCase):
    def test_loader_stops_at_file_wrapper(self):
        self.assertEqual(set(loaded_menus('{ menuDef { name first } } { menuDef { name lost } }')), {'first'})

    def test_play_menu_route_reaches_loaded_selection_and_lobby(self):
        menus = loaded_menus((TARGET/'ui/jamp/multiplayer.menu').read_text())
        self.assertIn('open st_main_tournament', menus['multiplayermenu'])
        self.assertIn('st_main_tournament', menus)
        self.assertIn('st_tournament_ready', menus)
        self.assertIn('open st_tournament_ready', menus['st_main_tournament'])
        for name, block in menus.items():
            if name.startswith('st_'):
                for dest in re.findall(r'open (st_\w+)', block):
                    self.assertIn(dest, menus, (name, dest))
                self.assertNotRegex(block, r'exec "(?:tournament |login|logout|connect |map |devmap )')

    def test_no_pause_tournament_entry(self):
        player = (TARGET/'ui/jamp/ingame_player.menu').read_text()
        self.assertNotIn('sabertrialsTournament', player)
        self.assertNotIn('ingame_tournament', player)

    def test_sample_cfgs_only_change_preview_cvars(self):
        cfgs = list(TARGET.glob('st-tournament-preview-*.cfg'))
        self.assertEqual(len(cfgs), 5)
        for cfg in cfgs:
            for line in cfg.read_text().splitlines():
                # Bracket cards use their own preview-only cvars.
                self.assertRegex(line, r'^set ui_st(?:Front\w+|Card(?:Title|A|B)\d+) "[^";\r\n]*"$')


if __name__ == '__main__':
    unittest.main()

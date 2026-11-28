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
        if tokens[i] == 'assetGlobalDef':
            i += 2
            depth = 1
            while depth:
                depth += (tokens[i] == '{') - (tokens[i] == '}')
                i += 1
            continue
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

    def test_live_lobby_routes_and_actions(self):
        menus = loaded_menus((TARGET/'ui/jamp/multiplayer.menu').read_text())
        self.assertIn('open st_main_tournament', menus['multiplayermenu'])
        self.assertIn('open joinserver', menus['st_main_tournament'])
        self.assertNotIn('preview-', menus['st_main_tournament'])
        menu_list = (TARGET/'ui/jampingame.txt').read_text()
        for entry in ('st_lobby', 'st_lobby_pause'):
            path = f'ui/jamp/{entry}.menu'
            self.assertIn(path, menu_list)
            menus.update(loaded_menus((TARGET/path).read_text()))
        self.assertIn('open st_tournament_ready', menus['ingame'])
        self.assertIn('ui_stLobbyActive', menus['ingame'])
        room = menus['st_tournament_ready']
        for action in ('join', 'ready', 'status'):
            self.assertIn(f'cmd st_lobby {action}', room)
        self.assertIn('cmd st_lobby leave', menus['st_lobby_leave'])
        for squad in range(1, 9):
            self.assertIn(f'cmd st_lobby join {squad}', menus['st_lobby_squads'])
        for name, block in menus.items():
            if name.startswith('st_lobby_') or name == 'st_tournament_ready':
                for link in re.findall(r'open (st_\w+)', block):
                    self.assertIn(link, menus, (name, link))


if __name__ == '__main__':
    unittest.main()

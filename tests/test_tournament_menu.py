"""Menu generation checks; no game process or server configuration is created."""
import importlib.util
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('tournament_menus', ROOT/'tools/Stage-Tournament.py')
menus = importlib.util.module_from_spec(spec)
spec.loader.exec_module(menus)
account_spec = importlib.util.spec_from_file_location('account_menus', ROOT/'tools/Stage-Accounts.py')
accounts = importlib.util.module_from_spec(account_spec)
account_spec.loader.exec_module(accounts)


class TournamentMenuTests(unittest.TestCase):
    def test_restaging_keeps_one_account_page_and_preserves_side_rails(self):
        original_root, original_stage = accounts.ROOT, accounts.STAGE
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for name in ('main.menu', 'ingame.menu'):
                    target = root/'ui/jamp'/name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes((ROOT/'ui/jamp'/name).read_bytes())
                accounts.ROOT, accounts.STAGE = root, root/'staged'
                accounts.stage()
                for name, rail, page in [('main.menu', 'main', 'st_main_account'), ('ingame.menu', 'ingame', 'st_pause_account')]:
                    before = (root/'ui/jamp'/name).read_text()
                    after = (accounts.STAGE/'ui/jamp'/name).read_text()
                    self.assertEqual(len(re.findall(r'menuDef\s*\{\s*name\s+"?'+page+r'\b', after)), 1)
                    a, b = menus.span(before, rail)
                    c, d = menus.span(after, rail)
                    # Account staging removes/reinserts its own link; compare
                    # tokens so harmless whitespace does not obscure changes.
                    self.assertEqual(re.findall(r'"[^\"]*"|\S+',before[a:b]), re.findall(r'"[^\"]*"|\S+',after[c:d]))
                first = {p.name: p.read_text() for p in (accounts.STAGE/'ui/jamp').glob('*.menu')}
                for name, value in first.items():
                    (root/'ui/jamp'/name).write_text(value)
                accounts.stage()
                for p in (accounts.STAGE/'ui/jamp').glob('*.menu'):
                    self.assertEqual(re.findall(r'"[^\"]*"|\S+',first[p.name]),re.findall(r'"[^\"]*"|\S+',p.read_text()))
        finally:
            accounts.ROOT, accounts.STAGE = original_root, original_stage

    def test_all_bracket_matches_and_substitutes_have_reachable_controls(self):
        text = menus.tournament()
        for page in range(4):
            name = 'st_event_bracket' + (f'_{page+1}' if page else '')
            a, b = menus.span(text, name)
            block = text[a:b]
            fields = [int(x) for x in re.findall(r'cvar "ui_ste(\d+)"', block) if 13 <= int(x) <= 43]
            self.assertEqual(fields, list(range(13+page*8, min(13+(page+1)*8, 44))))
            self.assertIn('close '+name, block)
        a, b = menus.span(text, 'st_event_substitutes')
        self.assertEqual(re.findall(r'st_event_substitute (\d+)', text[a:b]), ['0', '1', '2', '3', '4'])
        a, b = menus.span(text, 'ingame_tournament')
        self.assertNotIn('exec "tournament leave"', text[a:b])
        self.assertIn('open st_event_leave', text[a:b])
        a, b = menus.span(text, 'st_event_leave')
        self.assertIn('exec "tournament leave"', text[a:b])


if __name__ == '__main__':
    unittest.main()

from pathlib import Path
import importlib.util,json,unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('combat_audit',ROOT/'tools/Audit-Combat-Foundation.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)

class AuditTests(unittest.TestCase):
    def test_function_extraction_ignores_comment_and_string_braces(self):
        text='int f(void) { /* } */ const char* s="}"; // {\n if(s) {return 1;} return 0; }\nint next;'
        self.assertEqual(audit.body(text,'int f('),text[:text.index('\nint next;')])

    def test_broken_function_rejected(self):
        with self.assertRaises(ValueError):audit.body('int f(void) { /* } */','int f(')

    def test_generated_move_sources_are_complete(self):
        data=json.loads((ROOT/'dist/combat-foundation-01/style-move-matrix.json').read_text())
        self.assertFalse(data['enabled_in_game'])
        self.assertEqual(len(data['styles']),12)
        for style in data['styles']:
            self.assertEqual([d['direction'] for d in style['directions']],list(range(7)))
            for move in style['directions']:
                self.assertEqual(move['damage_group'],move['animation_group'])
                self.assertNotIn(move['damage_group'],(4,5))
                if style['family']==1:self.assertEqual(move['damage_group'],6)
                if style['family']==2:self.assertEqual(move['damage_group'],7)
                self.assertEqual(set(move['clips']),{'windup','attack','return'})
                for clip in move['clips'].values():
                    self.assertGreater(clip['frames'],0)
                    self.assertGreater(clip['nominal_ms'],0)
                    self.assertLess(clip['animation_id'],1558)
                    self.assertLessEqual(clip['first_frame']+clip['frames'],22443)

    def test_transition_sources_and_damage_fixtures(self):
        folder=ROOT/'dist/combat-foundation-01'
        report=json.loads((folder/'baseline-audit.json').read_text())
        self.assertEqual(report['installed_files_verified'],77)
        self.assertEqual(report['animation_group_stride'],77)
        for rows in report['transitions'].values():
            self.assertEqual(len(rows),42)
            self.assertTrue(all(row['cfg'] and row['cfg'][1]>0 and row['cfg'][3] for row in rows))
        self.assertEqual(audit.sha(folder/'fixtures/accepted_damage_functions.inc'),report['fixture_sha256'])
        for name,expected in report['damage_sources'].items():
            self.assertEqual(audit.sha(audit.BASE/'game/codemp/game'/name),expected)

if __name__=='__main__':unittest.main()

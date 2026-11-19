"""Feedback may tune Purple but must preserve the user's accepted Orange."""
from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]

class FeedbackPreservation(unittest.TestCase):
    def test_all_orange_aliases_and_shipped_motion_are_unchanged(self):
        old=ROOT/'dist/hybrid-candidate-02/assets'
        new=ROOT/'dist/hybrid-candidate-03/assets'
        before=json.loads((old/'aliases.json').read_text())
        after=json.loads((new/'aliases.json').read_text())
        self.assertEqual([a for a in before['aliases'] if a['style']==6],
                         [a for a in after['aliases'] if a['style']==6])
        # Mocap is still an authoring pilot, not silently substituted gameplay.
        for name in ('zz_sabertrials_styles_v1.pk3','zz_sabertrials_stances_v1.pk3'):
            self.assertEqual((old/name).read_bytes(),(new/name).read_bytes(),name)

    def test_both_animation_parsers_have_the_accepted_capacity(self):
        root=ROOT/'dist/hybrid-candidate-03'
        for kind in ('engine','game','frontend'):
            for source,identifier in [('codemp/ui/ui_main.c','UIPAFtext'),
                                      ('codemp/game/bg_panimate.c','BGPAFtext')]:
                self.assertIn(identifier+'[131072]',(root/kind/source).read_text())

if __name__=='__main__':unittest.main()

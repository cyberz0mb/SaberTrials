"""Accepted fixes must survive installing the newer mechanics build."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class Preservation(unittest.TestCase):
    def test_rend2_retains_accepted_portrait_fix(self):
        relative='engine/codemp/rd-rend2/tr_main.cpp'
        # Generated overlays normalize line endings; compare the entire source.
        for candidate in ('hybrid-candidate-01','hybrid-candidate-02','hybrid-candidate-03'):
            with self.subTest(candidate=candidate):
                self.assertEqual((ROOT/'dist'/candidate/relative).read_text(),
                                 (ROOT/'dist/portrait-vote-fix'/relative).read_text(),
                                 'Hybrid renderer must retain the complete accepted portrait viewport fix')

    def test_vote_reset_fix_is_preserved(self):
        relative='game/codemp/game/g_sabertrials.c'
        for candidate in ('hybrid-candidate-01','hybrid-candidate-02','hybrid-candidate-03'):
            with self.subTest(candidate=candidate):
                self.assertEqual((ROOT/'dist'/candidate/relative).read_bytes(),
                                 (ROOT/'dist/portrait-vote-fix'/relative).read_bytes(),
                                 'Accepted gametype vote handling must be retained')


if __name__=='__main__':unittest.main()

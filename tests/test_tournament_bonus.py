import concurrent.futures
import copy
from pathlib import Path
import tempfile
import unittest

from services.ranking.store import InvalidMatch, RankingStore
from services.ranking.tournament import BONUS_INTERVAL, summarize_bracket


def bracket(count=8):
    """Clearly synthetic fixture: left entrant wins each played series."""
    seeds = [f'p{i}' for i in range(1, count + 1)]
    seeds += [None] * ((1 << (count - 1).bit_length()) - count)
    rounds = []
    current = seeds
    while len(current) > 1:
        results = []
        for index in range(0, len(current), 2):
            pair = [p for p in current[index:index + 2] if p]
            results.append({'winner': pair[0] if pair else None,
                            'kind': ('empty', 'bye', 'played')[len(pair)]})
        rounds.append(results)
        current = [r['winner'] for r in results]
    return seeds, rounds


class TournamentBonusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='st-tournament-test-')
        self.path = Path(self.temp.name) / 'ranking.sqlite'
        self.now = 1000.0
        self.store = RankingStore(self.path, clock=lambda: self.now)
        for i in range(1, 33):
            self.store.register_verified_player(f'p{i}', f'Test player {i}')
        for server in ('s1', 's2'):
            self.store.register_server(server, 'Test server ' + server)
        for combat in ('original', 'trials'):
            self.store.register_ruleset(combat, 'duel', combat=combat, settings={'test_only': True})
        self.store.register_ruleset('team', 'team', combat='trials', team_size=2, settings={'test_only': True})

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def record(self, event='t1', server='s1', rules='trials', count=8, seeds=None, rounds=None):
        if seeds is None:
            seeds, rounds = bracket(count)
        return self.store.record_tournament(event, server, rules, seeds, rounds)

    def test_champion_gets_five_and_no_ranked_wins_or_loser_penalties(self):
        result = self.record()
        self.assertEqual((result['champion'], result['old'], result['new'], result['bonus']),
                         ('p1', 1000, 1005, 5))
        self.assertEqual(result['played_series_wins'], 3)
        rows = self.store.leaderboard('duel', 'trials')
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['wins'], rows[0]['losses'], rows[0]['matches']), (0, 0, 0))
        self.assertEqual((rows[0]['tournament_wins'], rows[0]['tournament_bonus_points']), (1, 5))
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM matches').fetchone()[0], 0)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM ratings').fetchone()[0], 1)

    def test_small_tournament_counts_championship_without_bonus(self):
        result = self.record(count=4)
        self.assertEqual(result['bonus_reason'], 'insufficient_entrants')
        self.assertEqual(result['bonus'], 0)
        row = self.store.leaderboard('duel', 'trials')[0]
        self.assertEqual((row['rating'], row['tournament_wins']), (1000, 1))
        # Ineligible championships do not consume the next eligible reward.
        self.assertEqual(self.record('t2')['bonus'], 5)

    def test_forfeit_is_not_a_played_series_win(self):
        seeds, rounds = bracket()
        rounds[0][0]['kind'] = 'forfeit'
        result = self.record(seeds=seeds, rounds=rounds)
        self.assertEqual(result['bonus_reason'], 'insufficient_played_wins')
        self.assertEqual((result['played_series_wins'], result['bonus']), (2, 0))

    def test_non_power_of_two_and_byes_follow_actual_played_series(self):
        for count in (5, 9, 17, 32):
            with self.subTest(count=count):
                seeds, rounds = bracket(count)
                summary = summarize_bracket(seeds, rounds)
                self.assertEqual(len(summary['entrants']), count)
                self.assertEqual(summary['champion'], 'p1')
        seeds, rounds = bracket(5)
        # p1 plays three series but five entrants still cannot earn a bonus.
        result = self.record(seeds=seeds, rounds=rounds)
        self.assertEqual(result['played_series_wins'], 3)
        self.assertEqual(result['bonus'], 0)

    def test_weekly_limit_is_global_across_servers_and_combat_presets(self):
        self.record()
        result = self.record('t2', server='s2', rules='original')
        self.assertEqual((result['bonus'], result['bonus_reason']), (0, 'weekly_limit'))
        self.assertEqual(self.store.leaderboard('duel', 'original')[0]['rating'], 1000)
        self.assertEqual(self.store.leaderboard('duel', 'trials')[0]['rating'], 1005)
        self.now += BONUS_INTERVAL - 1
        self.assertEqual(self.record('t3')['bonus'], 0)
        self.now += 1
        self.assertEqual(self.record('t4')['bonus'], 5)
        row = self.store.leaderboard('duel', 'trials')[0]
        self.assertEqual((row['rating'], row['tournament_wins'], row['tournament_bonus_points']),
                         (1010, 3, 10))

    def test_another_champion_has_independent_cooldown(self):
        self.record()
        seeds, rounds = bracket()
        # Relabel all p1 appearances to p9, another verified human account.
        seeds = ['p9' if p == 'p1' else p for p in seeds]
        for stage in rounds:
            for result in stage:
                if result['winner'] == 'p1':
                    result['winner'] = 'p9'
        self.assertEqual(self.record('t2', seeds=seeds, rounds=rounds)['bonus'], 5)

    def test_service_clock_rollback_does_not_bypass_limit(self):
        self.record()
        self.now -= BONUS_INTERVAL * 2
        self.assertEqual(self.record('t2')['bonus'], 0)

    def test_retries_are_immutable_even_after_cooldown_and_reopen(self):
        first = self.record()
        limited = self.record('t2')
        self.now += BONUS_INTERVAL * 2
        self.store.close()
        self.store = RankingStore(self.path, clock=lambda: self.now)
        self.assertEqual(self.record(), first)
        self.assertEqual(self.record('t2'), limited)
        self.assertEqual(self.store.leaderboard('duel', 'trials')[0]['tournament_wins'], 2)
        self.assertEqual(self.store.leaderboard('duel', 'trials')[0]['rating'], 1005)

    def test_conflicting_retries_wrong_server_and_rules_rejected(self):
        self.record()
        for args in ({'server': 's2'}, {'rules': 'original'}, {'count': 16}):
            with self.subTest(args=args), self.assertRaises(InvalidMatch):
                self.record(**args)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM tournaments').fetchone()[0], 1)

    def test_unknown_and_revoked_servers_cannot_submit(self):
        with self.assertRaises(InvalidMatch):
            self.record(server='fake')
        self.store.set_server_enabled('s1', False)
        with self.assertRaises(InvalidMatch):
            self.record()

    def test_unknown_accounts_and_team_rules_rejected(self):
        seeds, rounds = bracket()
        seeds[1] = 'bot:fake'
        with self.assertRaises(InvalidMatch):
            self.record(seeds=seeds, rounds=rounds)
        for rules in ('team', 'missing'):
            with self.subTest(rules=rules), self.assertRaises(InvalidMatch):
                self.record(rules=rules)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM tournaments').fetchone()[0], 0)

    def test_invalid_brackets_cannot_invent_a_champion(self):
        seeds, rounds = bracket()
        variants = []
        incomplete = copy.deepcopy(rounds)
        incomplete.pop()
        variants.append((seeds, incomplete))
        foreign = copy.deepcopy(rounds)
        foreign[-1][0]['winner'] = 'p32'
        variants.append((seeds, foreign))
        resurrected = copy.deepcopy(rounds)
        resurrected[1][0]['winner'] = 'p2'
        variants.append((seeds, resurrected))
        false_bye = copy.deepcopy(rounds)
        false_bye[0][0]['kind'] = 'bye'
        variants.append((seeds, false_bye))
        variants.extend([(seeds[:-1], rounds), ([seeds[0]] * 8, rounds),
                         ([None] * 8, rounds), ([{}] + seeds[1:], rounds)])
        for invalid_seeds, invalid_rounds in variants:
            with self.subTest(seeds=invalid_seeds, rounds=invalid_rounds), self.assertRaises(InvalidMatch):
                self.record(seeds=invalid_seeds, rounds=invalid_rounds)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM tournaments').fetchone()[0], 0)

    def test_active_ranked_match_retries_after_resolution_without_lost_bonus(self):
        self.store.start_match('m1', 's1', 'duel', 'trials', ['p1'], ['p2'],
                               accepted=['p1', 'p2'], game_type='duel')
        with self.assertRaises(InvalidMatch):
            self.record()
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM tournaments').fetchone()[0], 0)
        self.store.finish_match('m1', 's1', 'a')
        result = self.record()
        self.assertEqual((result['old'], result['new']), (1012, 1017))
        snap = self.store.start_match('m2', 's1', 'challenge', 'trials', ['p1'], ['p2'],
                                     accepted=['p1', 'p2'], game_type='ffa')
        self.assertEqual(snap['rating'], [1017, 988])

    def test_parallel_duplicate_results_apply_once(self):
        def submit(_):
            store = RankingStore(self.path, clock=lambda: 1000)
            try:
                return store.record_tournament('t1', 's1', 'trials', *bracket())
            finally:
                store.close()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, range(2)))
        self.assertEqual(results[0], results[1])
        self.assertEqual(self.store.leaderboard('duel', 'trials')[0]['tournament_wins'], 1)

    def test_parallel_different_events_share_weekly_limit(self):
        def submit(index):
            store = RankingStore(self.path, clock=lambda: 1000)
            try:
                return store.record_tournament(f't{index}', 's1', 'trials', *bracket())
            finally:
                store.close()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, range(2)))
        self.assertEqual(sorted(r['bonus'] for r in results), [0, 5])
        row = self.store.leaderboard('duel', 'trials')[0]
        self.assertEqual((row['rating'], row['tournament_wins']), (1005, 2))

    def test_v1_migration_preserves_ranked_history(self):
        self.store.start_match('m1', 's1', 'duel', 'trials', ['p1'], ['p2'],
                               accepted=['p1', 'p2'], game_type='duel')
        first = self.store.finish_match('m1', 's1', 'a')
        # Recreate the exact pre-tournament schema version without its new table.
        self.store.db.execute('DROP TABLE tournaments')
        self.store.db.execute('PRAGMA user_version=1')
        self.store.close()
        self.store = RankingStore(self.path, clock=lambda: self.now)
        self.assertEqual(self.store.db.execute('PRAGMA user_version').fetchone()[0], 2)
        self.assertEqual(self.store.finish_match('m1', 's1', 'a'), first)
        self.assertEqual(self.record()['new'], 1017)

    def test_team_leaderboard_does_not_inherit_player_championships(self):
        self.record()
        self.store.register_team('p1', 'Same ID team', '[TEST]')
        self.store.db.execute('INSERT INTO ratings(league,rules,subject,rating,wins) VALUES(?,?,?,?,?)',
                              ('team', 'team', 'p1', 1012, 1))
        row = self.store.leaderboard('team', 'team')[0]
        self.assertEqual((row['tournament_wins'], row['tournament_bonus_points']), (0, 0))

    def test_invalid_clock_rolls_back_without_championship(self):
        self.now = float('nan')
        with self.assertRaises(InvalidMatch):
            self.record()
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM tournaments').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()

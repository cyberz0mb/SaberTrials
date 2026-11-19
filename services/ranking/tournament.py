"""Validate a completed single-elimination bracket at the trusted service boundary.

This checks bracket consistency, not whether a game actually happened. The future
authenticated adapter must verify the locked roster and authoritative game reports.
"""

TOURNAMENT_BONUS = 5.0
BONUS_INTERVAL = 7 * 24 * 60 * 60
MIN_BONUS_ENTRANTS = 8
MIN_PLAYED_WINS = 3


def summarize_bracket(seeds, rounds):
    """Seeds contain account IDs/None; rounds contain winner/kind result objects.

    Each result has exactly {'winner': account_id_or_none, 'kind': kind}.
    Kinds: played, forfeit, bye, empty. Byes and forfeits never count as played
    series wins. A played series is one whole best-of series, not an individual
    kill or round. Empty seeds permit non-power-of-two entry counts.
    """
    if not isinstance(seeds, list) or len(seeds) not in (4, 8, 16, 32):
        raise ValueError('Bracket needs 4, 8, 16 or 32 seed slots')
    entrants = [p for p in seeds if p is not None]
    if (any(not isinstance(p, str) or not p for p in entrants)
            or len(entrants) < 4 or len(set(entrants)) != len(entrants)):
        raise ValueError('Bracket needs 4-32 distinct player accounts')
    if not isinstance(rounds, list) or len(rounds) != len(seeds).bit_length() - 1:
        raise ValueError('A complete bracket through the final is required')
    current = list(seeds)
    played_wins = dict.fromkeys(entrants, 0)
    for results in rounds:
        if not isinstance(results, list) or len(results) != len(current) // 2:
            raise ValueError('Wrong number of series in bracket round')
        advancing = []
        for index, result in enumerate(results):
            if not isinstance(result, dict) or set(result) != {'winner', 'kind'}:
                raise ValueError('Series needs exactly winner and kind')
            pair = [p for p in current[index * 2:index * 2 + 2] if p is not None]
            winner, kind = result['winner'], result['kind']
            if not pair:
                valid = winner is None and kind == 'empty'
            elif len(pair) == 1:
                valid = winner == pair[0] and kind == 'bye'
            else:
                valid = winner in pair and kind in ('played', 'forfeit')
            if not valid:
                raise ValueError('Series winner/kind does not match bracket progression')
            if kind == 'played':
                played_wins[winner] += 1
            advancing.append(winner)
        current = advancing
    champion = current[0]
    return {'champion': champion, 'entrants': entrants,
            'played_wins': played_wins[champion]}

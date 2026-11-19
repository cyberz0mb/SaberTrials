import math
import unittest

from services.ranking import rating


class RatingTests(unittest.TestCase):
    def test_approved_constants(self):
        self.assertEqual(rating.INITIAL_RATING, 1000.0)
        self.assertEqual(rating.K_FACTOR, 24.0)

    def test_equal_win(self):
        change = rating.rate_match(1000, 1000, 1)
        self.assertEqual((change.new_a, change.new_b), (1012, 988))

    def test_approved_examples(self):
        for difference, win, loss in [(400, 22, -2), (200, 18, -6),
                                      (0, 12, -12), (-200, 6, -18), (-400, 2, -22)]:
            with self.subTest(difference=difference):
                self.assertEqual(round(rating.rate_match(1000, 1000+difference, 1).delta_a), win)
                self.assertEqual(round(rating.rate_match(1000, 1000+difference, 0).delta_a), loss)

    def test_fractional_values_are_preserved(self):
        change = rating.rate_match(1000.25, 1200.25, 1)
        self.assertAlmostEqual(change.delta_a, 18.2339262396)
        self.assertNotEqual(change.new_a, round(change.new_a))

    def test_symmetry_and_conservation(self):
        for a, b in [(1000, 1000), (912.73, 1339.16), (-80, 340), (10000, 0)]:
            for result in [0, .5, 1]:
                change = rating.rate_match(a, b, result)
                reverse = rating.rate_match(b, a, 1-result)
                self.assertAlmostEqual(change.new_a, reverse.new_b)
                self.assertEqual(change.delta_b, -change.delta_a)
                self.assertAlmostEqual(change.new_a + change.new_b, a+b)

    def test_draw(self):
        self.assertEqual(rating.rate_match(1000, 1000, .5).delta_a, 0)
        change = rating.rate_match(1000, 1200, .5)
        self.assertGreater(change.delta_a, 0)
        self.assertLess(change.delta_b, 0)

    def test_expectation_extremes_do_not_overflow(self):
        for a, b in [(1e308, -1e308), (-1e308, 1e308), (1e308, 1e308)]:
            expected = rating.expected_score(a, b)
            self.assertTrue(math.isfinite(expected))
            self.assertGreaterEqual(expected, 0)
            self.assertLessEqual(expected, 1)

    def test_invalid_ratings(self):
        for bad in [float('nan'), float('inf'), -float('inf'), '1000', None, True]:
            for args in [(bad, 1000, 1), (1000, bad, 0)]:
                with self.subTest(args=args), self.assertRaises(ValueError):
                    rating.rate_match(*args)

    def test_invalid_result(self):
        for bad in [-1, 2, .25, float('nan'), 'win', None, True]:
            with self.subTest(result=bad), self.assertRaises(ValueError):
                rating.rate_match(1000, 1000, bad)

    def test_no_input_mutation_and_immutable_result(self):
        change = rating.rate_match(1000, 1200, 1)
        self.assertEqual((change.old_a, change.old_b), (1000, 1200))
        with self.assertRaises(AttributeError):
            change.delta_a = 99


if __name__ == '__main__':
    unittest.main()

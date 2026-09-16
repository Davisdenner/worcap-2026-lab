import unittest

import numpy as np

from src.round2 import Features, target_origins, weather_row


class Round2Tests(unittest.TestCase):
    def test_test_weather_boundary_skips_duplicate_december(self):
        train = np.array([[1.], [2.], [3.]])
        test = np.array([[3.], [4.], [5.]])
        self.assertEqual(weather_row(train, test, 2)[0], 3)
        self.assertEqual(weather_row(train, test, 3)[0], 4)
        self.assertEqual(weather_row(train, test, 4)[0], 5)
        with self.assertRaises(ValueError):
            weather_row(train, test, 5)

    def test_final_origins_match_months(self):
        origins = target_origins(2023)
        self.assertEqual(origins[0], 995)  # December 2022
        self.assertEqual(origins[-1], 1018)  # November 2024
        self.assertEqual((origins[0]+1) % 12, 0)

    def test_context_is_causal(self):
        f = Features.__new__(Features)
        n = 301*261
        f.lat = np.repeat(np.arange(301), 261)
        f.lon = np.tile(np.arange(261), 301)
        f.climo = np.zeros((12, n), dtype=np.float32)
        f.means = np.zeros((12, n, 9), dtype=np.float32)
        calls = []
        def row(j, origin):
            calls.append(origin)
            return np.full(n, origin+j, dtype=np.float32)
        f.row = row
        x = f.matrix(5, np.array([0, n-1]), True)
        self.assertEqual(x.shape, (2, 55))
        self.assertEqual(set(calls), {3, 4, 5})
        np.testing.assert_array_equal(x[:, 23], [4, 4])
        np.testing.assert_array_equal(x[:, 32], [1, 1])


if __name__ == "__main__":
    unittest.main()

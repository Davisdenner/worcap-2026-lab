import unittest
import numpy as np
from src.round4 import memory, groups, fit_weights


class MemoryTests(unittest.TestCase):
    def test_future_invariance(self):
        z = np.arange(60, dtype=float).reshape(20, 3)
        for config in ("mean3", "lags3", "mean6trend"):
            expected = memory(z, np.array([6, 7]), config)
            changed = z.copy()
            changed[8:] = -999
            np.testing.assert_array_equal(expected, memory(changed, np.array([6, 7]), config))

    def test_lags_order(self):
        z = np.arange(20).reshape(20, 1)
        np.testing.assert_array_equal(memory(z, np.array([5]), "lags3"), [[5, 4, 3]])
        np.testing.assert_array_equal(memory(z, np.array([5]), "mean3"), [[5, 4]])
        np.testing.assert_array_equal(memory(z, np.array([5]), "mean6trend"), [[5, 2.5, 2]])

    def test_missing_history(self):
        with self.assertRaises(ValueError):
            memory(np.ones((10, 2)), np.array([1]), "mean3")

    def test_group_calendar_and_bounds(self):
        g = groups()
        self.assertEqual(g.shape, (24, 301, 261))
        np.testing.assert_array_equal(g[0], g[11])
        np.testing.assert_array_equal(g[:12], g[12:])
        self.assertEqual(len(np.unique(g)), 12)

    def test_regularized_weights(self):
        w = fit_weights(np.ones((3, 3)))
        np.testing.assert_allclose(w, [.5, .25, .25], atol=1e-7)
        w = fit_weights(np.diag([100., 1., 2.]))
        self.assertAlmostEqual(w.sum(), 1.)
        self.assertTrue(np.all(w >= .1-1e-8))
        self.assertTrue(np.all(w <= .7+1e-8))

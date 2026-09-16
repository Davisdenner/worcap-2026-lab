import unittest
import numpy as np
from scipy.ndimage import uniform_filter

from src.round3 import seasonal_design, seasonal_mask


class Round3Tests(unittest.TestCase):
    def test_coarsening_does_not_mix_future_months(self):
        values = np.zeros((3, 10, 10), dtype=np.float32)
        values[2] = 100
        coarse = uniform_filter(values, size=(1, 9, 9), mode="nearest")
        np.testing.assert_array_equal(coarse[:2], 0)
        np.testing.assert_array_equal(coarse[2], 100)

    def test_seasonal_window_wraps_december_to_january(self):
        # Origins Jan..Dec yield target months Feb..Jan.
        mask = seasonal_mask(np.arange(12), 0)
        np.testing.assert_array_equal(np.flatnonzero(mask), [0, 1, 9, 10, 11])

    def test_seasonal_design_uses_target_month(self):
        x = seasonal_design(np.ones((2, 16)), np.array([11, 0]))
        self.assertEqual(x.shape, (2, 51))
        self.assertAlmostEqual(x[0, 1], 0)
        self.assertAlmostEqual(x[0, 2], 1)
        self.assertAlmostEqual(x[1, 1], .5)
        np.testing.assert_array_equal(x[:, 0], [1, 1])


if __name__ == "__main__":
    unittest.main()

import unittest

import numpy as np
import pandas as pd

from src.competition import fit_climatology, month_number, score, training_pairs


class TemporalProtocolTests(unittest.TestCase):
    def test_training_target_stays_before_cutoff(self):
        times = pd.date_range("2015-01-01", "2017-12-01", freq="MS")
        idx = training_pairs(times, "2017-01-01", start="2015-01-01")
        self.assertEqual(times[idx[-1]], pd.Timestamp("2016-11-01"))
        self.assertEqual(times[idx[-1] + 1], pd.Timestamp("2016-12-01"))

    def test_future_values_do_not_change_climatology(self):
        times = pd.date_range("2010-01-01", periods=48, freq="MS")
        values = np.arange(48, dtype=float)[:, None, None]
        before = fit_climatology(values, times, "2012-01-01")
        values[24:] = 1e9
        after = fit_climatology(values, times, "2012-01-01")
        np.testing.assert_array_equal(before, after)
        self.assertEqual(before[0, 0, 0], 6)

    def test_window_and_target_month(self):
        times = pd.date_range("2010-01-01", periods=36, freq="MS")
        values = np.arange(36, dtype=float)[:, None, None]
        climatology = fit_climatology(values, times, "2013-01-01", years=1)
        np.testing.assert_array_equal(climatology[:, 0, 0], np.arange(24, 36))
        self.assertEqual(month_number(["2017-01-01"])[0], 0)

    def test_rmse_pools_squared_errors(self):
        pred = np.zeros((24, 2, 2))
        observed = pred.copy()
        observed[12:] = 4
        metrics = score(pred, observed)
        self.assertAlmostEqual(metrics["rmse"], np.sqrt(8))
        self.assertEqual(metrics["year1_rmse"], 0)
        self.assertEqual(metrics["year2_rmse"], 4)

    def test_nonfinite_predictions_rejected(self):
        with self.assertRaises(ValueError):
            score(np.full((24, 1, 1), np.nan), np.zeros((24, 1, 1)))


if __name__ == "__main__":
    unittest.main()

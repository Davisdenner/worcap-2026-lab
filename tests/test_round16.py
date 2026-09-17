import unittest
import numpy as np
from src.round16 import seasonal_mean, apply, preceding, HISTORY


class CausalSpatialCalibrationTests(unittest.TestCase):
    def test_complete_blocks_only(self):
        self.assertEqual(preceding(HISTORY,2009),[2005,2007])
        self.assertNotIn(2021,preceding(HISTORY,2021))
        self.assertEqual(preceding(HISTORY,2023)[-1],2021)

    def test_seasonal_window_wraps_calendar_without_future_rows(self):
        values=np.arange(24,dtype=float).reshape(24,1,1)
        fields=seasonal_mean(values,'sazonal')
        indices=[0,1,2,10,11,12,13,14,22,23]
        self.assertAlmostEqual(fields[0,0,0],values[indices].mean())
        self.assertEqual(fields.shape,(12,1,1))

    def test_annual_intercept_and_clipping(self):
        values=np.ones((48,2,3))*-2
        correction=seasonal_mean(values,'anual')
        result=apply(np.ones((24,2,3)),correction,1.)
        np.testing.assert_array_equal(result,0)
        np.testing.assert_array_equal(apply(np.ones((24,2,3)),correction,0),1)

    def test_incomplete_year_rejected(self):
        with self.assertRaises(ValueError): seasonal_mean(np.zeros((13,2,3)),'sazonal')


if __name__=='__main__': unittest.main()

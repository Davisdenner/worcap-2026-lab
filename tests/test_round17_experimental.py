import unittest
from src.round17_experimental import confirmation_passes,shift_passes,confirm


class ExperimentalS12Tests(unittest.TestCase):
    def test_requires_explicit_exception(self):
        with self.assertRaises(PermissionError): confirm(False)

    def test_confirmation_still_requires_gain_and_both_years(self):
        before=dict(rmse=2.,year1_rmse=2.,year2_rmse=2.)
        self.assertTrue(confirmation_passes(before,dict(rmse=1.997,year1_rmse=1.996,year2_rmse=1.998)))
        self.assertFalse(confirmation_passes(before,dict(rmse=1.999,year1_rmse=1.999,year2_rmse=1.999)))
        self.assertFalse(confirmation_passes(before,dict(rmse=1.99,year1_rmse=1.98,year2_rmse=2.001)))

    def test_shift_each_year_and_finiteness(self):
        self.assertTrue(shift_passes([.10,.15],.076))
        self.assertFalse(shift_passes([.10,.16],.076))
        self.assertFalse(shift_passes([.10,float('nan')],.076))


if __name__=='__main__': unittest.main()

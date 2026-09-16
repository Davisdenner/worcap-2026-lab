import unittest
import numpy as np
from src.round12 import apply_correction,rank,CONFIGS,DEV
from src.round10 import training_origins


class S10ResidualTests(unittest.TestCase):
    def test_residual_training_excludes_current_and_future_blocks(self):
        for cutoff in DEV+(2021,2023):
            years,idx=training_origins(cutoff)
            self.assertTrue(all(y+2<=cutoff for y in years))
            self.assertTrue(np.all(idx+1<(cutoff-1940)*12))
        self.assertEqual(training_origins(2009)[0],[2005,2007])

    def test_correction_is_additive_and_nonnegative(self):
        ref=np.array([1.,2.,3.]); delta=np.array([-8.,4.,0.])
        np.testing.assert_array_equal(apply_correction(ref,delta,.25),[0.,3.,3.])
        np.testing.assert_array_equal(ref,[1.,2.,3.])
        with self.assertRaises(ValueError): apply_correction(ref,delta,2)
        with self.assertRaises(ValueError): apply_correction(ref,delta[:1],.25)

    def test_rank_rejects_tiny_gains_even_if_all_periods_improve(self):
        records={y:[dict(model='s10',monthly_rmse=[2.]*24)]+[
            dict(model=name,monthly_rmse=[1.999]*24,correction_rms=.1) for name in CONFIGS] for y in DEV}
        self.assertIsNone(rank(records)['selected'])
        name=next(iter(CONFIGS))
        for rows in records.values(): rows[1]['monthly_rmse']=[1.98]*24
        result=rank(records)
        self.assertEqual(result['selected'],name)
        self.assertEqual(result['ranking'][0]['months_improved'],144)


if __name__=='__main__': unittest.main()

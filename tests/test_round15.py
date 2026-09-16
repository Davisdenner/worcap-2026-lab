import unittest
from unittest.mock import patch
import numpy as np
from src import round15 as r


class JointWeightTests(unittest.TestCase):
    def test_prior_and_extension_reconstruct_s10(self):
        rng=np.random.default_rng(15)
        p=rng.uniform(0,10,size=(4,24,301,261))
        base=np.tile([.5,.3,.2],(12,1))
        s06=r.r9.combine(p[:3],base)
        s09=.75*s06+.25*p[3]
        tropical=rng.uniform(0,10,size=(24,121,261))
        extended=r.r11.blend(s09,tropical,1)
        prior=np.column_stack([.5625*base,np.full(12,.1875),np.full(12,.25)])
        actual=r.combine(np.concatenate([p,extended[None]]),prior)
        np.testing.assert_allclose(actual,r.r11.blend(s09,tropical,.25),rtol=0,atol=1e-12)

    def test_symmetric_errors_keep_equal_prior(self):
        prior=np.full(5,.2)
        np.testing.assert_allclose(r.solve_weights(np.eye(5),prior,.3),prior,atol=1e-10)

    def test_constraints_and_regularization(self):
        prior=np.full(5,.2); cov=np.diag([.1,1,2,3,4])
        weak=r.solve_weights(cov,prior,.1); strong=r.solve_weights(cov,prior,100)
        self.assertAlmostEqual(weak.sum(),1)
        self.assertTrue((weak>=0).all())
        self.assertLessEqual(np.max(abs(weak-prior)),.100000001)
        self.assertLess(np.linalg.norm(strong-prior),np.linalg.norm(weak-prior))

    def test_fit_never_reads_current_or_future_covariance(self):
        calls=[]
        def fake_cov(year):
            self.assertLess(year+1,2009); calls.append(year)
            return np.tile(np.eye(5),(12,1,1))
        with patch.object(r,'covariance',side_effect=fake_cov),patch.object(r,'prior_weights',return_value=(np.full((12,5),.2),[])),patch.object(r,'save_json'):
            r.fitted_weights(2009,999)
        self.assertEqual(calls,[2005,2007])
        self.assertEqual(r.calibration_blocks(2021),[2005,2007,2009,2011,2013,2015,2017,2019])
        self.assertIn(2021,r.calibration_blocks(2023))

    def test_small_gain_rejected(self):
        records={y:[dict(model='s10',monthly_rmse=[2.]*24)]+[
            dict(model=name,monthly_rmse=[1.999]*24,correction_rms=.1) for name in r.CONFIGS] for y in r.DEV}
        self.assertIsNone(r.rank(records)['selected'])


if __name__=='__main__': unittest.main()

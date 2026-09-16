import unittest
import numpy as np
from scipy.spatial.distance import cdist
from src.round13 import fit_kernel,predict_kernel,rank,DEV,CONFIGS


class TropicalKernelTests(unittest.TestCase):
    def test_matches_independent_augmented_system(self):
        rng=np.random.default_rng(13); z=rng.normal(size=(35,5)); y=rng.normal(size=(35,9))
        query=rng.normal(size=(7,5)); model=fit_kernel(z,y,.5,.3)
        k=np.exp(-cdist(z,z,'sqeuclidean')/model['bandwidth'])
        augmented=np.block([[k+.3*np.eye(35),np.ones((35,1))],[np.ones((1,35)),np.zeros((1,1))]])
        coef=np.linalg.solve(augmented,np.vstack([y,np.zeros((1,9))]))
        expected=np.column_stack([np.exp(-cdist(query,z,'sqeuclidean')/model['bandwidth']),np.ones(7)])@coef
        np.testing.assert_allclose(predict_kernel(model,query,y),expected,rtol=1e-10,atol=1e-10)

    def test_intercept_is_not_penalized_and_batch_does_not_fit(self):
        rng=np.random.default_rng(14); z=rng.normal(size=(40,4)); y=np.full((40,3),7.)
        model=fit_kernel(z,y,2,3); query=rng.normal(size=(2,4))
        a=predict_kernel(model,query,y)
        np.testing.assert_allclose(a,7.,atol=1e-10)
        b=predict_kernel(model,np.vstack([query,np.full((1,4),900.)]),y)[:2]
        np.testing.assert_allclose(a,b,atol=1e-10)

    def test_degenerate_distances_rejected(self):
        with self.assertRaises(ValueError): fit_kernel(np.ones((5,3)),np.ones((5,2)),1,.3)

    def test_gate_keeps_only_consistent_large_gain(self):
        records={y:[dict(model='s10',monthly_rmse=[2.]*24)]+[
            dict(model=name,monthly_rmse=[1.999]*24,correction_rms=.1) for name in CONFIGS] for y in DEV}
        self.assertIsNone(rank(records)['selected'])
        for rows in records.values(): rows[1]['monthly_rmse']=[1.98]*24
        self.assertEqual(rank(records)['selected'],next(iter(CONFIGS)))


if __name__=='__main__': unittest.main()

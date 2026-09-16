import unittest
import numpy as np

from src.round10 import training_origins,weather_design,fit_residual,predict_residual


class ResidualPLSTests(unittest.TestCase):
    def test_residual_targets_strictly_before_forecast(self):
        for cutoff in (2009,2011,2013,2015,2017,2019,2021,2023):
            years,origins=training_origins(cutoff)
            self.assertTrue(all(y+2<=cutoff for y in years))
            self.assertLess(origins.max()+1,(cutoff-1940)*12)
            self.assertEqual(len(origins),24*len(years))
        self.assertEqual(training_origins(2009)[0],[2005,2007])
        self.assertNotIn(2021,training_origins(2021)[0])
        self.assertIn(2021,training_origins(2023)[0])

    def test_causal_weather_transform(self):
        class Identity:
            def transform(self,x):
                return x
        raw=np.arange(60,dtype=float).reshape(20,3)
        model=dict(pca=Identity(),means=np.zeros((12,3)),scale=np.ones(3),pc_scale=np.ones(3))
        expected=weather_design(raw,model,np.array([6,7]))
        altered=raw.copy(); altered[8:]=-999
        np.testing.assert_array_equal(expected,weather_design(altered,model,np.array([6,7])))
        with self.assertRaises(ValueError):
            weather_design(raw,model,np.array([1]))

    def test_prediction_batch_does_not_fit_statistics(self):
        rng=np.random.default_rng(8)
        x=rng.normal(size=(48,12)); y=x@rng.normal(size=(12,20))+.1*rng.normal(size=(48,20))
        model=fit_residual(x,y,2)
        one=rng.normal(size=(1,12))
        a=predict_residual(model,one)
        b=predict_residual(model,np.concatenate([one,np.full((3,12),9999.)]))[:1]
        np.testing.assert_allclose(a,b,rtol=1e-10,atol=1e-10)
        self.assertEqual(a.shape,(1,20))
        self.assertTrue(np.isfinite(a).all())

    def test_no_earlier_residuals_rejected(self):
        with self.assertRaises(ValueError):
            training_origins(2005)


if __name__=='__main__':
    unittest.main()

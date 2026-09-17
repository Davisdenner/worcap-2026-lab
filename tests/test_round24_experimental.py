"""Limites de autorização e alinhamento dos atributos futuros da S13."""
import unittest
import numpy as np
from src import round24 as research
from src import round24_experimental as exp


class ExperimentalTransportTest(unittest.TestCase):
    def test_requires_explicit_authorization(self):
        with self.assertRaises(PermissionError): exp.authorize(False)

    def test_confirmation_waiver_is_explicit_and_preserves_failure(self):
        chosen,auth=exp.authorize(True)
        check=exp.r.old.read(exp.OUT/'confirmation.json')
        self.assertFalse(check['passed'])
        with self.assertRaises(PermissionError):
            exp.confirmation_waiver(False,check,auth)
        waiver=exp.confirmation_waiver(True,check,auth)
        self.assertIn('confirmation_2021_2022',waiver['waived_gates'])
        self.assertFalse(exp.r.old.read(exp.OUT/'confirmation.json')['passed'])

    def test_sample_is_available(self):
        self.assertTrue((research.old.RAW/'sample_submission.csv').exists())

    def test_weather_boundary_matches_official_train(self):
        fields=exp.test_weather()
        self.assertEqual(len(fields),3)
        self.assertTrue(all(field.shape==(24,301,261) for field in fields))
        for original,test in zip(research.fields(),fields):
            np.testing.assert_array_equal(original[-1],test[0])

    def test_same_historical_features_at_boundary(self):
        cells=np.array([0,100,10000,78560])
        np.testing.assert_array_equal(exp.future_extra(995,cells),research.extra(995,cells))

    def test_future_features_only_test_weather(self):
        cells=np.array([0,10000,78560])
        for origin in (996,1018):
            x=exp.future_extra(origin,cells)
            self.assertEqual(x.shape,(3,6))
            self.assertTrue(np.isfinite(x).all())
        with self.assertRaises(ValueError): exp.future_flux(1019)


if __name__=='__main__': unittest.main()

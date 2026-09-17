"""Invariantes da transição espacial e da disciplina temporal da rodada 21."""
import unittest
import numpy as np
from src import round21


class RegionalExpertsTest(unittest.TestCase):
    def test_weights_partition_unity(self):
        latitude = np.arange(-60, 15.01, .25)
        value = round21.weights(latitude)
        self.assertEqual(value.shape, (301,3))
        np.testing.assert_allclose(value.sum(axis=1), 1)
        self.assertTrue(np.all(value >= 0))
        np.testing.assert_array_equal(value[0], [1,0,0])
        np.testing.assert_array_equal(value[-1], [0,0,1])

    def test_taper_boundaries(self):
        v = round21.weights(np.array([-17.5,-15,-12.5,-2.5,0,2.5]))
        np.testing.assert_allclose(v[0],[1,0,0])
        np.testing.assert_allclose(v[1],[.5,.5,0])
        np.testing.assert_allclose(v[2],[0,1,0])
        np.testing.assert_allclose(v[3],[0,1,0])
        np.testing.assert_allclose(v[4],[0,.5,.5])
        np.testing.assert_allclose(v[5],[0,0,1])

    def test_training_halo_covers_inference(self):
        lat = np.arange(-60,15.01,.25)
        weight = round21.weights(lat)
        for index,name in enumerate(round21.REGIONS):
            active = weight[:,index]>0
            self.assertTrue(np.all(round21.training_mask(lat[active],name)))

    def test_invalid_region(self):
        with self.assertRaises(ValueError):
            round21.training_mask(np.array([0]),'invalida')

    def test_four_preregistered_candidates(self):
        self.assertEqual(len(round21.CONFIGS),4)
        self.assertEqual(set(round21.CONFIGS.values()),
                         {(7,.25),(7,.5),(15,.25),(15,.5)})


if __name__ == '__main__': unittest.main()

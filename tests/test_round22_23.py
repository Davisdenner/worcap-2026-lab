"""Controles de amostragem, cortes e reconstrução espacial."""
import unittest
import numpy as np
from scipy.ndimage import uniform_filter
from src import round22_23 as r


class BaseTrainingTest(unittest.TestCase):
    def test_starts_preregistered(self):
        self.assertEqual(r.STARTS, {'start1940':'1940-03-01',
                                    'start1960':'1960-01-01',
                                    'start1981':'1981-01-01'})

    def test_common_month_has_identical_cells(self):
        a=r.cells_for(500); b=r.cells_for(500)
        np.testing.assert_array_equal(a,b)
        self.assertEqual(len(np.unique(a)),r.N)

    def test_components_reconstruct_unsmoothed_target(self):
        rng=np.random.default_rng(5)
        rain=rng.random((301,261)).astype(np.float32)
        climo=rng.random((301,261)).astype(np.float32)
        smooth=uniform_filter(rain,size=9,mode='nearest')
        smooth_climo=uniform_filter(climo,size=9,mode='nearest')
        broad=smooth-smooth_climo; detail=rain-smooth
        np.testing.assert_allclose(smooth_climo+broad+detail,rain,rtol=0,atol=3e-7)

    def test_tree_and_mixtures_fixed(self):
        self.assertEqual(r.TREE['max_iter'],150)
        self.assertEqual(r.FRACTIONS,(.1,.25))
        self.assertEqual(r.N,512)


if __name__=='__main__': unittest.main()

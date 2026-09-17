"""Invariantes físicos/temporais da ablação de transporte de umidade."""
import unittest
from unittest.mock import patch
import numpy as np
from src import round24 as r


class MoistureTransportTest(unittest.TestCase):
    def tearDown(self):
        r.flux.cache_clear()
        r.fields.cache_clear()

    def test_constant_flux_has_zero_convergence(self):
        q=np.ones((3,301,261),np.float32)*.01
        u=np.ones_like(q)*5; v=np.ones_like(q)*2
        with patch.object(r,'fields',return_value=(q,u,v)):
            got=r.flux(2)
        np.testing.assert_allclose(got[2],0,rtol=0,atol=1e-5)
        np.testing.assert_allclose(got[3],0,rtol=0,atol=1e-8)

    def test_upwind_looks_against_wind(self):
        q=np.broadcast_to(np.arange(261,dtype=np.float32)[None,None,:],(3,301,261)).copy()
        u=np.ones_like(q); v=np.zeros_like(q)
        with patch.object(r,'fields',return_value=(q,u,v)):
            got=r.flux(2)
        self.assertEqual(got[3].reshape(301,261)[150,100],-8)
        self.assertEqual(got[3].reshape(301,261)[150,0],0)
        self.assertLess(got[2].reshape(301,261)[150,100],0)

    def test_north_taper(self):
        w=r.north_mask()
        self.assertEqual(w.shape,(301,261))
        np.testing.assert_array_equal(w[220],0)  # −5°
        np.testing.assert_array_equal(w[240],1)  # 0°
        np.testing.assert_array_equal(w[230],.5)

    def test_fixed_candidates(self):
        self.assertEqual(len(r.CONFIGS),8)
        self.assertEqual(set(r.KINDS.values()),{2,3,6})
        self.assertNotIn('produtos_global_b0.25',r.CONFIGS)

    def test_no_future_or_missing_weather(self):
        with self.assertRaises(ValueError): r.flux(-1)
        with self.assertRaises(ValueError): r.flux(996)


if __name__=='__main__': unittest.main()

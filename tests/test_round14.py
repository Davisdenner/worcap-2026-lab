import unittest
import numpy as np
from src.round14 import spherical_convergence,moisture_fields,fit_physics,rank,CONFIGS,DEV,RADIUS
from src.round10 import weather_design


class MoisturePhysicsTests(unittest.TestCase):
    def test_spherical_zonal_linear_flux(self):
        lat=np.arange(-20,16,1.); lon=np.arange(-90,-24,1.)
        east=np.broadcast_to(np.deg2rad(lon)[None,None,:],(2,len(lat),len(lon))).copy()
        actual=spherical_convergence(east,np.zeros_like(east),lat,lon)
        expected=np.broadcast_to(-1/(RADIUS*np.cos(np.deg2rad(lat))[None,:,None]),east.shape)
        np.testing.assert_allclose(actual,expected,rtol=1e-10,atol=1e-15)

    def test_spherical_meridional_flux_metric_and_sign(self):
        lat=np.arange(-20,15.01,.25); lon=np.arange(-90,-84.99,.25)
        north=np.ones((1,len(lat),len(lon)))
        actual=spherical_convergence(np.zeros_like(north),north,lat,lon)
        expected=np.broadcast_to(np.tan(np.deg2rad(lat))[None,:,None]/RADIUS,north.shape)
        np.testing.assert_allclose(actual[:,1:-1],expected[:,1:-1],rtol=1e-5,atol=1e-15)

    def test_mask_halo_and_no_temporal_mixing(self):
        lat=np.arange(-20,1.); lon=np.arange(-90,-69.)
        q=np.ones((2,21,21))*.01; u=np.ones_like(q)*2; v=np.zeros_like(q); ps=np.ones_like(q)*1e5
        ps[:,10,10]=8e4
        fields,mask=moisture_fields(q,u,v,ps,lat,lon)
        self.assertFalse(mask[0,7:14,7:14].any())
        np.testing.assert_array_equal(fields[:,:,7:14,7:14],0)
        self.assertAlmostEqual(fields[0,0,3,3],.02)
        u[1]=999
        np.testing.assert_array_equal(fields[:1],moisture_fields(q,u,v,ps,lat,lon)[0][:1])

    def test_physics_preprocessing_fits_only_training(self):
        rng=np.random.default_rng(18); raw=rng.normal(size=(110,40)); idx=np.arange(12,84)
        first=fit_physics(raw,idx,16); altered=raw.copy(); altered[84:]=900
        second=fit_physics(altered,idx,16)
        np.testing.assert_array_equal(first['means'],second['means'])
        np.testing.assert_allclose(first['pca'].components_,second['pca'].components_,atol=1e-12)
        np.testing.assert_allclose(weather_design(raw,first,np.array([70,71])),weather_design(altered,second,np.array([70,71])),atol=1e-12)

    def test_four_candidates_and_frozen_gain_gate(self):
        self.assertEqual(len(CONFIGS),4)
        records={y:[dict(model='s10',monthly_rmse=[2.]*24)]+[
            dict(model=name,monthly_rmse=[1.999]*24,correction_rms=.1) for name in CONFIGS] for y in DEV}
        self.assertIsNone(rank(records)['selected'])


if __name__=='__main__': unittest.main()

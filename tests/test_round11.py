import unittest
import numpy as np
from src.round11 import fine_fields,blend,fit_pls,anomaly_prediction,CONFIGS,CONTROL


class TropicalTests(unittest.TestCase):
    def test_spatial_filter_does_not_mix_time(self):
        x=np.zeros((3,301,261),np.float32); x[0]=2; x[1]=9; x[2]=-4
        y=fine_fields(x)
        self.assertEqual(y.shape,(3,2376))
        np.testing.assert_array_equal(y,np.broadcast_to(np.array([2,9,-4])[:,None],y.shape))
        changed=x.copy(); changed[2]=999
        np.testing.assert_array_equal(y[:2],fine_fields(changed)[:2])

    def test_blend_preserves_south_and_tapers(self):
        ref=np.ones((24,301,261)); new=np.full((24,121,261),5.)
        pred=blend(ref,new,.25)
        np.testing.assert_array_equal(pred[:,:181],ref[:,:181])
        self.assertEqual(pred[0,190,0],1.5)
        self.assertEqual(pred[0,200,0],2.)
        np.testing.assert_array_equal(pred[:,200:],np.full((24,101,261),2.))

    def test_predict_does_not_fit_to_validation_batch(self):
        rng=np.random.default_rng(11); x=rng.normal(size=(64,40)); y=rng.normal(size=(64,40))
        model=fit_pls(x,y,16); query=rng.normal(size=(1,40))
        a=anomaly_prediction(model,query)
        b=anomaly_prediction(model,np.concatenate([query,np.full((2,40),900.)]))[:1]
        np.testing.assert_allclose(a,b,atol=1e-10,rtol=1e-10)

    def test_control_not_eligible(self):
        self.assertEqual(len(CONFIGS),4)
        self.assertNotIn(CONTROL,CONFIGS)


if __name__=='__main__': unittest.main()

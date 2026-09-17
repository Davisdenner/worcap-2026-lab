import unittest
import numpy as np
from src.round18 import long_memory,replace_tropical


class LongMemoryTests(unittest.TestCase):
    def test_future_observations_do_not_change_features(self):
        z=np.arange(80,dtype=float).reshape(40,2)
        origins=np.array([11,15,20])
        expected=long_memory(z,origins,12)
        z[21:]=1e9
        np.testing.assert_array_equal(long_memory(z,origins,12),expected)
        np.testing.assert_array_equal(expected[0,4:],np.arange(24).reshape(12,2).mean(axis=0))

    def test_insufficient_history_rejected(self):
        with self.assertRaises(ValueError): long_memory(np.zeros((24,2)),np.array([10]),12)

    def test_replacement_preserves_south_and_old_component_identity(self):
        ref=np.full((24,301,261),2.)
        original=np.ones((24,121,261)); weights=np.full((12,5),.2)
        np.testing.assert_array_equal(replace_tropical(ref,original,original,weights,1),ref)
        changed=replace_tropical(ref,original,original+1,weights,.5)
        np.testing.assert_array_equal(changed[:,:181],ref[:,:181])
        np.testing.assert_allclose(changed[:,200:],2.1)


if __name__=='__main__': unittest.main()

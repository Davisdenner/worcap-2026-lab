import unittest
from unittest.mock import patch
import numpy as np
from src import round20 as r


class IdentityPCA:
    def transform(self,x): return x


class DirectGlobalTests(unittest.TestCase):
    def test_context_uses_current_and_only_previous_months(self):
        raw=np.repeat(np.arange(12,dtype=np.float32)[:,None],16,axis=1)
        model=dict(pca=IdentityPCA(),means=np.zeros((12,16)),scale=np.ones(16),pc_scale=np.ones(16))
        result=r.global_features(raw,model,np.array([2,5]))
        self.assertEqual(result.shape,(2,32))
        np.testing.assert_array_equal(result[0,:16],2)
        np.testing.assert_array_equal(result[0,16:],1)
        np.testing.assert_array_equal(result[1,:16],5)
        np.testing.assert_array_equal(result[1,16:],4)
        changed=raw.copy(); changed[6:]=99999
        np.testing.assert_array_equal(result,r.global_features(changed,model,np.array([2,5])))

    def test_unavailable_history_is_rejected(self):
        with self.assertRaises(ValueError): r.global_features(np.zeros((12,16)),{},np.array([1]))

    def test_sampling_is_nested_unique_and_reproducible(self):
        a=r.nested_cells([492,493]); b=r.nested_cells([492,493,494])
        for first,second in zip(a,b):
            self.assertEqual(len(np.unique(first)),1536)
            np.testing.assert_array_equal(first[:768],second[:768])
            self.assertTrue(np.isin(first[:768],first).all())

    def test_controlled_ablation_parameters(self):
        self.assertEqual(r.MODELS['local15'][1:],r.MODELS['global15'][1:])
        self.assertEqual(r.MODELS['global15'][2:],r.MODELS['global31'][2:])
        small,dense=r.MODELS['global31'],r.MODELS['global31_dense']
        self.assertEqual(small[:2],dense[:2])
        np.testing.assert_array_equal(np.array(small[2:])*2,np.array(dense[2:]))
        self.assertEqual(len(r.CONFIGS),8)
        self.assertFalse(r.TREE['early_stopping'])

    def test_confirmation_requires_approved_selection(self):
        with patch.object(r.old,'read',return_value={'selected':None}):
            with self.assertRaises(ValueError): r.selected()

    def test_reference_combination_is_convex(self):
        reference=np.array([0.,4.,10.]); direct=np.array([3.,0.,8.])
        for fraction in r.FRACTIONS:
            result=reference+fraction*(direct-reference)
            self.assertTrue(np.all(result>=0))
            np.testing.assert_allclose(result,(1-fraction)*reference+fraction*direct)


if __name__=='__main__': unittest.main()

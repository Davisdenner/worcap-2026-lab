import unittest
from unittest.mock import patch
import numpy as np
from src import round17 as r


class ConditionalCorrectionTests(unittest.TestCase):
    def test_feature_origin_and_no_target_input(self):
        n=78561
        reference=np.full((24,n),3.)
        pieces=np.stack([np.full((24,n),v) for v in (1.,2.,3.,4.,5.)])
        climo=np.full((12,n),2.)
        # Uma coluna por ponto não é necessária para os demais campos fictícios.
        weather=[np.broadcast_to(np.arange(996)[:,None],(996,n)) for _ in range(9)]
        with patch.object(r,'data',return_value=(reference,pieces,climo,weather,None)):
            x=r.matrix(2009,0,np.array([0,261,78560]))
            self.assertEqual(x.shape,(3,23))
            self.assertTrue(np.all(x[:,14:]==827))  # dezembro/2008
            np.testing.assert_array_equal(x[:,6:11],np.tile([-2,-1,0,1,2],(3,1)))
            np.testing.assert_array_equal(x[:,13],1)

    def test_unavailable_month_rejected(self):
        with self.assertRaises(ValueError): r.matrix(2009,24,np.array([0]))

    def test_test_targets_cannot_be_used_for_samples(self):
        with self.assertRaises(ValueError): r.samples(2023)


if __name__=='__main__': unittest.main()

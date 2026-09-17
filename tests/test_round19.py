import unittest
from unittest.mock import patch
import numpy as np
from src import round19 as r
from src.round19_history import early_prior,feature_rows
from src import round17 as old


class ExpandedHistoryTests(unittest.TestCase):
    def test_only_earlier_complete_blocks(self):
        self.assertEqual(r.preceding(r.HISTORY,2009),[1997,1999,2001,2003,2005,2007])
        with self.assertRaises(ValueError): r.weights([2021],2021,True)
        with self.assertRaises(ValueError): r.samples(2023)

    def test_decay_normalized_and_eight_year_halflife(self):
        w=r.weights([1997,2005],2009,True).reshape(48,2048)[:,0]
        self.assertAlmostEqual(w.mean(),1.)
        np.testing.assert_allclose(w[24:]/w[:24],2.)
        self.assertIsNone(r.weights([1997],2009,False))

    def test_early_prior_never_fits_future_weights(self):
        p=early_prior()
        self.assertAlmostEqual(p.sum(),1.)
        np.testing.assert_array_equal(p,[.28125,.140625,.140625,.1875,.25])

    def test_feature_builder_exactly_matches_frozen_s12(self):
        rng=np.random.default_rng(12); n=78561
        pred=rng.normal(size=(24,n)); pieces=rng.normal(size=(5,24,n))
        climo=rng.normal(size=(12,n))
        fields=[np.broadcast_to(np.arange(996)[:,None],(996,n)) for _ in range(9)]
        cells=np.array([0,100,78560])
        with patch.object(old,'data',return_value=(pred,pieces,climo,fields,None)):
            for m in (0,11,12,23):
                original=old.matrix(2009,m,cells)
                reproduced=feature_rows(pred,pieces,climo,fields,m,cells,old.target_origins(2009)[m])
                np.testing.assert_array_equal(original,reproduced)

    def test_no_selected_candidate_blocks_confirmation(self):
        with patch.object(old,'read',return_value={'selected':None}):
            with self.assertRaises(ValueError): r.selected()


if __name__=='__main__': unittest.main()

import unittest
from unittest.mock import patch

import numpy as np

from src.round9 import preceding, forward_weights, residual_features, passes_gate, PRIOR


class OfficialForwardTests(unittest.TestCase):
    def test_complete_blocks_only(self):
        self.assertEqual(preceding((2005,2007,2009,2011),2009),[2005,2007])
        self.assertEqual(preceding((2013,2015,2017,2019),2016),[2013])
        self.assertEqual(preceding((2013,2015,2017,2019),2021),[2013,2015,2017,2019])

    def test_small_or_unstable_improvement_does_not_pass(self):
        self.assertTrue(passes_gate(1.79,1.8,1.84,1.85,5,9,80,144,.004))
        self.assertFalse(passes_gate(1.799,1.8,1.84,1.85,6,12,144,144,0))
        self.assertFalse(passes_gate(1.79,1.8,1.84,1.85,4,9,80,144,.004))
        self.assertFalse(passes_gate(1.79,1.8,1.84,1.85,5,9,79,144,.004))
        self.assertFalse(passes_gate(1.79,1.8,1.84,1.85,5,9,80,144,.006))
        self.assertFalse(passes_gate(1.79,1.8,1.86,1.85,5,9,80,144,.004))

    def test_early_weights_do_not_access_future_calibration(self):
        with patch('src.round9.np.load',side_effect=AssertionError('must not read future labels')):
            weights,years = forward_weights(2013)
        self.assertEqual(years,[])
        np.testing.assert_array_equal(weights,np.tile(PRIOR,(12,1)))

    def test_official_residual_features_history_and_future_invariance(self):
        class FakeFeatures:
            lat = np.array([-60,-30,-10,0,10,15])
            means = np.zeros((12,6,9),dtype=np.float32)
            weather = np.broadcast_to(np.arange(20,dtype=np.float32)[:,None],(20,6)).copy()

            def row(self,j,o):
                return self.weather[o]+j

            def matrix(self,o,cells,context=False):
                return np.zeros((len(cells),55),dtype=np.float32)

        f = FakeFeatures()
        pieces = np.zeros((3,24,2,3),dtype=np.float32)
        pieces[1] = 2
        pieces[2] = 4
        pred = np.ones((24,2,3),dtype=np.float32)
        cells = np.array([0,2,5])
        expected = residual_features(f,8,cells,pieces,pred,0)
        self.assertEqual(expected.shape,(3,98))
        np.testing.assert_array_equal(expected[:,55],np.full(3,5.5))
        np.testing.assert_array_equal(expected[:,91:94],np.tile([0,2,4],(3,1)))
        np.testing.assert_array_equal(expected[:,94],np.ones(3))
        np.testing.assert_array_equal(expected[:,95:],np.tile([-1,1,3],(3,1)))
        f.weather[9:] = -999
        actual = residual_features(f,8,cells,pieces,pred,0)
        np.testing.assert_array_equal(expected,actual)

    def test_no_external_imports_or_prediction_paths(self):
        from pathlib import Path
        import src.round9 as module
        source = Path(module.__file__).read_text(encoding='utf-8')
        self.assertNotIn('from .round7',source)
        self.assertNotIn('from .round8',source)
        self.assertNotIn('submission_07_predictions',source)
        self.assertNotIn('submission_08_predictions',source)


if __name__ == '__main__':
    unittest.main()

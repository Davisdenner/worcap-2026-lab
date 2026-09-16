import unittest
import numpy as np
from src.round6 import history_features


class LocalMemoryTests(unittest.TestCase):
    def test_causal_window(self):
        seen=[]
        def row(i):
            seen.append(i)
            return np.array([i],dtype=float)
        current,average=history_features(row,np.zeros((12,1)),np.array([12]))
        np.testing.assert_array_equal(current,[[12]])
        np.testing.assert_array_equal(average,[[11]])
        self.assertEqual(seen,[12,11,10])

    def test_calendar_wrap(self):
        means=np.arange(12,dtype=float)[:,None]
        current,average=history_features(lambda i:np.array([i%12+5]),means,np.array([12,13]))
        np.testing.assert_array_equal(current,[[5],[5]])
        np.testing.assert_array_equal(average,[[5],[5]])

    def test_insufficient_history(self):
        with self.assertRaises(ValueError):
            history_features(lambda i:np.array([i]),np.zeros((12,1)),np.array([1]))

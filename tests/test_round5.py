import unittest
import numpy as np
from src.round5 import spatial


class SpatialTests(unittest.TestCase):
    def test_no_time_or_variable_mixing(self):
        x = np.zeros((3, 9, 38, 33), dtype=np.float32)
        x[1, 2] = 10
        y = spatial(x.reshape(3,-1), "broad16").reshape(x.shape)
        np.testing.assert_array_equal(x,y)

    def test_detailed_preserves_input(self):
        x = np.arange(30).reshape(3,10)
        np.testing.assert_array_equal(spatial(x,"detail32"),x)

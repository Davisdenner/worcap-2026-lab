import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from src.round7 import continental, ocean_history


class ContinentalTests(unittest.TestCase):
    def setUp(self):
        self.raw=np.random.default_rng(7).normal(size=(144,32)).astype(np.float32)
        self.f=SimpleNamespace(idx=np.arange(24,119),year=1950)
        self.origins=np.arange(119,143)

    def calculate(self,raw):
        with patch("src.round7.np.load",return_value=raw),patch("src.round7.target_origins",return_value=self.origins):
            return continental(self.f)

    def test_fit_not_affected_by_validation(self):
        x,v=self.calculate(self.raw)
        changed=self.raw.copy(); changed[119:]+=100
        xx,vv=self.calculate(changed)
        np.testing.assert_array_equal(x,xx)
        self.assertFalse(np.array_equal(v,vv))
        self.assertEqual(x.shape,(95,8))
        self.assertEqual(v.shape,(24,8))

    def test_no_later_month_in_first_prediction(self):
        _,v=self.calculate(self.raw)
        changed=self.raw.copy(); changed[120:]+=100
        _,vv=self.calculate(changed)
        np.testing.assert_array_equal(v[0],vv[0])

    def test_ocean_extra_lag(self):
        data=np.arange(60,dtype=float).reshape(20,3)
        before=ocean_history(data,np.array([10]))
        changed=data.copy(); changed[10:]=999
        np.testing.assert_array_equal(before,ocean_history(changed,np.array([10])))
        np.testing.assert_array_equal(before[0,:3],data[9])
        np.testing.assert_array_equal(before[0,3:],data[7:10].mean(axis=0))

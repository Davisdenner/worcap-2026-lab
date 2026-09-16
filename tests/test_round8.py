import unittest
import numpy as np
from src.round8 import parse_psl,monthly_center


class AtlanticTests(unittest.TestCase):
    def test_year_month_mapping_missing_and_footer(self):
        text="1940 1941\n1940 "+" ".join(map(str,np.arange(12)/10))+"\n1941 "+" ".join(["-99.99"]*12)+"\n-99.99\nTNA index\n"
        x=parse_psl(text,24)
        np.testing.assert_allclose(x[:12],np.arange(12)/10)
        self.assertTrue(np.isnan(x[12:]).all())

    def test_duplicate_year_rejected(self):
        row="1940 "+" ".join(["1"]*12)
        with self.assertRaises(ValueError):
            parse_psl("1940 1940\n"+row+"\n"+row,24)

    def test_future_does_not_change_training_anomalies(self):
        x=np.arange(48,dtype=float)[:,None]
        idx=np.arange(24)
        old,means=monthly_center(x,idx)
        changed=x.copy(); changed[24:]=999
        new,newmeans=monthly_center(changed,idx)
        np.testing.assert_array_equal(means,newmeans)
        np.testing.assert_array_equal(old[:24],new[:24])

    def test_months_after_october2024_excluded(self):
        text="2024 2024\n2024 "+" ".join(["1"]*12)
        x=parse_psl(text,1020)
        self.assertEqual(x[1017],1)
        self.assertTrue(np.isnan(x[1018:]).all())

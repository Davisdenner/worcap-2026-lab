import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from src import s11_delivery as r


class DeliveryTests(unittest.TestCase):
    def test_raw_output_collision_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'SETTINGS.json'
            p.write_text(json.dumps(dict(raw='raw',cache='raw',models='m',output='o',evidence='e')))
            with self.assertRaises(ValueError): r.settings(p)

    def test_prediction_history_boundary(self):
        f=object.__new__(r.PredictionFeatures)
        f.history=np.arange(27).reshape(9,3,1)
        f.test=[np.arange(24).reshape(24,1) for _ in range(9)]
        self.assertEqual(f.row(0,993)[0],0)
        self.assertEqual(f.row(0,995)[0],2)
        self.assertEqual(f.row(0,996)[0],1)
        self.assertEqual(f.row(0,1018)[0],23)
        for origin in (992,1019):
            with self.assertRaises(ValueError): f.row(0,origin)

    def test_archived_calibration_reproduces_weights(self):
        evidence=Path(__file__).resolve().parents[1]/'delivery/s11/evidence'
        if not evidence.exists(): self.skipTest('Delivery evidence not installed')
        w=r.read(evidence/'frozen_weights.json')
        cov=np.load(evidence/'calibration_covariances.npy').mean(axis=0)
        prior=np.asarray(w['prior'])
        from threadpoolctl import threadpool_limits
        with threadpool_limits(limits=1):
            actual=np.stack([r.solve_weights(cov[g],prior[g],1.) for g in range(12)])
        np.testing.assert_array_equal(actual,w['weights'])
        self.assertEqual(w['last_calibration_target'],'2022-12')
        self.assertTrue(np.all(actual>=0))
        self.assertLessEqual(np.max(abs(actual-prior)),.100000001)

    def test_gates_not_relaxed_by_s11_public_success(self):
        from src.round9 import passes_gate
        self.assertFalse(passes_gate(1.774622,1.775343,1.78805,1.78846,4,6,81,144,.0017))


if __name__=='__main__': unittest.main()

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from src.submission import export_csv


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        self.grid = xr.Dataset(coords={"time": pd.to_datetime(["2023-01-01", "2023-02-01"]),
                                       "lat": [-30., 0.], "lon": [-53., -52.75]})
        self.pred = xr.DataArray(np.arange(8.).reshape(2, 2, 2),
                                 dims=("time", "lat", "lon"), coords=self.grid.coords)

    def test_coordinate_order_is_preserved_with_transposed_input(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "pred.csv"
            pred = self.pred.isel(lat=slice(None, None, -1)).transpose("lon", "time", "lat")
            report = export_csv(pred, self.grid, path)
            result = pd.read_csv(path)
            self.assertEqual(report["rows"], 8)
            self.assertEqual(result.id.iloc[0], "2023_01_-30.00_-53.00")
            self.assertEqual(result.id.iloc[1], "2023_01_-30.00_-52.75")
            np.testing.assert_array_equal(result.tp_mm_day, np.arange(8.))

    def test_template_reorders_ids_and_values_together(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "original.csv"
            export_csv(self.pred, self.grid, path)
            template = pd.read_csv(path).iloc[::-1]
            template_path = Path(folder) / "sample.csv"
            template.to_csv(template_path, index=False)
            output = Path(folder) / "ordered.csv"
            export_csv(self.pred, self.grid, output, template_path)
            pd.testing.assert_frame_equal(pd.read_csv(output), template.reset_index(drop=True))

    def test_invalid_values_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            for value in [np.nan, np.inf, -1.]:
                pred = self.pred.copy()
                pred.values[0, 0, 0] = value
                with self.assertRaises(ValueError):
                    export_csv(pred, self.grid, Path(folder) / "bad.csv")


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch
from src import round15_experimental as r


class ExperimentalExportTests(unittest.TestCase):
    def test_no_implicit_authorization(self):
        with patch.object(r.r, 'locked') as locked:
            with self.assertRaises(PermissionError):
                r.run()
            locked.assert_not_called()

    def test_no_overwrite(self):
        with patch('pathlib.Path.exists', return_value=True), patch.object(r.r, 'locked') as locked:
            with self.assertRaises(FileExistsError):
                r.run(True)
            locked.assert_not_called()


if __name__ == '__main__':
    unittest.main()

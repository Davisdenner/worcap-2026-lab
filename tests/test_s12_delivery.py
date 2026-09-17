import unittest
from pathlib import Path
from src import s12_delivery as r


class S12DeliveryTests(unittest.TestCase):
    def test_archive_manifest_and_all_examples_are_integral(self):
        root,manifest=r.evidence({'evidence':r.ROOT/'delivery/s11/evidence'})
        self.assertEqual([b['block'] for b in manifest['blocks']],list(range(2005,2023,2)))
        self.assertEqual(len(manifest['features']),23)
        for block in manifest['blocks']:
            self.assertEqual(r.base.digest(root/block['file']),block['sha256'])
            self.assertLess(int(block['base_training_targets_end'][:4]),block['block'])

    def test_catalog_has_corrector_engine_without_promoting_history(self):
        catalog=r.base.read(r.ROOT/'configs/modelos.json')
        self.assertEqual(catalog['versoes']['s12']['motor'],'s12_delivery')
        self.assertEqual(catalog['criterio_minimo_relativo'],.003)
        original=r.base.read(r.ROOT/'submissions/submission_12.json')
        self.assertFalse(original['automatic_promotion_passed'])
        self.assertTrue(original['experimental'])


if __name__=='__main__': unittest.main()

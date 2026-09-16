import unittest
import tempfile
from pathlib import Path
from src import reproducao as r
from src.round9 import passes_gate


class ReproducaoTests(unittest.TestCase):
    def test_catalogo_concorda_com_manifesto(self):
        catalogo = r.motor.read(r.CATALOGO)
        manifesto = r.motor.read(r.ROOT / 'submissions/manifest.json')
        records = {Path(x['file']).stem: x for x in manifesto['submissions']}
        for nome, item in catalogo['versoes'].items():
            record = records['submission_' + nome[1:]]
            self.assertEqual(item['csv_sha256'], record['sha256'])
            self.assertEqual(item['public_rmse'], record['public_rmse'])
        self.assertEqual(r.resolver('melhor')[0], 's11')
        self.assertEqual(catalogo['controle_aprovado'], 's10')
        self.assertEqual(catalogo['criterio_minimo_relativo'], .003)

    def test_versao_desconhecida_nao_cai_na_s11(self):
        with self.assertRaises(ValueError):
            r.resolver('s12')

    def test_criterio_03_e_estabilidade_continuam_ativos(self):
        # Ganho de 0,299% não basta; 0,3% basta somente com todas as condições.
        args = dict(reference_rmse=2., second=1.9, reference_second=2.,
                    blocks=5, years=9, months=80, total_months=144, worst=.005)
        self.assertFalse(passes_gate(pooled=2.*(1-.00299), **args))
        self.assertTrue(passes_gate(pooled=2.*.997, **args))
        args['blocks'] = 4
        self.assertFalse(passes_gate(pooled=1.98, **args))

    def test_evidencias_preservadas(self):
        catalogo = r.motor.read(r.CATALOGO)
        for nome, esperado in catalogo['evidencias_sha256'].items():
            self.assertEqual(r.motor.digest(r.ROOT / 'delivery/s11/evidence' / nome), esperado)

    def test_csv_alterado_e_rejeitado(self):
        with tempfile.TemporaryDirectory() as pasta:
            output = Path(pasta)
            (output / 's10_reproduction.csv').write_text('id,tp_mm_day\nincorreto,0\n')
            with self.assertRaisesRegex(ValueError, 'CSV diferente do original'):
                r.verificar(dict(version='s10', output=output), r.resolver('s10')[1])


if __name__ == '__main__':
    unittest.main()

# Licenças e atribuição de terceiros

O código do projeto é separado das dependências. NumPy, SciPy, scikit-learn,
pandas, xarray, joblib, netCDF4 e dependências transitivas mantêm suas próprias
licenças. O construtor do pacote inclui metadados e arquivos de licença das
distribuições instaladas; consulte o inventário antes de redistribuir.

Os wheels offline são distribuições locais reempacotadas para Windows x64,
não downloads originais dos editores. As licenças e os metadados originais são
preservados dentro de cada wheel. A origem e os hashes estão em
[wheels/provenance.json](wheels/provenance.json). Não são incluídos runtime
Python nem biblioteca proprietária de GPU. Os wheels não são versionados no Git.

Dados oficiais não recebem a licença do código e não integram o ZIP. Seu uso
continua sujeito aos termos da competição e dos dados, incluindo a limitação
não comercial descrita nas regras fornecidas pelo participante.

A atribuição original é mantida sem tradução:

> Contains modified Copernicus Climate Change Service information 2026.
> Neither the European Commission nor ECMWF is responsible for any use that
> may be made of the Copernicus information or data it contains.

S10/S11 não incluem observações NOAA nem componentes derivados de S07/S08.
O repositório completo preserva experimentos anteriores para transparência;
essa preservação não os torna dependências da solução atual restrita a dados oficiais.

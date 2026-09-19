<#
.SYNOPSIS
Verifica a reproducao da S12 a partir de um clone vazio, como exige a
Secao 2.8 das regras da competicao.

.DESCRIPTION
A Secao 2.8 obriga o vencedor a entregar o codigo-fonte capaz de gerar a
submissao vencedora, com codigo de treino, de inferencia e descricao do
ambiente. As anotacoes do projeto registram esta pendencia: "reproducao
completa da S12 em clone vazio ainda nao integrada".

Este script NAO reescreve nada do pipeline. Ele clona o repositorio num
diretorio novo, monta um ambiente virtual limpo a partir do
requirements.txt, liga os dados oficiais brutos por juncao de diretorio, e
roda `src.reproducao` nas quatro etapas. Ao final compara o sha256 do CSV
gerado com o registrado em configs/modelos.json.

O diagnostico mais importante vem antes de tudo isso: o script lista quais
arquivos exigidos pela reproducao NAO vieram no clone. Se as evidencias
congeladas de delivery/ estiverem fora do controle de versao, a entrega da
Secao 2.8 estaria incompleta mesmo com o codigo correto -- e e melhor
descobrir isso agora.

.PARAMETER Destino
Diretorio onde o clone sera criado. Padrao: um diretorio novo em $env:TEMP.

.PARAMETER PularInstalacao
Reaproveita um .venv existente no destino, para reexecutar sem baixar
pacotes de novo.

.EXAMPLE
.\scripts\verificar_clone_limpo.ps1
.\scripts\verificar_clone_limpo.ps1 -Destino D:\teste_s12
#>
[CmdletBinding()]
param(
    [string]$Destino = (Join-Path $env:TEMP ("worcap_clone_" + (Get-Date -Format "yyyyMMdd_HHmmss"))),
    [switch]$PularInstalacao
)

$ErrorActionPreference = "Stop"
$Origem = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$repo = Join-Path $Destino "repo"
$relatorio = [ordered]@{
    origem = $Origem; destino = $repo; inicio = (Get-Date).ToString("o")
}

function Etapa($titulo) {
    Write-Host ""
    Write-Host "=== $titulo ===" -ForegroundColor Cyan
}

# ---------------------------------------------------------------- 1. clone
Etapa "1. Clonando apenas os arquivos versionados"
if (Test-Path $repo) { throw "Destino ja existe: $repo" }
New-Item -ItemType Directory -Path $Destino -Force | Out-Null
git clone --quiet $Origem $repo
if ($LASTEXITCODE -ne 0) { throw "git clone falhou" }
$commit = (git -C $repo rev-parse HEAD).Trim()
$relatorio.commit = $commit
Write-Host "commit: $commit"

# ------------------------------------------------- 2. o que NAO veio junto
Etapa "2. Arquivos exigidos pela reproducao que faltam no clone"
$exigidos = @(
    "configs/modelos.json",
    "configs/reproducao.json",
    "delivery/s11/requirements.txt",
    "src/reproducao.py",
    "src/s11_delivery.py",
    "src/s12_delivery.py",
    "delivery/s11/evidence/frozen_weights.json",
    "delivery/s11/evidence/calibration_covariances.npy",
    "delivery/s11/evidence/official_sources.json",
    "delivery/s12/evidence/manifest.json"
)
foreach ($ano in 2005, 2007, 2009, 2011, 2013, 2015, 2017, 2019, 2021) {
    $exigidos += "delivery/s12/evidence/${ano}_samples.npz"
}
$faltando = @()
foreach ($rel in $exigidos) {
    if (-not (Test-Path (Join-Path $repo $rel))) { $faltando += $rel }
}
$relatorio.faltando_no_clone = $faltando
if ($faltando.Count -eq 0) {
    Write-Host "nenhum -- o clone contem tudo que a reproducao exige" -ForegroundColor Green
} else {
    Write-Host "FALTAM $($faltando.Count) arquivo(s):" -ForegroundColor Yellow
    $faltando | ForEach-Object { Write-Host "  $_" }
    Write-Host ""
    Write-Host "Isso significa que um terceiro que receba so o repositorio NAO" -ForegroundColor Yellow
    Write-Host "consegue reproduzir a S12. Para a Secao 2.8, ou versione esses" -ForegroundColor Yellow
    Write-Host "arquivos, ou documente-os como artefatos entregues a parte." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Copiando do repositorio de origem para seguir o teste..." -ForegroundColor Yellow
    foreach ($rel in $faltando) {
        $de = Join-Path $Origem $rel
        $para = Join-Path $repo $rel
        if (-not (Test-Path $de)) { throw "Nem na origem existe: $rel" }
        New-Item -ItemType Directory -Path (Split-Path $para) -Force | Out-Null
        Copy-Item $de $para
    }
}

# ------------------------------------------------------ 3. dados oficiais
Etapa "3. Ligando os dados oficiais brutos"
$rawOrigem = Join-Path $Origem "data\raw"
if (-not (Test-Path $rawOrigem)) { throw "Nao encontrei $rawOrigem" }
New-Item -ItemType Directory -Path (Join-Path $repo "data") -Force | Out-Null
$rawDestino = Join-Path $repo "data\raw"
if (-not (Test-Path $rawDestino)) {
    New-Item -ItemType Junction -Path $rawDestino -Target $rawOrigem | Out-Null
}
$nc = (Get-ChildItem $rawDestino -Filter *.nc).Count
Write-Host "$nc arquivos NetCDF visiveis via juncao (dados brutos nao sao copiados)"
$relatorio.arquivos_netcdf = $nc

# ------------------------------------------------------------ 4. ambiente
Etapa "4. Ambiente virtual limpo"
$py = Join-Path $repo ".venv\Scripts\python.exe"
if (-not $PularInstalacao) {
    # `python` no PATH pode ser qualquer coisa -- nesta maquina e um Python 2.7
    # do windows-build-tools, que nem tem o modulo venv. O REPRODUCAO.md manda
    # usar `py -3.11`; usamos o mesmo lancador, com o interpretador atual como
    # ultimo recurso apenas se ele for 3.11.
    $criador = $null
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.11 -c "import sys" 2>$null
        if ($LASTEXITCODE -eq 0) { $criador = @("py", "-3.11") }
    }
    if (-not $criador) {
        throw ("Nao encontrei Python 3.11 via `py -3.11`. O REPRODUCAO.md fixa " +
               "3.11.1 como referencia; instale-o ou passe -PularInstalacao " +
               "apontando um .venv ja pronto.")
    }
    Write-Host ("criando .venv com: " + ($criador -join " "))
    & $criador[0] $criador[1] -m venv (Join-Path $repo ".venv")
    if ($LASTEXITCODE -ne 0) { throw "criacao do venv falhou" }
}
if (-not (Test-Path $py)) { throw "Nao existe interpretador em $py" }
if (-not $PularInstalacao) {
    & $py -m pip install --quiet --upgrade pip
    # Dependencias FIXADAS. O requirements.txt da raiz e exploratorio, sem
    # versoes, e nao serve para comparacao byte a byte (REPRODUCAO.md, secao 2).
    & $py -m pip install --quiet -r (Join-Path $repo "delivery\s11\requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "pip install falhou" }
    & $py -m pip check
    $relatorio.pip_check_ok = ($LASTEXITCODE -eq 0)
}
$relatorio.python = (& $py --version)
Write-Host $relatorio.python
if ($relatorio.python -notmatch "3\.11\.1") {
    Write-Host ("AVISO: a referencia verificada e 3.11.1; diferencas de patch, " +
                "plataforma ou BLAS podem mudar o hash.") -ForegroundColor Yellow
}

# -------------------------------------------------------------- 5. etapas
Etapa "5. Reproducao da S12"
$tempos = [ordered]@{}
foreach ($etapa in "listar", "preparar", "treinar", "prever") {
    Write-Host ""
    Write-Host "-- $etapa --" -ForegroundColor DarkCyan
    $t0 = Get-Date
    Push-Location $repo
    try {
        & $py -m src.reproducao $etapa --versao s12
        if ($LASTEXITCODE -ne 0) { throw "Etapa '$etapa' falhou com codigo $LASTEXITCODE" }
    } finally { Pop-Location }
    $tempos[$etapa] = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
    Write-Host "($($tempos[$etapa])s)"
}
$relatorio.segundos_por_etapa = $tempos

# ----------------------------------------------------------- 6. veredito
Etapa "6. Conferencia do hash contra configs/modelos.json"
$catalogo = Get-Content (Join-Path $repo "configs\modelos.json") -Raw | ConvertFrom-Json
$esperado = $catalogo.versoes.s12.csv_sha256
$csv = Join-Path $repo "data\processed\reproducao\saidas_verificadas\s12\s12_reproduction.csv"
if (-not (Test-Path $csv)) { throw "CSV nao gerado: $csv" }
$obtido = (Get-FileHash $csv -Algorithm SHA256).Hash.ToLower()
$relatorio.csv_sha256_esperado = $esperado
$relatorio.csv_sha256_obtido = $obtido
$relatorio.identico = ($obtido -eq $esperado)

Write-Host "esperado: $esperado"
Write-Host "obtido:   $obtido"
Write-Host ""
if ($relatorio.identico) {
    Write-Host "APROVADO: a S12 foi reproduzida byte a byte a partir de um clone vazio." -ForegroundColor Green
    if ($faltando.Count -gt 0) {
        Write-Host "RESSALVA: $($faltando.Count) arquivo(s) precisaram ser copiados fora do clone." -ForegroundColor Yellow
    }
} else {
    Write-Host "REPROVADO: o CSV difere do original." -ForegroundColor Red
}

$relatorio.fim = (Get-Date).ToString("o")
$saida = Join-Path $Origem "reports\competition\reproducao_clone_limpo.json"
New-Item -ItemType Directory -Path (Split-Path $saida) -Force | Out-Null
$relatorio | ConvertTo-Json -Depth 5 | Set-Content $saida -Encoding UTF8
Write-Host ""
Write-Host "Relatorio: $saida"
Write-Host "Clone de teste: $repo (apague quando quiser)"

# Publica o código-fonte do Editor de PDF em https://github.com/editorpdf/editor-pdf (exigência da licença AGPL
# do MuPDF e do Ghostscript). Copia só a lista de arquivos abaixo para %LOCALAPPDATA%\EditorPDF-codigo\repo:
# a chave do APK, os registros e os instaladores nunca vão. Cada versão ganha uma marcação (tag) com o número dela.
# Roda sozinho pelo web\publicar-versao.ps1; também pode rodar à mão.
$ErrorActionPreference = 'Stop'
$Codigo = Split-Path -Parent $MyInvocation.MyCommand.Path
$Raiz   = Split-Path $Codigo
$Repo   = Join-Path $env:LOCALAPPDATA 'EditorPDF-codigo\repo'
$gh = (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Depth 5 -Filter gh.exe | Select-Object -First 1).FullName
$env:Path = "$env:LOCALAPPDATA\MinGit\cmd;" + (Split-Path $gh) + ";$env:Path"

# o que vai para o repositório (caminhos relativos à pasta Adobe; pastas vão inteiras)
$lista = @(
    'LEIA-ME.md', 'CONTEXTO.md',
    'sistema\app.py', 'sistema\servidor.py', 'sistema\ferramentas.py', 'sistema\painel.py', 'sistema\painel.html',
    'sistema\editor-pdf.html', 'sistema\motor.js', 'sistema\editor-pdf.spec', 'sistema\instalador.iss', 'sistema\versao.txt',
    'sistema\icone.ico', 'sistema\icone.png', 'sistema\Abrir editor.bat', 'sistema\abrir-painel.vbs', 'sistema\ligar-servidor.vbs',
    'sistema\lib',
    'dados\tessdata',
    'android\build.gradle.kts', 'android\settings.gradle.kts', 'android\gradle.properties', 'android\gerar-apk.ps1',
    'android\app\build.gradle.kts', 'android\app\src',
    'web\gerar-web.ps1', 'web\publicar-web.ps1', 'web\publicar-versao.ps1', 'web\sw.js', 'web\privacidade.html', 'web\novidades.json',
    'loja\gerar-msix.ps1', 'loja\icones_loja.py', 'loja\identidade.json', 'loja\COMO-PUBLICAR.md', 'loja\capturas',
    'codigo\publicar-codigo.ps1'
)
# na raiz do repositório
$raizRepo = @{ 'README.md' = 'codigo\README.md'; 'LICENSE' = 'codigo\LICENSE'; 'TERCEIROS.md' = 'codigo\TERCEIROS.md'; '.gitignore' = 'codigo\.gitignore' }

if (-not (Test-Path (Join-Path $Repo '.git'))) {
    New-Item -ItemType Directory $Repo -Force | Out-Null
    $ErrorActionPreference = 'Continue'
    & $gh repo view editorpdf/editor-pdf --json name *> $null
    if ($LASTEXITCODE) {
        & $gh repo create editorpdf/editor-pdf --public --description 'Editor de PDF Fácil: editor de PDF gratuito para Windows, Android e navegador (AGPL-3.0)' --homepage 'https://editorpdf.github.io'
        if ($LASTEXITCODE) { throw "não consegui criar o repositório ($LASTEXITCODE)" }
    }
    $ErrorActionPreference = 'Stop'
    git -C $Repo init -q -b main
    git -C $Repo remote add origin https://github.com/editorpdf/editor-pdf.git
}
# mesma identidade do site (e-mail "noreply" do GitHub: não expõe o e-mail pessoal) e sem converter quebras de linha
git -C $Repo config user.name 'k2locserv-collab'
git -C $Repo config user.email '343685101+k2locserv-collab@users.noreply.github.com'
git -C $Repo config core.autocrlf false

# recopia tudo (mantém só a pasta .git), assim arquivos apagados no projeto somem do repositório também
Get-ChildItem -LiteralPath $Repo -Force | Where-Object Name -ne '.git' | ForEach-Object { Remove-Item -LiteralPath $_.FullName -Recurse -Force }
foreach ($rel in $lista) {
    $de = Join-Path $Raiz $rel
    if (-not (Test-Path -LiteralPath $de)) { throw "não achei $rel" }
    $para = Join-Path $Repo $rel
    New-Item -ItemType Directory (Split-Path $para) -Force | Out-Null
    Copy-Item -LiteralPath $de $para -Recurse -Force
}
foreach ($k in $raizRepo.Keys) { Copy-Item -LiteralPath (Join-Path $Raiz $raizRepo[$k]) (Join-Path $Repo $k) -Force }

# trava de segurança: nada de chave, senha ou registro
$proibido = Get-ChildItem -LiteralPath $Repo -Recurse -Force -File | Where-Object {
    $_.FullName -notlike "*\.git\*" -and ($_.Extension -in '.jks', '.keystore', '.pfx', '.p12', '.log', '.msix', '.apk', '.exe' -or $_.Name -in 'chave.properties', 'local.properties', 'config.json')
}
if ($proibido) { throw "arquivo que não pode ser publicado: $($proibido.FullName -join ', ')" }

$vWin = [IO.File]::ReadAllText((Join-Path $Raiz 'sistema\versao.txt')).Trim()
$vAnd = [regex]::Match([IO.File]::ReadAllText((Join-Path $Raiz 'android\app\build.gradle.kts')), 'versionName\s*=\s*"([^"]+)"').Groups[1].Value
$tag = "windows-$vWin-android-$vAnd"
Push-Location $Repo
try {
    $ErrorActionPreference = 'Continue'
    git add -A
    git diff --cached --quiet
    if ($LASTEXITCODE) { git commit -q -m "Código-fonte do Editor de PDF: Windows $vWin, Android $vAnd" }
    # a marcação aponta para o código da versão publicada (se a versão for republicada, a marcação acompanha)
    git tag -f $tag *> $null
    git push -q -u origin main
    if ($LASTEXITCODE) { throw "não consegui enviar o código ($LASTEXITCODE)" }
    git push -q -f origin "refs/tags/$tag"
    "Código publicado: https://github.com/editorpdf/editor-pdf/tree/$tag"
} finally { Pop-Location }

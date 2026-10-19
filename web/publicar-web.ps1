# Gera o site de novo e publica no GitHub Pages (https://editorpdf.github.io/).
# Precisa do login feito no GitHub CLI (gh auth login) e do Git portátil em %LOCALAPPDATA%\MinGit.
$ErrorActionPreference = 'Stop'
$Web = Split-Path -Parent $MyInvocation.MyCommand.Path
$gh = (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Depth 5 -Filter gh.exe | Select-Object -First 1).FullName
$env:Path = "$env:LOCALAPPDATA\MinGit\cmd;" + (Split-Path $gh) + ";$env:Path"
# computador novo: a cópia de trabalho do site (fora do OneDrive) ainda não existe -> baixa do GitHub
$Site = Join-Path $env:LOCALAPPDATA 'EditorPDF-web\site'
if (-not (Test-Path (Join-Path $Site '.git'))) {
    if (Test-Path $Site) { Remove-Item -LiteralPath $Site -Recurse -Force }
    New-Item -ItemType Directory (Split-Path $Site) -Force | Out-Null
    $ErrorActionPreference = 'Continue'
    & $gh repo clone editorpdf/editorpdf.github.io $Site
    if ($LASTEXITCODE) { throw "não consegui baixar o repositório do site ($LASTEXITCODE)" }
    git -C $Site config user.name 'k2locserv-collab'
    git -C $Site config user.email '343685101+k2locserv-collab@users.noreply.github.com'
    $ErrorActionPreference = 'Stop'
}
& (Join-Path $Web 'gerar-web.ps1')
Push-Location (Join-Path $env:LOCALAPPDATA 'EditorPDF-web\site')
try {
    $ErrorActionPreference = 'Continue'
    git add -A
    git commit -q -m ("Atualiza o Editor de PDF ({0})" -f (Get-Date -Format 'dd/MM/yyyy HH:mm'))
    git push -q
    "Publicado. Em 1 ou 2 minutos o site atualiza: https://editorpdf.github.io/"
} finally { Pop-Location }

# Gera o site de novo e publica no GitHub Pages (https://editorpdf.github.io/).
# Precisa do login feito no GitHub CLI (gh auth login) e do Git portátil em %LOCALAPPDATA%\MinGit.
$ErrorActionPreference = 'Stop'
$Web = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $Web 'gerar-web.ps1')
$gh = (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Depth 5 -Filter gh.exe | Select-Object -First 1).FullName
$env:Path = "$env:LOCALAPPDATA\MinGit\cmd;" + (Split-Path $gh) + ";$env:Path"
Push-Location (Join-Path $env:LOCALAPPDATA 'EditorPDF-web\site')
try {
    $ErrorActionPreference = 'Continue'
    git add -A
    git commit -q -m ("Atualiza o Editor de PDF ({0})" -f (Get-Date -Format 'dd/MM/yyyy HH:mm'))
    git push -q
    "Publicado. Em 1 ou 2 minutos o site atualiza: https://editorpdf.github.io/"
} finally { Pop-Location }

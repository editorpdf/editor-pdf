# Publica uma versão nova para quem já tem o app: envia o instalador do Windows e o APK para as "versões" (releases)
# do GitHub e atualiza o site (versao.json). Os apps instalados veem o aviso "Nova versão disponível" ao abrir.
# Antes: aumente o número em sistema\versao.txt (Windows) e/ou em android\app\build.gradle.kts (Android),
# gere o instalador e o APK, e escreva as novidades em web\novidades.json.
$ErrorActionPreference = 'Stop'
$Web = Split-Path -Parent $MyInvocation.MyCommand.Path
$Raiz = Split-Path $Web
$gh = (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Depth 5 -Filter gh.exe | Select-Object -First 1).FullName
$vWin = [IO.File]::ReadAllText((Join-Path $Raiz 'sistema\versao.txt')).Trim()
$vAnd = [regex]::Match([IO.File]::ReadAllText((Join-Path $Raiz 'android\app\build.gradle.kts')), 'versionName\s*=\s*"([^"]+)"').Groups[1].Value
$tag = "windows-$vWin-android-$vAnd"
# nomes sem espaço (o GitHub troca espaço por ponto)
$tmp = Join-Path $env:TEMP 'editorpdf-release'; New-Item -ItemType Directory $tmp -Force | Out-Null
Copy-Item (Join-Path $Raiz 'instalador\Instalar Editor de PDF.exe') (Join-Path $tmp 'Instalar-Editor-de-PDF.exe') -Force
Copy-Item (Join-Path $Raiz 'instalador\Editor de PDF.apk') (Join-Path $tmp 'Editor-de-PDF.apk') -Force
$ErrorActionPreference = 'Continue'
& $gh release view $tag --repo editorpdf/editorpdf.github.io *> $null
if ($LASTEXITCODE -eq 0) {
    & $gh release upload $tag (Join-Path $tmp 'Instalar-Editor-de-PDF.exe') (Join-Path $tmp 'Editor-de-PDF.apk') --clobber --repo editorpdf/editorpdf.github.io
} else {
    & $gh release create $tag (Join-Path $tmp 'Instalar-Editor-de-PDF.exe') (Join-Path $tmp 'Editor-de-PDF.apk') --repo editorpdf/editorpdf.github.io `
        --title "Editor de PDF — Windows $vWin, Android $vAnd" --notes "Instalador do Windows e APK do Android. Quem já tem o app recebe o aviso de atualização." --latest
}
if ($LASTEXITCODE) { throw "não consegui enviar os arquivos para o GitHub ($LASTEXITCODE)" }
$ErrorActionPreference = 'Stop'
& (Join-Path $Web 'publicar-web.ps1')
"Versão publicada: Windows $vWin, Android $vAnd"

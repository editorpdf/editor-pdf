# Gera o APK do Editor de PDF para Android (Adobe\instalador\Editor de PDF.apk).
# Usa o JDK, o Android SDK e o Gradle baixados em %LOCALAPPDATA%\AndroidBuild.
$ErrorActionPreference = 'Stop'
$Android = Split-Path -Parent $MyInvocation.MyCommand.Path
$Raiz    = Split-Path $Android
$Sistema = Join-Path $Raiz 'sistema'
$Build   = Join-Path $env:LOCALAPPDATA 'AndroidBuild'
$env:JAVA_HOME = (Get-ChildItem $Build -Directory -Filter 'jdk-*' | Select-Object -First 1).FullName
$env:ANDROID_HOME = Join-Path $Build 'sdk'
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
$Gradle = (Get-ChildItem $Build -Directory -Filter 'gradle-*' | Select-Object -First 1).FullName + '\bin\gradle.bat'
Set-Content (Join-Path $Android 'local.properties') ("sdk.dir=" + $env:ANDROID_HOME.Replace('\', '\\')) -Encoding ASCII

# 1) página, motor e bibliotecas dentro do app (assets/www)
$www = Join-Path $Build 'assets\www'
if (Test-Path $www) { Remove-Item -LiteralPath $www -Recurse -Force }
New-Item -ItemType Directory $www -Force | Out-Null
$html = [IO.File]::ReadAllText((Join-Path $Sistema 'editor-pdf.html'))
# versão do app (a mesma do build.gradle.kts): o editor compara com a do site para avisar de atualização
$versaoApk = [regex]::Match([IO.File]::ReadAllText((Join-Path $Android 'app\build.gradle.kts')), 'versionName\s*=\s*"([^"]+)"').Groups[1].Value
$html = $html.Replace('<head>', "<head>`n<script>window.APP_CELULAR=true;window.APP_VERSAO='$versaoApk'</script>")
$html = $html.Replace('<meta name="viewport" content="width=device-width, initial-scale=1">', '<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">')
[IO.File]::WriteAllText((Join-Path $www 'index.html'), $html, (New-Object Text.UTF8Encoding $false))
Copy-Item (Join-Path $Sistema 'motor.js') $www
Copy-Item (Join-Path $Sistema 'lib') $www -Recurse

# 2) chave de assinatura (criada uma vez; GUARDE a pasta android\chave: sem ela não dá para atualizar o app instalado)
$chave = Join-Path $Android 'chave'
if (-not (Test-Path (Join-Path $chave 'chave.properties'))) {
    New-Item -ItemType Directory $chave -Force | Out-Null
    $senha = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 24 | ForEach-Object { [char]$_ })
    $ErrorActionPreference = 'Continue'  # o keytool escreve o progresso na saída de erro
    & keytool -genkeypair -v -keystore (Join-Path $chave 'editorpdf.jks') -alias editorpdf -keyalg RSA -keysize 3072 -validity 10000 `
        -storepass $senha -keypass $senha -dname "CN=Editor de PDF, O=Uso pessoal, C=BR" 2>&1 | Out-Null
    $ErrorActionPreference = 'Stop'
    Set-Content (Join-Path $chave 'chave.properties') "arquivo=editorpdf.jks`napelido=editorpdf`nsenha=$senha" -Encoding ASCII
}

# 3) compila
Push-Location $Android
$ErrorActionPreference = 'Continue'
try { & $Gradle --no-daemon -q --project-cache-dir "$Build\out\gradle-cache" assembleRelease; if ($LASTEXITCODE) { throw "o Gradle falhou ($LASTEXITCODE)" } } finally { Pop-Location }
$apk = Join-Path $Build 'out\app\outputs\apk\release\app-release.apk'
$destino = Join-Path $Raiz 'instalador\Editor de PDF.apk'
Copy-Item $apk $destino -Force
"APK gerado: $destino ({0:N1} MB)" -f ((Get-Item $destino).Length / 1MB)

# Monta o site do Editor de PDF (iPhone, iPad e qualquer navegador) em %LOCALAPPDATA%\EditorPDF-web\site.
# É a mesma página do app, com o motor MuPDF.js: tudo roda no aparelho, nada é enviado a servidor nenhum.
$ErrorActionPreference = 'Stop'
$Web     = Split-Path -Parent $MyInvocation.MyCommand.Path
$Sistema = Join-Path (Split-Path $Web) 'sistema'
$Site    = Join-Path $env:LOCALAPPDATA 'EditorPDF-web\site'
New-Item -ItemType Directory $Site -Force | Out-Null
# limpa o que for gerado (mantém a pasta .git da publicação)
Get-ChildItem -LiteralPath $Site -Force | Where-Object Name -ne '.git' | ForEach-Object { Remove-Item -LiteralPath $_.FullName -Recurse -Force }

$versao = Get-Date -Format 'yyyyMMdd-HHmmss'
$html = [IO.File]::ReadAllText((Join-Path $Sistema 'editor-pdf.html'))
$cabeca = @'
<head>
<script>window.APP_WEB=true</script>
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Editor de PDF">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="apple-touch-icon" href="icone-180.png">
<link rel="manifest" href="manifest.webmanifest">
'@
$html = $html.Replace('<head>', $cabeca)
$html = $html.Replace('<meta name="viewport" content="width=device-width, initial-scale=1">', '<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">')
$html = $html.Replace('</body>', "<script>if('serviceWorker' in navigator)navigator.serviceWorker.register('sw.js').catch(()=>{})</script>`n</body>")
[IO.File]::WriteAllText((Join-Path $Site 'index.html'), $html, (New-Object Text.UTF8Encoding $false))
Copy-Item (Join-Path $Sistema 'motor.js') $Site
Copy-Item (Join-Path $Sistema 'lib') $Site -Recurse
[IO.File]::WriteAllText((Join-Path $Site 'sw.js'), ([IO.File]::ReadAllText((Join-Path $Web 'sw.js')).Replace('__VERSAO__', $versao)), (New-Object Text.UTF8Encoding $false))
Set-Content (Join-Path $Site '.nojekyll') '' -Encoding ASCII
Copy-Item (Join-Path $Web 'privacidade.html') $Site   # exigida pela Microsoft Store

# ícones (o iPhone arredonda os cantos sozinho, então vai o quadrado inteiro); gerados no TEMP porque o Python
# da Loja/instalador não enxerga pastas novas do %LOCALAPPDATA%
$tmpIco = Join-Path $env:TEMP 'editorpdf-icones'; New-Item -ItemType Directory $tmpIco -Force | Out-Null
py -c @"
from PIL import Image
im = Image.open(r'$Sistema\icone.png').convert('RGBA')
fundo = Image.new('RGBA', im.size, (12, 22, 48, 255)); fundo.alpha_composite(im)
for s in (180, 192, 512):
    fundo.convert('RGB').resize((s, s), Image.LANCZOS).save(r'$tmpIco\icone-%d.png' % s)
"@
Copy-Item (Join-Path $tmpIco 'icone-*.png') $Site
$manifesto = @{
    name = 'Editor de PDF'; short_name = 'Editor PDF'; start_url = './'; scope = './'; display = 'standalone'
    background_color = '#f3f3f3'; theme_color = '#0c1630'; lang = 'pt-BR'
    icons = @(@{ src = 'icone-192.png'; sizes = '192x192'; type = 'image/png' }, @{ src = 'icone-512.png'; sizes = '512x512'; type = 'image/png'; purpose = 'any' })
} | ConvertTo-Json -Depth 4
[IO.File]::WriteAllText((Join-Path $Site 'manifest.webmanifest'), $manifesto, (New-Object Text.UTF8Encoding $false))

# versao.json: o app do Windows e o do Android consultam para avisar que saiu versão nova.
# Os instaladores ficam na versão mais recente do GitHub (publicar-versao.ps1 envia os arquivos).
$raizAdobe = Split-Path $Web
$novidades = [IO.File]::ReadAllText((Join-Path $Web 'novidades.json')) | ConvertFrom-Json
$vWin = [IO.File]::ReadAllText((Join-Path $Sistema 'versao.txt')).Trim()
$vAnd = [regex]::Match([IO.File]::ReadAllText((Join-Path $raizAdobe 'android\app\build.gradle.kts')), 'versionName\s*=\s*"([^"]+)"').Groups[1].Value
$base = 'https://github.com/editorpdf/editorpdf.github.io/releases/latest/download/'
$vj = [ordered]@{
    windows = [ordered]@{ versao = $vWin; url = $base + 'Instalar-Editor-de-PDF.exe'; novidades = @($novidades.windows) }
    android = [ordered]@{ versao = $vAnd; url = $base + 'Editor-de-PDF.apk'; novidades = @($novidades.android) }
} | ConvertTo-Json -Depth 4
[IO.File]::WriteAllText((Join-Path $Site 'versao.json'), $vj, (New-Object Text.UTF8Encoding $false))
"Site gerado em $Site (versão $versao; Windows $vWin, Android $vAnd)"

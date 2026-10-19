# Bateria de testes do Editor de PDF. Rode antes de publicar uma versão.
#   testes\rodar-testes.ps1            testa o código (sistema\app.py)
#   testes\rodar-testes.ps1 -Pacote    testa o app já empacotado pelo PyInstaller (%TEMP%\epdf\Editor de PDF)
# Faz: amostras -> testes do servidor (Python) -> abre o app com o DevTools numa porta livre -> testes da interface
# no motor do Windows -> os mesmos testes no motor do celular/site (?motor=js) -> fecha o app.
# Atenção: fecha o Editor de PDF que estiver aberto (o app de teste usa o mesmo perfil do app instalado).
param([switch]$Pacote)
$ErrorActionPreference = 'Stop'
$Testes  = Split-Path -Parent $MyInvocation.MyCommand.Path
$Raiz    = Split-Path $Testes
$Sistema = Join-Path $Raiz 'sistema'
$Saida   = Join-Path $env:TEMP 'editorpdf-testes'
$env:EDITOR_PDF_TESSDATA = Join-Path $Raiz 'dados\tessdata'
$falhas = 0

function Fechar-App {
    Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -in 'Editor de PDF', 'EditorPDF' } | Stop-Process -Force
    Get-CimInstance Win32_Process -Filter "Name like 'py%.exe'" | Where-Object { $_.CommandLine -like '*sistema\app.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
    # o WebView2 do app rodado pelo Python às vezes fica aberto e "rouba" a próxima janela (sem a porta de depuração)
    Get-CimInstance Win32_Process -Filter "Name='msedgewebview2.exe'" | Where-Object { $_.CommandLine -like '*webview-exe-name=python.exe*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep 1
}
function Teste-Interface($rotulo) {
    $json = py (Join-Path $Testes 'cdp.py') js (Join-Path $Testes 'editor_testes.js') $Saida
    # só o número de falhas sai da função; o resto vai direto para a tela
    try { $r = $json | ConvertFrom-Json } catch { Write-Host "FALHOU  $rotulo`: resposta inesperada: $json"; return 1 }
    Write-Host "--- Interface ($($r.modo))"; $r.log | ForEach-Object { Write-Host $_ }
    return [int]$r.falhas
}

py (Join-Path $Testes 'amostras.py') $Saida
"--- Servidor"
py (Join-Path $Testes 'servidor_testes.py') $Saida
if ($LASTEXITCODE) { $falhas++ }

Fechar-App
# porta do DevTools: a primeira livre a partir de 9351 (outro programa pode estar usando a 9333)
$porta = 9351; while (Get-NetTCPConnection -LocalPort $porta -State Listen -ErrorAction SilentlyContinue) { $porta++ }
$env:EDITORPDF_CDP_PORTA = "$porta"
$env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = "--remote-debugging-port=$porta"
if ($Pacote) { Start-Process (Join-Path $env:TEMP 'epdf\Editor de PDF\Editor de PDF.exe') }
else { Start-Process py -ArgumentList ('"' + (Join-Path $Sistema 'app.py') + '"') -WorkingDirectory $Sistema }
Remove-Item Env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS
try {
    py (Join-Path $Testes 'cdp.py') esperar 90
    $falhas += Teste-Interface 'Windows'
    # o instalador do Windows não leva o motor do celular (lib\mupdf, lib\tesseract): no -Pacote ele não é testado
    if (-not $Pacote) {
        py (Join-Path $Testes 'cdp.py') ir '/?motor=js'
        Start-Sleep 2
        py (Join-Path $Testes 'cdp.py') esperar 60
        $falhas += Teste-Interface 'celular/site'
    } else { Write-Host '--- Motor do celular/site: pulado no -Pacote (testado sem o -Pacote)' }
} finally { Fechar-App }

""
if ($falhas) { "RESULTADO: $falhas grupo(s)/item(ns) com falha. Não publique antes de corrigir."; exit 1 }
"RESULTADO: tudo certo. Imagens para conferir a olho em $Saida (escaneado-editado.png, comparar.png)."

# Gera o pacote da Microsoft Store (loja\Editor de PDF.msix) a partir do app já empacotado pelo PyInstaller.
# Antes: gere o app (py -m PyInstaller editor-pdf.spec ... --distpath %TEMP%\epdf) e preencha loja\identidade.json
# com os dados do Partner Center. A Loja assina o pacote; aqui ele sai sem assinatura (é assim que se envia).
# Ferramentas (MakeAppx e MakePri) em %LOCALAPPDATA%\MsixTools\x64 (pasta bin\<versão>\x64 do pacote Microsoft.Windows.SDK.BuildTools do NuGet).
param([string]$App = (Join-Path $env:TEMP 'epdf\Editor de PDF'))
$ErrorActionPreference = 'Stop'
$Loja = Split-Path -Parent $MyInvocation.MyCommand.Path
$Raiz = Split-Path $Loja
$Sistema = Join-Path $Raiz 'sistema'
# roda de uma cópia no TEMP: de dentro do %LOCALAPPDATA% o Windows não carrega as peças do MakeAppx (erro de configuração lado a lado)
$bin = Join-Path $env:TEMP 'epdf-msixtools'
# copia o conteúdo da pasta (com a pasta de destino já existente, copiar a pasta em si criaria uma subpasta x64)
if (-not (Test-Path (Join-Path $bin 'makeappx.exe'))) {
    if (Test-Path $bin) { Remove-Item -LiteralPath $bin -Recurse -Force }
    New-Item -ItemType Directory $bin -Force | Out-Null
    Copy-Item "$env:LOCALAPPDATA\MsixTools\x64\*" $bin -Recurse -Force
}
$makeappx = Join-Path $bin 'makeappx.exe'; $makepri = Join-Path $bin 'makepri.exe'
if (-not (Test-Path (Join-Path $App 'Editor de PDF.exe'))) { throw "App do PyInstaller não encontrado em $App" }

$id = Get-Content (Join-Path $Loja 'identidade.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$v = [IO.File]::ReadAllText((Join-Path $Sistema 'versao.txt')).Trim()
$partes = @($v.Split('.') | ForEach-Object { [int]$_ }); while ($partes.Count -lt 3) { $partes += 0 }
$versao = '{0}.{1}.{2}.0' -f $partes[0], $partes[1], $partes[2]   # a Loja exige o último número 0

# 1) pasta do pacote (fora do OneDrive)
$area = Join-Path $env:TEMP 'epdf-msix'; $pasta = Join-Path $area 'root'
if (Test-Path $area) { Remove-Item -LiteralPath $area -Recurse -Force }
New-Item -ItemType Directory $pasta -Force | Out-Null
robocopy $App $pasta /E /NFL /NDL /NJH /NJS /NP | Out-Null
Rename-Item (Join-Path $pasta 'Editor de PDF.exe') 'EditorPDF.exe'

# 2) ícones (gerados no TEMP: o Python não enxerga pastas novas do %LOCALAPPDATA%)
$tmpIc = Join-Path $env:TEMP 'epdf-msix-icones'
if (Test-Path $tmpIc) { Remove-Item -LiteralPath $tmpIc -Recurse -Force }
py -3 (Join-Path $Loja 'icones_loja.py') (Join-Path $Sistema 'icone.png') $tmpIc
Copy-Item $tmpIc (Join-Path $pasta 'Assets') -Recurse

# 3) manifesto
$esc = { param($s) [Security.SecurityElement]::Escape([string]$s) }
$nomeLoja = if ($id.DisplayName) { $id.DisplayName } else { 'Editor de PDF' }   # tem que ser o nome reservado no Partner Center
$manifesto = @"
<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
         xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
         xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
         IgnorableNamespaces="uap rescap">
  <Identity Name="$(& $esc $id.Name)" Publisher="$(& $esc $id.Publisher)" Version="$versao" ProcessorArchitecture="x64" />
  <Properties>
    <DisplayName>$(& $esc $nomeLoja)</DisplayName>
    <PublisherDisplayName>$(& $esc $id.PublisherDisplayName)</PublisherDisplayName>
    <Logo>Assets\StoreLogo.png</Logo>
  </Properties>
  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.17763.0" MaxVersionTested="10.0.26100.0" />
  </Dependencies>
  <Resources>
    <Resource Language="pt-BR" />
  </Resources>
  <Applications>
    <Application Id="EditorPDF" Executable="EditorPDF.exe" EntryPoint="Windows.FullTrustApplication">
      <uap:VisualElements DisplayName="$(& $esc $nomeLoja)" Description="Ler, editar, assinar e converter PDFs"
                          BackgroundColor="transparent" Square150x150Logo="Assets\Square150x150Logo.png" Square44x44Logo="Assets\Square44x44Logo.png">
        <uap:DefaultTile Wide310x150Logo="Assets\Wide310x150Logo.png" />
      </uap:VisualElements>
      <Extensions>
        <uap:Extension Category="windows.fileTypeAssociation">
          <uap:FileTypeAssociation Name="pdf">
            <uap:DisplayName>Documento PDF</uap:DisplayName>
            <uap:Logo>Assets\Square44x44Logo.png</uap:Logo>
            <uap:SupportedFileTypes>
              <uap:FileType ContentType="application/pdf">.pdf</uap:FileType>
            </uap:SupportedFileTypes>
          </uap:FileTypeAssociation>
        </uap:Extension>
      </Extensions>
    </Application>
  </Applications>
  <Capabilities>
    <rescap:Capability Name="runFullTrust" />
  </Capabilities>
</Package>
"@
[IO.File]::WriteAllText((Join-Path $pasta 'AppxManifest.xml'), $manifesto, (New-Object Text.UTF8Encoding $false))

# 4) índice dos ícones (resources.pri) e o pacote
$ErrorActionPreference = 'Continue'
& $makepri createconfig /cf (Join-Path $area 'priconfig.xml') /dq pt-BR /pv 10.0.0 /o | Out-Null
# um índice só (sem separar por escala: isso é para pacotes divididos, que não usamos)
$cfg = [xml](Get-Content (Join-Path $area 'priconfig.xml') -Raw); $cfg.SelectNodes('//packaging') | ForEach-Object { [void]$_.ParentNode.RemoveChild($_) }; $cfg.Save((Join-Path $area 'priconfig.xml'))
& $makepri new /pr $pasta /cf (Join-Path $area 'priconfig.xml') /mn (Join-Path $pasta 'AppxManifest.xml') /of (Join-Path $pasta 'resources.pri') /o | Out-Null
if ($LASTEXITCODE) { throw "o MakePri falhou ($LASTEXITCODE)" }
$saida = Join-Path $Loja 'Editor de PDF.msix'
& $makeappx pack /d $pasta /p $saida /o | Out-Null
if ($LASTEXITCODE) { throw "o MakeAppx falhou ($LASTEXITCODE)" }
$ErrorActionPreference = 'Stop'
"Pacote gerado: $saida ({0:N1} MB), versão $versao, identidade $($id.Name)" -f ((Get-Item $saida).Length / 1MB)
"Pasta do pacote (para testar neste PC): $pasta"

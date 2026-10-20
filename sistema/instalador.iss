; Instalador do Editor de PDF (Inno Setup 6). Gerar:  ISCC.exe /DOrigem=<pasta "Editor de PDF" do PyInstaller> instalador.iss
#ifndef Origem
  #error Informe /DOrigem=<pasta gerada pelo PyInstaller>
#endif
; a versão fica em versao.txt (o app lê o mesmo arquivo para avisar de atualizações)
#define ArqVersao FileOpen(AddBackslash(SourcePath) + "versao.txt")
#define Versao Trim(FileRead(ArqVersao))
#expr FileClose(ArqVersao)

[Setup]
AppId={{6E7B2F4A-3C1D-4E8B-9A5F-ED1708C0FF01}
AppName=Editor de PDF
AppVersion={#Versao}
AppPublisher=Editor de PDF
DefaultDirName={localappdata}\Programs\Editor de PDF
DefaultGroupName=Editor de PDF
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
OutputDir=..\instalador
OutputBaseFilename=Instalar Editor de PDF
SetupIconFile=icone.ico
UninstallDisplayIcon={app}\Editor de PDF.exe
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
ChangesAssociations=yes

[Languages]
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "atalho"; Description: "Criar atalho na área de trabalho"; Flags: checkedonce
Name: "leitor"; Description: "Usar o Editor de PDF para abrir arquivos PDF (duplo clique)"; Flags: checkedonce

[Registry]
; tipo de arquivo do app e o comando que abre o PDF
Root: HKCU; Subkey: "Software\Classes\EditorPDF.pdf"; ValueType: string; ValueName: ""; ValueData: "Documento PDF"; Flags: uninsdeletekey; Tasks: leitor
Root: HKCU; Subkey: "Software\Classes\EditorPDF.pdf\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: """{app}\_internal\icone.ico"""; Tasks: leitor
Root: HKCU; Subkey: "Software\Classes\EditorPDF.pdf\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Editor de PDF.exe"" ""%1"""; Tasks: leitor
; aparece em "Abrir com"
Root: HKCU; Subkey: "Software\Classes\.pdf\OpenWithProgids"; ValueType: string; ValueName: "EditorPDF.pdf"; ValueData: ""; Flags: uninsdeletevalue; Tasks: leitor
Root: HKCU; Subkey: "Software\Classes\Applications\Editor de PDF.exe\SupportedTypes"; ValueType: string; ValueName: ".pdf"; ValueData: ""; Flags: uninsdeletekey; Tasks: leitor
Root: HKCU; Subkey: "Software\Classes\Applications\Editor de PDF.exe"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "Editor de PDF"; Tasks: leitor
; aparece em Configurações > Aplicativos padrão
Root: HKCU; Subkey: "Software\EditorPDF\Capabilities"; ValueType: string; ValueName: "ApplicationName"; ValueData: "Editor de PDF"; Flags: uninsdeletekey; Tasks: leitor
Root: HKCU; Subkey: "Software\EditorPDF\Capabilities"; ValueType: string; ValueName: "ApplicationDescription"; ValueData: "Ler, editar e converter PDFs"; Tasks: leitor
Root: HKCU; Subkey: "Software\EditorPDF\Capabilities\FileAssociations"; ValueType: string; ValueName: ".pdf"; ValueData: "EditorPDF.pdf"; Tasks: leitor
Root: HKCU; Subkey: "Software\RegisteredApplications"; ValueType: string; ValueName: "Editor de PDF"; ValueData: "Software\EditorPDF\Capabilities"; Flags: uninsdeletevalue; Tasks: leitor
; "Abrir junto com o Windows" (o app grava esse valor quando o usuário liga a opção): sai ao desinstalar
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "Editor de PDF"; Flags: dontcreatekey uninsdeletevalue

[Files]
Source: "{#Origem}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Editor de PDF"; Filename: "{app}\Editor de PDF.exe"
Name: "{userdesktop}\Editor de PDF"; Filename: "{app}\Editor de PDF.exe"; Tasks: atalho

[Run]
; o Windows não deixa um programa virar o padrão sozinho: abre a tela de Aplicativos padrão já no Editor de PDF
Filename: "{sys}\cmd.exe"; Parameters: "/c start """" ""ms-settings:defaultapps?registeredAppUser=Editor%20de%20PDF"""; Description: "Escolher o Editor de PDF como leitor padrão de PDF (abre as Configurações)"; Flags: nowait postinstall skipifsilent runhidden; Tasks: leitor
Filename: "{app}\Editor de PDF.exe"; Description: "Abrir o Editor de PDF agora"; Flags: nowait postinstall skipifsilent unchecked

[InstallDelete]
; limpeza na instalação/atualização: só o que ficou obsoleto (os dados do usuário continuam)
; perfil do Edge usado até a versão 1.4 (desde a 1.5 a janela é própria; se precisar de novo, o app recria)
Type: filesandordirs; Name: "{localappdata}\EditorPDF\janela"
; programas que o app detecta (Office, Ghostscript...): é refeito na primeira abertura
Type: files; Name: "{localappdata}\EditorPDF\ambiente.json"

[UninstallRun]
; com "Abrir junto com o Windows" o app fica em segundo plano: fecha antes de apagar os arquivos
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM ""Editor de PDF.exe"""; Flags: runhidden; RunOnceId: "FecharApp"

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\EditorPDF"

[Code]
// Se o app já está instalado, o mesmo instalador vira "Atualizar": mantém a pasta, as opções escolhidas
// antes (atalho, leitor de PDF) e as configurações, e só troca os arquivos.
var
  Anterior: String;

function VersaoInstalada(): String;
begin
  Result := '';
  if not RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{6E7B2F4A-3C1D-4E8B-9A5F-ED1708C0FF01}_is1', 'DisplayVersion', Result) then
    Result := '';
end;

// compara "1.4" com "1.10" número a número; devolve <0, 0 ou >0
function CompararVersoes(A, B: String): Integer;
var
  PA, PB, NA, NB: Integer;
begin
  Result := 0;
  while (Result = 0) and ((A <> '') or (B <> '')) do begin
    PA := Pos('.', A); PB := Pos('.', B);
    if PA = 0 then begin NA := StrToIntDef(A, 0); A := ''; end
    else begin NA := StrToIntDef(Copy(A, 1, PA - 1), 0); Delete(A, 1, PA); end;
    if PB = 0 then begin NB := StrToIntDef(B, 0); B := ''; end
    else begin NB := StrToIntDef(Copy(B, 1, PB - 1), 0); Delete(B, 1, PB); end;
    Result := NA - NB;
  end;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  Anterior := VersaoInstalada();
  if (Anterior <> '') and (CompararVersoes(Anterior, '{#Versao}') > 0) then
    Result := MsgBox('Já existe uma versão mais nova do Editor de PDF instalada (' + Anterior + ').' #13#13 +
      'Instalar a versão {#Versao} por cima vai voltar para uma versão mais antiga. Continuar mesmo assim?',
      mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES;
end;

procedure InitializeWizard();
begin
  if Anterior = '' then exit;
  if Anterior = '{#Versao}' then
    WizardForm.Caption := 'Reinstalar Editor de PDF {#Versao}'
  else
    WizardForm.Caption := 'Atualizar Editor de PDF para a versão {#Versao}';
end;

// na atualização as opções já foram escolhidas na primeira instalação
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (Anterior <> '') and (PageID = wpSelectTasks);
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if Anterior = '' then exit;
  if CurPageID = wpReady then begin
    WizardForm.ReadyMemo.Visible := False;
    WizardForm.ReadyLabel.AutoSize := False;
    WizardForm.ReadyLabel.WordWrap := True;
    WizardForm.ReadyLabel.Height := WizardForm.ReadyMemo.Top + WizardForm.ReadyMemo.Height - WizardForm.ReadyLabel.Top;
    if Anterior = '{#Versao}' then begin
      WizardForm.PageNameLabel.Caption := 'Pronto para reinstalar';
      WizardForm.PageDescriptionLabel.Caption := 'A versão {#Versao} já está instalada.';
      WizardForm.ReadyLabel.Caption := 'Os arquivos do Editor de PDF {#Versao} serão instalados de novo. Suas configurações e PDFs não são alterados.';
      WizardForm.NextButton.Caption := 'Reinstalar';
    end else begin
      WizardForm.PageNameLabel.Caption := 'Pronto para atualizar';
      WizardForm.PageDescriptionLabel.Caption := 'Versão instalada: ' + Anterior + '   →   nova versão: {#Versao}';
      WizardForm.ReadyLabel.Caption := 'O Editor de PDF será atualizado para a versão {#Versao}, no mesmo lugar. O atalho, o leitor de PDF e as suas configurações continuam como estão.' #13#13 +
        'Se o Editor de PDF estiver aberto, ele será fechado.';
      WizardForm.NextButton.Caption := 'Atualizar';
    end;
  end else if CurPageID = wpFinished then begin
    if Anterior = '{#Versao}' then
      WizardForm.FinishedLabel.Caption := 'O Editor de PDF {#Versao} foi reinstalado.'
    else
      WizardForm.FinishedLabel.Caption := 'O Editor de PDF foi atualizado da versão ' + Anterior + ' para a {#Versao}.';
  end;
end;


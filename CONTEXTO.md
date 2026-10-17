# Contexto: Editor de PDF (para quem for continuar)

Editor de PDF local, no navegador, com um servidor Python opcional que apaga o texto de verdade.

## Estrutura

```
Adobe/
  Painel Editor de PDF.lnk   atalho único que o usuário abre
  sistema/                   o programa
    editor-pdf.html          o editor (HTML único; pdf.js e pdf-lib vêm de CDN)
    servidor.py              servidor (Python + PyMuPDF): página, /api/analyze, /api/apply
    painel.py + painel.html  painel: mini servidor local (127.0.0.1:8769) + página, aberta em janela Edge/Chrome --app
    abrir-painel.vbs         abre o painel sem janela de console (pyw -3 painel.py)
    ligar-servidor.vbs       liga o servidor sem janela (painel.py --ligar; usado no início do Windows)
    Abrir editor.bat         alternativa simples, sem painel
  dados/                     config.json ({"rede": true|false}) e registros.log. Não apagar à mão.
  replica/                   recon, matriz de funções, testes e relatório (processo de clonagem)
  LEIA-ME.md                 manual do usuário
```

## Como roda

- Porta 8768. O painel (`painel.py`, rodado com `pyw -3`) liga o servidor com o `python.exe` ao lado do seu `pythonw.exe` (o `python` do Windows pode ser só o atalho da Loja). Desligar = achar o PID que escuta a porta (`netstat -ano` lido em latin-1, independe do idioma) e `taskkill /F /T`. O painel fecha sozinho ~25 s depois de a janela sumir (a página consulta `/api/estado` a cada 2 s). Ações demoradas rodam em thread e a página acompanha por `/api/trabalho`, então a janela não trava. Só aceita Host localhost/127.0.0.1:8769 e Origin igual.
- `dados\config.json` → `rede: true` faz o servidor escutar em 0.0.0.0; senão só 127.0.0.1. O painel grava o arquivo e reinicia o servidor.
- Proteções: o cabeçalho Host só aceita localhost e, com a rede ligada, IPs privados (nunca nomes de domínio); POST exige Origin igual ao Host; o corpo é validado (`validar_ops`); limite de 150 MB por pedido.
- `py servidor.py verificar` confere PyMuPDF, pdf2docx, fontes do Windows, página e pasta de dados.
- `/api/pdf2docx` (pdf2docx + python-docx) converte o PDF em .docx na memória; o cliente manda o PDF já com as edições pendentes aplicadas (`bake`). PDF sem texto devolve um aviso (sem OCR). `/api/ping` informa `docx: true|false`.
- OCR: o PyMuPDF já traz o motor Tesseract; só faltam os idiomas, em `dados\tessdata` (nenhum programa extra). `/api/ocr` usa `pix.pdfocr_tobytes` por página (300 dpi) e remonta o PDF com o tamanho original; `/api/pdf2docx` usa OCR sozinho quando o PDF não tem texto (`docx_de_ocr`, junta linhas em parágrafos). `/api/ping` informa `ocr` e `idiomas`. Cuidado: `get_textpage_ocr` dá erro de referência fraca se a página não for guardada numa variável.
- Ferramentas em lote: `sistema/ferramentas.py` (registro `FERRAMENTAS`: função, mín/máx de arquivos, extensões) chamado por `POST /api/tool` com `{ferramenta, arquivos:[{nome,b64}], opcoes}`; devolve um arquivo (vários viram `.zip`) e avisos. O cliente define as ferramentas e os formulários em `TOOLS2` (editor-pdf.html), então para adicionar uma ferramenta: função em `ferramentas.py` + linha em `FERRAMENTAS` + objeto em `TOOLS2`. Dependências: PyMuPDF, pdf2docx, python-docx, Pillow, openpyxl, python-pptx.
- `office2pdf` roda um script PowerShell com COM (Word/Excel/PowerPoint, `AutomationSecurity=3`, um por vez por causa de `_office_lock`); `html2pdf` usa `msedge --headless --print-to-pdf` com perfil temporário e só aceita URL pública (resolve o nome e recusa IP não global). As duas são recusadas (403) para clientes que não sejam 127.0.0.1, e `/api/ping` informa `office: []` e `navegador: false` a eles.
- O painel abre o editor com `msedge.exe`/`chrome.exe --app=URL` (janela sem abas). Sem Edge/Chrome, abre no navegador padrão.
- Interface: `editor-pdf.html` tem tema claro/escuro (localStorage `editorpdf-tema`), tela inicial com cartões e barra de status; os ids dos elementos (bOpen, bSave, rail, tlist, right...) são usados pelo JS.
- Não há backup de dados: o app não guarda nada além de config e registro (os PDFs não são gravados).

## Recursos novos (2026-10-16)

- Formulários: `loadFields()` lê os widgets pelo pdf.js (`getAnnotations`), `addFields()` desenha inputs na camada da página, valores em `S.form`; `fillForm()` grava com pdf-lib dentro do `bake()` (e `S.flatten` trava). Com formulário, a página é renderizada com `AnnotationMode.ENABLE_FORMS`. `dirty()` diz se há algo a gravar (objetos, formulário ou travar).
- Carimbo: ferramenta `stamp` → `openStamp()` desenha num canvas e vira objeto `img`.
- Busca: `POST /api/buscar {pdf, opcoes:{padroes, termos, maiusculas, inteira}}` → `ferramentas.buscar()` (regex por linha, retângulos dos caracteres). Usado pela barra de busca (`openFind`, destaque `S.hits`) e pela tarja automática do editor (`openAutoRedact`, cria objetos `redact`).
- Substituir: ferramenta `substituir` → `servidor.substituir_texto()` monta operações `rep` por linha e usa `apply_ops`. `FontPicker` agora usa a fonte padrão do PDF (helv/tiro/cour) quando o original era Helvetica/Times/Courier não embutida (evita espaços virando NBSP).
- Ferramentas novas em `ferramentas.py`: `cabecalho`, `tarja_auto`, `substituir`, `pdfa` (Ghostscript: `ghostscript()` procura `EDITOR_PDF_GS`, `_MEIPASS\gs` ou Program Files), `assinar` (pyHanko; carimbo desenhado pelo PyMuPDF como `StaticStampStyle`; recusada para clientes da rede), `img_comprimir/redimensionar/recortar/converter/girar`. `/api/ping` informa `pdfa` e `assinatura`.
- Grade de páginas: `openOrganizer()` (sobreposto à `#view`, reaproveita os botões de `.thumbs .tb`).
- Dependências novas: `pyhanko` (e `cryptography`); Ghostscript 10.08 instalado em Program Files (licença AGPL, a licença vai junto no pacote).

## Site (iPhone e navegadores)

- `web\gerar-web.ps1` monta o site em `%LOCALAPPDATA%\EditorPDF-web\site` (fora do OneDrive): editor com `window.APP_WEB=true` (usa o `motor.js`), metas do iOS, `manifest.webmanifest`, ícones 180/192/512 e `sw.js` (cache para funcionar offline; a versão muda a cada geração). `web\publicar-web.ps1` gera e faz `git push` (repositório público `editorpdf/editorpdf.github.io`, da organização editorpdf, onde a conta k2locserv-collab é admin; GitHub Pages na branch main, endereço https://editorpdf.github.io/). Git portátil em `%LOCALAPPDATA%\MinGit`, GitHub CLI pelo winget.
- No iOS, salvar usa `navigator.share({files})` (janela de compartilhar, com "Salvar em Arquivos").
- Teste com o WebKit do Playwright (emulação do iPhone 13).

## Android (APK)

- `sistema\motor.js`: motor que roda na própria página (MuPDF.js 1.28 em WebAssembly + pdf-lib + Tesseract.js 7), com as mesmas rotas do servidor (`/api/ping`, `/api/analyze`, `/api/apply`, `/api/ocr`, `/api/buscar`, `/api/tool`). O editor usa o motor quando `window.APP_CELULAR` existe ou com `?motor=js` (para testar no computador: `http://127.0.0.1:8768/?motor=js`). Sem: Word/Excel/PowerPoint, Office/HTML para PDF, PDF/A e certificado (`SO_COMPUTADOR` no editor).
- Bibliotecas em `sistema\lib\mupdf` e `sistema\lib\tesseract` (core 7, só as variantes LSTM; idiomas por e eng). O servidor.py entrega qualquer arquivo dentro de `lib` (com proteção contra `..`).
- Projeto em `android\` (Java, sem AndroidX além de webkit e core). `MainActivity`: WebView com `WebViewAssetLoader` (https://appassets.androidplatform.net/assets/www/), tipos MIME próprios (wasm/js), seletor de arquivos, ponte `AndroidApp` (`salvar` em Downloads/Editor de PDF, `compartilhar` via FileProvider, `nomeRecebido`), "Abrir com"/compartilhar PDF (servido em `/recebido/`), botão Voltar chama `voltarAndroid()` no editor.
- Gerar: `android\gerar-apk.ps1` (copia o editor com `APP_CELULAR` para `%LOCALAPPDATA%\AndroidBuild\assets\www`, cria a chave na 1ª vez e roda o Gradle; saída `instalador\Editor de PDF.apk`). Ferramentas em `%LOCALAPPDATA%\AndroidBuild` (JDK 17 Temurin, SDK 36, Gradle 9.8.1, AGP 9.4.1). O build e os assets ficam fora do OneDrive (a sincronização travava arquivos).
- Chave: `android\chave\editorpdf.jks` + `chave.properties` (senha em texto). Sem ela não dá para atualizar o app instalado.
- Teste: emulador `teste` (Android 14) em `%LOCALAPPDATA%\AndroidBuild\avd`; a versão debug liga a depuração da WebView para testar pelo DevTools (`adb forward tcp:9333 localabstract:webview_devtools_remote_<pid>`).

## Aplicativo (.exe) para mandar a outras pessoas

- `instalador\Instalar Editor de PDF.exe` (~74 MB): instala por usuário, sem pedir administrador, em `%LOCALAPPDATA%\Programs\Editor de PDF`, com atalho no menu Iniciar e na área de trabalho e desinstalador. Sem assinatura digital: o SmartScreen avisa na primeira vez ("Mais informações" > "Executar assim mesmo").
- `sistema\app.py` é a entrada do .exe: liga o servidor por dentro (só 127.0.0.1, porta 8770 ou uma livre), abre uma janela própria (pywebview + WebView2, dados em `%LOCALAPPDATA%\EditorPDF\webview`) e encerra quando a última janela fecha. "Salvar" no app chama `pywebview.api.salvar` (janela "Salvar como" do Windows) em vez de baixar. Segunda abertura manda `/api/abrir` (com ou sem PDF) e o app aberto cria outra janela (`servidor.NOVA_JANELA`, `instancia.json`). Sem WebView2, cai no Edge `--app` (perfil `%LOCALAPPDATA%\EditorPDF\janela`), como até a 1.4. Para depurar: `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9333`.
- Versão 1.7 (Windows) / 1.3 (Android):
  - PDF em bytes, não base64: `api()` aceita `pdf: Uint8Array`. No servidor vai uma vez por `POST /api/doc` (o servidor guarda em `DOCS`, até 600 MB; 410 = mandar de novo) e as chamadas usam `doc: id`; o PDF de volta vem em `/api/doc/<id>` e chega como `j.pdfBytes`. `/api/arquivo` já devolve `X-Doc` e `X-Caminho`. No `motor.js` os bytes passam direto (`pdfBytes`).
  - O pywebview põe um filtro de requisições no WebView2 que deixa envios grandes lentos; `soltar_filtro()` no app.py tira.
  - A janela abre na hora com "Abrindo…" (`ABRINDO`) enquanto o servidor carrega numa thread. `ambiente()` lê `dados\ambiente.json` e confere por trás.
  - Páginas longe da tela soltam a imagem (`liberarPagina`); página atual por busca binária no scroll.
  - Leitor: camada de texto do pdf.js (`camadaTexto`, `.textLayer`; com Selecionar, `.layer.t-select` deixa o clique passar), links, sumário (`montarSumario`, abas Páginas/Sumário).
  - IndexedDB `editorpdf` (`BANCO`): `recentes` (no Windows só o caminho, reaberto por `pywebview.api.recente`; no celular/site uma cópia até 40 MB) e `recuperar`/`recuperar-bytes` (edições não salvas). Assinaturas em localStorage `editorpdf-assinaturas`.
  - Atualização: versão do Windows em `sistema\versao.txt` (o instalador lê o mesmo arquivo), do Android no build.gradle.kts. `web\gerar-web.ps1` gera `versao.json` com `web\novidades.json`; `web\publicar-versao.ps1` manda instalador e APK para as releases de `editorpdf/editorpdf.github.io` e publica o site. O app compara e oferece "Atualizar agora" (`pywebview.api.atualizar` baixa só de github.com/editorpdf ou editorpdf.github.io e abre o instalador).
  - Instalador menor: o spec tira o FFmpeg do OpenCV (`opencv_videoio_ffmpeg`).
- Versão 1.9: o instalador apaga na atualização só o obsoleto (`[InstallDelete]`: pasta `janela` do Edge antigo e `ambiente.json`); os dados do usuário (pasta `webview`) ficam. Botão "Restaurar o app" na tela inicial (`restaurarApp`): apaga o banco IndexedDB, localStorage, caches do site e, no Windows, `pywebview.api.restaurar` remove `ambiente.json`, `registros.log` e `janela`.
- Versão 2.0 (17/10/2026, Windows e Android com o mesmo número; Android versionCode 7): "Sobre e licenças" e código aberto. A Microsoft Store continua com o envio 1.9 em certificação; a 2.0 entra na Loja num envio separado (gerar-msix.ps1 + Partner Center → Atualizar).
- Versão 2.1 (17/10/2026; Android versionCode 8): PDF com senha (`desbloquearAoAbrir`/`pedirSenha` usam a ferramenta `desbloquear`; `S.senha` e `protegerDeNovo` recolocam a senha no `save()`). PDF escaneado editável: `analyze`/`analisar` marcam blocos `ocr` (servidor: spans com alpha 0; motor.js: fonte GlyphLessFont) com `color` (tinta) e `bg` (papel) tirados dos pixels (`cores_da_area`/`coresDaArea`); `apply_ops`/`aplicar` apagam os pixels da imagem (REDACT_IMAGE_PIXELS, caixa aumentada embaixo) e pintam a cor do papel antes de escrever. No editor, `oferecerOcrParaEditar` aparece ao usar "Editar texto" numa página sem texto e com imagem. Testar o app a partir do código precisa de `EDITOR_PDF_TESSDATA=<Adobe>\dados\tessdata`, senão o OCR aparece desligado. A Loja ainda está com o envio 2.0 em certificação.
- Microsoft Store (pasta `loja`): `gerar-msix.ps1` monta o MSIX a partir do app do PyInstaller (exe renomeado para `EditorPDF.exe`, ícones por `icones_loja.py`, manifesto com associação .pdf e `runFullTrust`, `resources.pri`). Identidade em `loja\identidade.json` (valores do Partner Center). MakeAppx/MakePri em `%LOCALAPPDATA%\MsixTools\x64`, executados de uma cópia no TEMP (de dentro do LOCALAPPDATA dá erro de configuração lado a lado). No pacote, `app.py` detecta `LOJA` (GetCurrentPackageFullName) e o editor não mostra o próprio aviso de atualização. O spec tira `docx/templates/default-docx-template` (tem `[Content_Types].xml`, nome proibido no MSIX). Passo a passo e textos da listagem em `loja\COMO-PUBLICAR.md`; política de privacidade em `web\privacidade.html` (publicada no site).
- Imprimir (1.6): botão da impressora, menu Exportar e Ctrl+P (`openPrint`/`imprimir` no editor). No computador e no iPhone, as páginas viram imagens de ~200 dpi em `#impressao` (só ela aparece no `@media print`) e chama `window.print()`; papel deitado se a maioria das páginas for deitada. No Android, manda o próprio PDF para `AndroidApp.imprimir` (PrintManager). Dados e registro em `%LOCALAPPDATA%\EditorPDF`; o OCR usa o `tessdata` embutido (`EDITOR_PDF_TESSDATA`). Sem painel e sem compartilhamento na rede.
- Abrir com dois cliques: o instalador (tarefa `leitor`) registra o ProgID `EditorPDF.pdf` em HKCU, "Abrir com" e `RegisteredApplications` e abre `ms-settings:defaultapps?registeredAppUser=Editor de PDF`. O Windows chama `Editor de PDF.exe "<arquivo>"`; o `app.py` registra o caminho (`servidor.registrar_arquivo`, id aleatório) e abre `/?abrir=<id>`; a página baixa de `/api/arquivo/<id>`. Com o app já aberto, a nova cópia manda `POST /api/abrir` com o cabeçalho `X-Segredo` (gravado em `instancia.json`) e só abre outra janela.
- Licença: o projeto é AGPL-3.0-or-later (MuPDF/PyMuPDF/MuPDF.js e Ghostscript são AGPL). Código público em `github.com/editorpdf/editor-pdf`. `codigo\publicar-codigo.ps1` copia uma lista fixa de arquivos para `%LOCALAPPDATA%\EditorPDF-codigo\repo` (Git com identidade noreply do GitHub), recusa .jks/.log/.exe/.apk/.msix/chave.properties, faz commit, marca `windows-X-android-Y` e envia; `web\publicar-versao.ps1` chama sozinho. README, LICENSE, TERCEIROS.md e .gitignore do repositório ficam em `codigo\`. Arquivo novo que deva ir para o repositório precisa entrar na `$lista` do script. No editor, "Sobre e licenças" (`#bSobre`, lista `TERCEIROS`, `abrirFora`: `AndroidApp.abrirLink` / `pywebview.api.link` / `window.open`, só https).
- As bibliotecas JS ficam em `sistema\lib` (servidas em `/lib/`), então nada vem da internet.
- Gerar de novo (rode em `sistema`; a pasta de saída precisa de caminho curto, senão o PyMuPDF não carrega a DLL):
  `py -m PyInstaller editor-pdf.spec --noconfirm --distpath %TEMP%\epdf --workpath %TEMP%\epdf-build`
  `"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" "/DOrigem=%TEMP%\epdf\Editor de PDF" instalador.iss`
- Ícone: `sistema\icone.ico`. O pacote fica grande por causa do OpenCV que o pdf2docx usa.

## Armadilhas

- Rodar `servidor.py` com a rede ligada pede permissão no Firewall do Windows na primeira vez.
- O IP da rede muda quando o Wi-Fi reconecta.
- Sem login: quem alcançar o endereço usa o editor.
- A troca de texto usa a fonte original só se o PDF tiver todas as letras novas; senão Arial/Times/Courier do Windows.
- Páginas giradas usam o modo básico para trocar texto.

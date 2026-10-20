# Editor de PDF — instruções para a IA que for trabalhar nesta pasta

Leia este arquivo inteiro antes de mexer em qualquer coisa. Ele explica **o que é o app, como e por que foi feito
assim, como lançar uma versão e como testar**. Os detalhes de cada parte, versão por versão, estão em `CONTEXTO.md`;
o manual de uso (para pessoas) está em `LEIA-ME.md`. O mesmo conteúdo vale para qualquer IA (o `AGENTS.md` aponta para cá).

---

## 1. O app em uma frase

Editor de PDF gratuito, que funciona **sem internet e sem mandar o arquivo para lugar nenhum**: troca o texto do PDF
de verdade (apaga o antigo do arquivo), assina, aplica tarja que remove dados, organiza páginas, converte para Word,
reconhece texto de escaneado (OCR) e mais ~35 ferramentas. Existe em quatro formas, todas com **a mesma tela**:

| Forma | Onde | Motor |
| --- | --- | --- |
| App do Windows (instalador `.exe`) | `instalador\Instalar Editor de PDF.exe` | Python + PyMuPDF (`sistema\servidor.py`) |
| Microsoft Store | produto **Editor de PDF Fácil**, Store ID `9P5JP86G028L` | o mesmo app do Windows, empacotado em MSIX |
| Android (APK) | `instalador\Editor de PDF.apk` | MuPDF.js em WebAssembly (`sistema\motor.js`) |
| Site (iPhone, iPad, qualquer navegador) | https://editorpdf.github.io | MuPDF.js (`sistema\motor.js`) |

Nomes exatos: o app se chama **"Editor de PDF"**; na Microsoft Store o nome reservado é **"Editor de PDF Fácil"**
("Editor de PDF" já era de outra pessoa). Pacote Android: `br.editorpdf.app`. Código-fonte público (AGPL-3.0):
https://github.com/editorpdf/editor-pdf. Versão atual: ver `sistema\versao.txt` (era **2.3** em 19/10/2026).

---

## 2. Como trabalhar com o dono do app

- Escreva **em português do Brasil**, simples e direto. O dono não é programador: explique o resultado e o que ele
  precisa fazer, não o código.
- **Diga exatamente o que foi testado e o que não foi.** Nunca diga "funciona" sem ter rodado o teste.
- **Peça confirmação antes de qualquer ação para fora do computador**: publicar versão, enviar para a Microsoft Store,
  criar repositório, aceitar termos, mexer em conta. Mostre o que vai ser enviado antes de clicar em "Enviar".
  Ele já autorizou baixar e instalar as ferramentas de desenvolvimento necessárias.
- Depois de cada mudança: rode os testes (seção 6), atualize `CONTEXTO.md` (e `LEIA-ME.md` se mudou algo para o usuário)
  e, ao lançar, escreva as novidades em `web\novidades.json` em linguagem de usuário.
- Mudanças pequenas podem esperar a próxima versão; pergunte se ele quer lançar agora ou junto com a próxima.

---

## 3. Mapa da pasta

```
Adobe/
  CLAUDE.md, AGENTS.md      este guia (AGENTS.md é só um ponteiro para outras IAs)
  COMO-TROCAR-DE-CONTA.md   passo a passo para o dono continuar em outra conta/computador
  CONTEXTO.md               detalhes técnicos de cada parte e de cada versão
  LEIA-ME.md                manual de uso
  sistema/                  O APP
    editor-pdf.html           a interface inteira (um HTML só, ~240 KB, JS puro, sem framework, sem build)
    motor.js                  motor do celular/site (MuPDF.js + pdf-lib + Tesseract.js), mesmas rotas do servidor
    servidor.py               motor do Windows: servidor HTTP local (PyMuPDF): /api/analyze, /api/apply, /api/ocr, /api/tool...
    ferramentas.py            as ~35 ferramentas (juntar, dividir, comprimir, comparar, proteger, PDF/A, assinar...)
    app.py                    entrada do .exe: liga o servidor e abre a janela própria (pywebview/WebView2)
    editor-pdf.spec           receita do PyInstaller        instalador.iss   receita do Inno Setup
    versao.txt                número da versão do Windows (o instalador, o app e a Loja leem daqui)
    lib/                      pdf.js, pdf-lib, MuPDF.js, Tesseract.js (tudo local: nada vem da internet)
    painel.py/.html, *.vbs, Abrir editor.bat   modo antigo (servidor na rede pelo painel); ainda funciona
  dados/tessdata/           idiomas do OCR (por, eng; o osd foi tirado em 19/10/2026 por não ser usado). config.json e registros.log são do modo antigo
  android/                  projeto Android (Java, WebView) + gerar-apk.ps1
    chave/                    CHAVE DE ASSINATURA DO APK. Nunca apagar, nunca publicar (ver seção 8)
  web/                      site: gerar-web.ps1, publicar-web.ps1, publicar-versao.ps1, novidades.json, privacidade.html, sw.js
  loja/                     Microsoft Store: gerar-msix.ps1, identidade.json, COMO-PUBLICAR.md, capturas/
  codigo/                   repositório público: publicar-codigo.ps1, README.md, LICENSE, TERCEIROS.md, .gitignore
  testes/                   bateria automática: rodar-testes.ps1 (ver seção 6)
  instalador/               SAÍDA: instalador .exe e APK gerados (não editar à mão)
  replica/                  anotações do começo do projeto (estudo das funções do Acrobat online). Só histórico
```

---

## 4a. Como o app chegou aqui (linha do tempo da construção)

1. **Estudo do Acrobat online** (`replica\recon.md`, `replica\features.csv`): lista das funções do editor da Adobe
   (trocar texto, assinar, marcar, organizar páginas) para decidir o que o app precisava ter. Nada da Adobe foi copiado.
2. **Editor no navegador** (`editor-pdf.html`): pdf.js mostra as páginas, pdf-lib grava objetos (texto, imagem,
   assinatura, marcações). Funcionava sozinho, no "modo básico" (o texto trocado só ficava coberto).
3. **Servidor Python com PyMuPDF** (`servidor.py`): "modo avançado", que apaga o texto antigo de verdade e reaproveita
   a fonte original. Depois veio o **painel** (`painel.py`) para ligar/desligar o servidor e usar na rede.
4. **Ferramentas** (`ferramentas.py`, estilo iLovePDF): juntar, dividir, comprimir, converter, OCR, PDF/A, assinatura A1...
5. **Android e site:** o `motor.js` refaz as rotas do servidor dentro da página (MuPDF.js), então a mesma tela roda
   no APK e no site (iPhone).
6. **Aplicativo do Windows (.exe):** PyInstaller + Inno Setup, janela própria (pywebview), abrir PDF com dois cliques,
   imprimir, recentes, recuperação de edições.
7. **Atualização automática** pelo site e releases do GitHub; instalador que "atualiza" em vez de duplicar.
8. **Microsoft Store** (MSIX) e **código aberto** (AGPL) com "Sobre e licenças" (versão 2.0).
9. **2.1–2.2.1:** PDF com senha, escaneado editável, textos/carimbos salvos, seleção múltipla, comparar lado a lado,
   barra mais limpa. Detalhes de cada versão no `CONTEXTO.md`.

## 4. Como foi feito e por quê (o raciocínio)

Estas decisões foram tomadas de propósito. Mantenha-as, a menos que o dono peça outra coisa.

1. **Uma tela só para tudo.** `sistema\editor-pdf.html` é a mesma interface no Windows, no Android e no site.
   Os scripts de geração só injetam uma marca no `<head>`: `window.APP_CELULAR` (APK), `window.APP_WEB` (site);
   sem marca = Windows. Corrigir algo na tela corrige nas quatro formas. Não crie telas separadas por plataforma.
2. **Dois motores com a mesma "API".** O editor sempre chama `api('/api/...')`. No Windows isso vai para o
   `servidor.py` (HTTP em 127.0.0.1); no celular/site vai para `MOTOR.chamar()` do `motor.js`, que imita as
   mesmas rotas e respostas. **Toda função nova de PDF precisa existir nos dois** (Python em `servidor.py`/`ferramentas.py`
   e JS em `motor.js`), com o mesmo formato de entrada e saída. Algumas ferramentas são só do Windows
   (Office→PDF, PDF→Word, PDF/A, certificado A1): a lista fica em `SO_COMPUTADOR` no editor.
3. **MuPDF porque apaga de verdade.** Trocar texto e tarja usam "redação" do MuPDF: o texto antigo sai do arquivo,
   não é só coberto. É o diferencial do app. Por isso o projeto é **AGPL** (MuPDF e Ghostscript são AGPL): o código
   tem de ficar público (`codigo\publicar-codigo.ps1` faz isso a cada versão) e o app mostra "Sobre e licenças".
4. **Tudo local e sem conta.** Bibliotecas em `sistema\lib`, OCR com os idiomas embutidos, nenhum servidor na
   internet. A única consulta externa é o `versao.json` do site, para avisar de atualização (a versão da Loja nem isso).
5. **Windows = servidor local + janela própria.** `app.py` liga o `servidor.py` numa thread (só 127.0.0.1, porta 8770
   ou outra livre) e abre uma janela WebView2 pelo pywebview (sem barra de navegador). O PDF trafega em **bytes**
   (`POST /api/doc` guarda e devolve um número; as chamadas seguintes mandam só o número), porque base64 em PDFs
   grandes era lento. O `soltar_filtro()` tira um filtro do pywebview que deixava envios grandes lentos.
6. **Atualização sem loja.** A versão do Windows está em `sistema\versao.txt`, a do Android no `android\app\build.gradle.kts`.
   O site publica `versao.json`; o app compara ao abrir e oferece "Atualizar agora" (Windows baixa o instalador e roda;
   Android abre o download do APK). Os arquivos ficam nas *releases* do GitHub `editorpdf/editorpdf.github.io`.
   O instalador detecta a versão instalada e mostra "Atualizar"/"Reinstalar", sem apagar os dados do usuário.
7. **Microsoft Store para tirar o aviso do SmartScreen** (o instalador não tem assinatura paga). O MSIX é o mesmo app,
   e dentro da Loja o app não mostra o próprio aviso de atualização (`LOJA` no `app.py`).
8. **Gerar fora do OneDrive.** A pasta do projeto está no OneDrive, que trava arquivos durante a sincronização. Por isso
   os builds e cópias de trabalho vão para `%TEMP%` e `%LOCALAPPDATA%` (ver seção 5). Não mude isso.
9. **Escaneado editável (2.1):** o OCR cria texto invisível sobre a imagem; ao editar, o app apaga os pixels da imagem
   naquela área, pinta a cor do papel (amostrada dos pixels) e escreve o texto novo na cor da tinta.
10. **PDF com senha (2.1):** pede a senha, abre uma cópia sem proteção e, ao salvar, protege de novo com a mesma senha.
11. **Desempenho:** antes de otimizar, meça com `testes\desempenho.py` (PDF de 300 páginas). Regras que já renderam muito:
    não pedir ao servidor nada de páginas longe da tela; não regravar o PDF no pdf-lib sem necessidade; não importar
    bibliotecas pesadas (pdf2docx/OpenCV) só para saber se existem; `garbage=3` só em PDFs pequenos.
12. **Estilo do código:** JS compacto (como o resto do `editor-pdf.html`), nomes e comentários em português,
    funções pequenas com nomes descritivos (`desbloquearAoAbrir`, `protegerDeNovo`, `oferecerOcrParaEditar`...).
    Siga o estilo do trecho vizinho. Os ids dos elementos (`bOpen`, `bSave`, `rail`, `right`...) são usados pelo JS.

---

## 5. Rotina para lançar uma versão (passo a passo exato)

Todos os comandos em PowerShell, a partir da pasta `Adobe`.

1. **Número da versão:** escreva o novo em `sistema\versao.txt` (ex.: `2.3`) e, no `android\app\build.gradle.kts`,
   aumente `versionCode` em 1 e ponha o mesmo `versionName`. Windows e Android andam com o mesmo número.
2. **Novidades:** `web\novidades.json` (`{"windows":[...],"android":[...]}`), frases curtas para o usuário.
3. **Testes:** `testes\rodar-testes.ps1` (tem de terminar com "RESULTADO: tudo certo").
4. **App do Windows** (rode dentro de `sistema`; a saída precisa de caminho curto, senão o PyMuPDF não carrega a DLL):
   ```
   cd sistema
   py -m PyInstaller editor-pdf.spec --noconfirm --distpath "$env:TEMP\epdf" --workpath "$env:TEMP\epdf-build"
   & "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" /Q "/DOrigem=$env:TEMP\epdf\Editor de PDF" instalador.iss
   ```
   Sai `instalador\Instalar Editor de PDF.exe`. Enquanto o Inno Setup grava, o arquivo fica travado (o Windows diz
   "outro programa está usando este arquivo") — é normal, espere terminar.
5. **APK:** `android\gerar-apk.ps1` → `instalador\Editor de PDF.apk`.
6. **Testar o pacote pronto:** `testes\rodar-testes.ps1 -Pacote` (o dono precisa estar com o Editor de PDF fechado:
   o app só aceita uma cópia aberta, e o teste fecha a dele). No `-Pacote` o motor do celular é pulado, porque o
   instalador do Windows não leva `lib\mupdf` nem `lib\tesseract`.
7. **Publicar** (pedir confirmação ao dono antes): `web\publicar-versao.ps1`. Ele envia o instalador e o APK para as
   releases do GitHub, publica o código-fonte (com a marcação `windows-X-android-Y`) e atualiza o site.
   Em 1–2 minutos `https://editorpdf.github.io/versao.json` mostra o número novo e os apps avisam os usuários.
8. **Microsoft Store** (separado, quando o dono pedir): `loja\gerar-msix.ps1` → `loja\Editor de PDF.msix`
   (120 MB; depois de enviado à Loja pode ser apagado, porque é gerado de novo a cada versão);
   no Partner Center: o produto → "Iniciar atualização" → Pacotes → arrastar o .msix (o dono arrasta; é grande demais
   para upload automático) → "Novidades nesta versão" na listagem → mostrar ao dono → "Enviar para certificação".
   Detalhes em `loja\COMO-PUBLICAR.md`. Só dá para enviar quando o envio anterior já saiu da certificação.
9. **Documentar:** acrescente a versão em `CONTEXTO.md`.

---

## 6. Testes

- **`testes\rodar-testes.ps1`** — bateria automática (44 itens em 18/10/2026): gera PDFs de amostra, testa o motor do
  Windows em Python (`servidor_testes.py`: troca de texto, tarja, OCR em escaneado, senha, comparar) e depois abre o app
  com o DevTools numa porta livre a partir da 9351 (a 9333 às vezes está ocupada por outros projetos do dono) e testa a interface (`editor_testes.js`) no motor do Windows e no motor do celular/site
  (`?motor=js`). Fecha o Editor de PDF aberto. Imagens para conferir a olho ficam em `%TEMP%\editorpdf-testes`.
- **Como testar uma coisa nova:** escreva o teste em `editor_testes.js` (interface) e/ou `servidor_testes.py` (motor),
  no mesmo formato `ok(condição, 'descrição')` / `confere(...)`. O `testes\cdp.py` roda qualquer JS na janela do app
  (`py testes\cdp.py js arquivo.js`), navega (`ir /?motor=js`) e tira foto (`foto saida.png`).
- **Cuidado:** o app rodado pelos testes usa **o mesmo perfil** do app instalado do dono (`%LOCALAPPDATA%\EditorPDF\webview`).
  Tudo que um teste gravar (recentes, assinaturas, textos salvos) aparece no app dele — apague no fim do teste.
  O botão "Restaurar o app" apaga os dados reais do dono: não use em teste.
- **Para rodar o app a partir do código:** `$env:EDITOR_PDF_TESSDATA="<Adobe>\dados\tessdata"; py sistema\app.py`
  (sem essa variável o OCR aparece desligado). Para depurar a janela: `$env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS="--remote-debugging-port=9333"`.
- **Android de verdade:** emulador `teste` (Android 14) em `%LOCALAPPDATA%\AndroidBuild\avd` (defina `ANDROID_AVD_HOME`
  para essa pasta). O APK de release não deixa depurar a WebView; teste por toques (adb) ou use o `?motor=js` no Windows,
  que é o mesmo código.
- **iPhone:** Playwright com WebKit (emulação do iPhone 13) abrindo o site gerado.

---

## 7. Contas e serviços (o que existe fora do computador)

| O quê | Onde | Observação |
| --- | --- | --- |
| GitHub | conta **k2locserv-collab**, organização **editorpdf** | login pelo GitHub CLI (`gh auth login`) |
| Site + downloads | repositório `editorpdf/editorpdf.github.io` (GitHub Pages, branch main) | gerado em `%LOCALAPPDATA%\EditorPDF-web\site` |
| Código-fonte | repositório `editorpdf/editor-pdf` (público, AGPL-3.0) | cópia de trabalho em `%LOCALAPPDATA%\EditorPDF-codigo\repo` |
| Microsoft Store | Partner Center, editor **TechMaster0202**, produto **Editor de PDF Fácil** (`9P5JP86G028L`) | identidade em `loja\identidade.json`; link https://apps.microsoft.com/detail/9P5JP86G028L |
| Google Play | não publicado | custa US$ 25 e exige 12 testadores por 14 dias; precisaria de AAB e sem o aviso de atualização próprio |

Os commits do Git usam a identidade `k2locserv-collab <343685101+k2locserv-collab@users.noreply.github.com>`
(e-mail "noreply" para não expor o e-mail pessoal). A IA nunca digita senhas: o dono faz os logins.

---

## 8. Armadilhas conhecidas

- **Chave do APK (`android\chave\`)**: sem ela não dá para atualizar o app Android de quem já instalou (teria de
  desinstalar e perder os dados). Ela fica só nesta pasta (e no backup do OneDrive). Nunca vai para o GitHub
  (o `publicar-codigo.ps1` bloqueia `.jks` e `chave.properties`).
- O `publicar-codigo.ps1` só publica os arquivos da lista `$lista`. Arquivo novo que deva ir para o código público
  tem de entrar nela. O `COMO-TROCAR-DE-CONTA.md` fica de fora de propósito (tem caminhos pessoais do computador).
- As cópias de trabalho do site (`%LOCALAPPDATA%\EditorPDF-web\site`) e do código (`%LOCALAPPDATA%\EditorPDF-codigo\repo`)
  ficam fora do OneDrive. Num computador novo elas não existem: `publicar-web.ps1` e `publicar-codigo.ps1` baixam
  (`gh repo clone`) sozinhos na primeira vez — só precisa do `gh auth login` feito.
- **Controle Inteligente de Aplicativos (Smart App Control) está LIGADO no PC do dono** (desde set/2026). Ele bloqueia
  executáveis sem assinatura digital que ainda não têm reputação — às vezes o `Editor de PDF.exe` recém-gerado é barrado
  ("Uma política de Controle de Aplicativo bloqueou este arquivo"; evento 3077 em Microsoft-Windows-CodeIntegrity/Operational).
  Não desligue nem contorne essa proteção. Se o pacote for bloqueado, teste a partir do código (`rodar-testes.ps1` sem
  `-Pacote`) e avise o dono. A solução de verdade é assinar o app (certificado de assinatura de código) ou instalar pela
  Microsoft Store, que é assinada pela Microsoft.
- Testar "Abrir junto com o Windows" a partir do código: grave temporariamente o valor `Editor de PDF` em
  `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` (qualquer texto), abra `py sistema\app.py --fundo` e use
  `testes\janela.py visivel|fechar <pid>`; apague o valor no fim. Antes, feche cópias antigas do app (o segundo processo
  só repassa o pedido para a cópia aberta e sai — isso confunde o teste).
- `py` é o Python 3.15 em `%LOCALAPPDATA%\Python\pythoncore-3.15-64`; o comando `python` pode cair no atalho da Microsoft Store.
- Scripts `.ps1` com acentos precisam ser salvos em **UTF-8 com BOM** (o PowerShell 5.1 lê errado sem o BOM).
- MakeAppx (MSIX) dá erro "configuração lado a lado" se rodar de dentro do LOCALAPPDATA: o script copia para o TEMP.
- O pacote MSIX não aceita o arquivo `[Content_Types].xml` do modelo do python-docx: o `.spec` tira essa pasta.
- PyMuPDF: o texto do OCR vem com `alpha` 0 (invisível); no MuPDF.js a fonte é `GlyphLessFont`. É assim que o app
  reconhece um bloco escaneado.
- Páginas giradas usam o modo básico para trocar texto (limite conhecido).

---

## 9. Ideias que ficaram para depois (pedidas pelo dono)

Manter negrito/itálico no meio da frase ao editar; editar texto em páginas giradas; criar/editar links e marcadores;
criar campos de formulário; assinatura em tela cheia no celular; publicar na Google Play.
Apple App Store: avaliada em 19/10/2026 e deixada de lado (US$ 99/ano, exige Mac, e a AGPL do MuPDF é incompatível com
os termos da App Store sem a licença comercial da Artifex). No iPhone, o caminho é o site com "Adicionar à Tela de Início".
O app não vai ter função de descobrir ou quebrar senha de PDF: o "Desbloquear PDF" exige a senha (só remove sem senha
as restrições de imprimir/copiar/editar de PDFs que abrem sem senha).

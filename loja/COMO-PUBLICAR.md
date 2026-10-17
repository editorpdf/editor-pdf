# Publicar o Editor de PDF na Microsoft Store

> Nome reservado: **Editor de PDF Fácil** (o "Editor de PDF" já era de outra pessoa). Store ID `9P5JP86G028L`,
> link https://apps.microsoft.com/detail/9P5JP86G028L. Identidade já em `identidade.json`.
> Primeiro envio (versão 1.9.0.0) mandado para certificação em 17/10/2026: público, gratuito, Produtividade,
> classificação Livre, política de privacidade em editorpdf.github.io/privacidade.html, justificativa do runFullTrust nas Opções de envio.

## 1. Conta (uma vez só)
1. Entre em https://storedeveloper.microsoft.com com a sua conta Microsoft.
2. Escolha **Individual (pessoa física)**. É gratuito; pede um documento com foto e uma selfie.
3. Depois da verificação, abra o **Partner Center** (https://partner.microsoft.com/dashboard/apps-and-games/overview).

## 2. Reservar o nome
1. **Aplicativos e jogos → Novo produto → Aplicativo MSIX ou PWA**.
2. Reserve o nome: **Editor de PDF** (se estiver ocupado, por exemplo: "Editor de PDF Fácil", "Editor de PDF BR").
3. Abra o produto → **Gerenciamento do produto → Identidade do produto**. Copie:
   - **Package/Identity/Name**
   - **Package/Identity/Publisher** (começa com `CN=`)
   - **Package/Properties/PublisherDisplayName**
4. Mande esses três valores para o Claude (ou cole em `loja\identidade.json`).

## 3. Gerar o pacote com a identidade certa
```
py -m PyInstaller sistema\editor-pdf.spec --noconfirm --distpath %TEMP%\epdf --workpath %TEMP%\epdf-build
loja\gerar-msix.ps1
```
Sai `loja\Editor de PDF.msix`. A Loja assina o pacote; não precisa de certificado.

## 4. Envio (Partner Center → Iniciar envio)
- **Preços e disponibilidade:** Gratuito. Visibilidade: "Público" ou, para mandar só para quem quiser, "Privado / oculto" (só quem tem o link encontra).
- **Propriedades:** categoria **Produtividade**. Política de privacidade: `https://editorpdf.github.io/privacidade.html`. Site: `https://editorpdf.github.io`.
  - "Este produto acessa, coleta ou transmite informações pessoais?" → **Não**.
- **Classificação etária:** responda o questionário; não há violência, chat, compras nem conteúdo gerado por outros usuários → Livre.
- **Pacotes:** envie `loja\Editor de PDF.msix`.
- **Listagem da Loja (Português do Brasil):** copie os textos abaixo e envie as imagens de `loja\capturas` (1920×1080).
- **Notas para a certificação:** copie o texto do fim deste arquivo.

A revisão costuma levar de 1 a 3 dias úteis.

## 5. Atualizações depois
1. Aumente o número em `sistema\versao.txt` (ex.: 2.0).
2. Gere o app e o pacote (passo 3).
3. Partner Center → o produto → **Atualizar** → Pacotes → envie o novo `.msix` → Enviar para a Loja.
Quem instalou pela Loja recebe sozinho. (O instalador `.exe` e o site continuam funcionando como antes, com `web\publicar-versao.ps1`.)

---

## Textos da listagem

**Nome:** Editor de PDF

**Descrição curta (até 100 caracteres):**
Edite texto, assine, junte, converta e organize PDFs. Tudo no seu computador, sem internet.

**Descrição:**
Edite seus PDFs de verdade, sem enviar nada para a internet.

Troque o texto do PDF direto na página, mantendo a fonte e a posição originais. Assine documentos, preencha formulários, apague dados sigilosos com tarja que remove o texto de verdade e organize as páginas como quiser.

O que dá para fazer:
• Editar o texto existente do PDF, inclusive células de tabela
• Assinar: desenhar, digitar, usar uma imagem ou um certificado digital A1
• Preencher formulários
• Realçar, sublinhar, desenhar, adicionar notas, imagens e carimbos
• Tarja: esconder CPF, telefone, e-mail e outros dados, removendo o texto de verdade
• Buscar e substituir em todas as páginas
• Juntar, dividir, extrair, girar, apagar e reordenar páginas
• Converter PDF para Word; imagens, Word, Excel e PowerPoint para PDF (estes três usam o Microsoft Office instalado)
• Reconhecer texto de PDF escaneado (OCR), em português e inglês
• Comprimir, numerar páginas, marca d'água, cabeçalho e rodapé, proteger com senha
• Converter para PDF/A (arquivamento)
• Imprimir com as suas edições
• Selecionar e copiar texto, links clicáveis e sumário
• Arquivos recentes e recuperação de edições não salvas
• Tema claro e escuro

Privacidade: o app não tem conta e não envia seus arquivos para lugar nenhum. Tudo é processado no seu computador.

Código aberto (licença AGPL-3.0): https://github.com/editorpdf/editor-pdf

**Recursos do produto (um por linha):**
Editar o texto do PDF mantendo a fonte original
Assinatura desenhada, digitada ou com certificado A1
Tarja que remove dados de verdade
Juntar, dividir e organizar páginas
PDF para Word e Office para PDF
OCR para PDF escaneado
Funciona sem internet, sem enviar arquivos

**Palavras-chave:** pdf, editar pdf, assinar pdf, juntar pdf, pdf para word, ocr

**Requisitos:** Windows 10 (1809) ou 11, 64 bits. Converter Word/Excel/PowerPoint para PDF usa o Microsoft Office instalado.

---

## Notas para a certificação (copiar no campo "Notas para a certificação")

Editor de PDF is a desktop PDF editor (Python + WebView2). It needs runFullTrust because it is a Win32 desktop app: it starts a local HTTP engine bound only to 127.0.0.1 (port 8770, or a free port) that is used exclusively by its own WebView2 window, and it runs a bundled Ghostscript executable for PDF/A conversion. It does not accept network connections from other computers and does not collect or transmit user data. The app does not update itself when installed from the Store (updates come only from the Store). No account or login is needed. To test: open the app, click "Abrir…" and choose any PDF, then use "Editar texto" to change text and "Salvar PDF" to save.

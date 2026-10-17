# Editor de PDF

> **Desde a versão 1.3:** use o app instalado (atalho "Editor de PDF") no computador e o APK no celular. O servidor do painel ficou desligado; ele só é necessário para **compartilhar na rede** (outras pessoas usando pelo navegador). A pasta `sistema` continua sendo a fonte usada para gerar o instalador e o APK: não apague.

## Como abrir

- **Pelo painel (recomendado):** duplo clique em **`Painel Editor de PDF`** (o atalho na pasta principal). O painel abre em menos de 1 segundo, numa janela própria, e mostra ao vivo se o servidor está ligado, os endereços (para copiar), os recursos disponíveis (OCR, Word, Office...) e os registros. Dá para ligar e desligar o servidor, abrir o editor, **compartilhar na rede** e iniciar junto com o Windows. Fechar a janela do painel não desliga o servidor. Precisa do Python e das bibliotecas (`py -m pip install pymupdf pdf2docx python-docx pillow openpyxl python-pptx`); a aba "Verificar instalação" confere.
- **Sem o painel:** `sistema\Abrir editor.bat` liga o servidor numa janela preta (só este computador).
- **Modo básico:** abrir `sistema\editor-pdf.html` direto. Funciona, mas a troca de texto só cobre o trecho antigo.

## Mandar para outra pessoa

Mande o arquivo **`instalador\Instalar Editor de PDF.exe`** (por WhatsApp, Google Drive, pendrive...). A pessoa dá dois cliques, avança e pronto: aparece "Editor de PDF" na área de trabalho e no menu Iniciar. Não precisa de Python nem de internet, e tudo funciona (troca de texto, tarja, OCR, Word, ferramentas). Os PDFs ficam no computador dela.

**Atualizações automáticas (desde a 1.7):** quem já tem o app recebe o aviso "Nova versão disponível" ao abrir e atualiza com um clique. Para lançar uma versão: aumente o número em `sistema\versao.txt` (Windows) e/ou em `android\app\build.gradle.kts` (Android), gere o instalador e o APK, escreva as novidades em `web\novidades.json` e rode `web\publicar-versao.ps1`. Downloads diretos: https://github.com/editorpdf/editorpdf.github.io/releases/latest

**Código aberto (licença AGPL):** o app usa MuPDF e Ghostscript, que exigem que o código-fonte fique público. Ele está em https://github.com/editorpdf/editor-pdf, e o `publicar-versao.ps1` envia o código de cada versão sozinho (`codigo\publicar-codigo.ps1`, que copia só uma lista fixa de arquivos: a chave do APK, os registros e os instaladores nunca vão). No app, "Sobre e licenças" fica no rodapé da tela inicial.

Também dá para mandar o instalador de novo. Se o app já estiver instalado, o instalador mostra a tela "Atualizar" com as duas versões (por exemplo 1.3 → 1.4), não pergunta as opções de novo e troca só os arquivos, sem duplicar o app. Se a versão for a mesma, aparece "Reinstalar". Se a versão instalada for mais nova, ele avisa antes. Ao gerar uma versão nova, aumente o `Versao` no `instalador.iss`.

- Na primeira vez o Windows mostra "O Windows protegeu o computador", porque o instalador não tem assinatura digital paga. Clique em **Mais informações** e **Executar assim mesmo**.
- Precisa de Windows 10 ou 11. Desde a versão 1.5 abre numa janela própria (usa o WebView2, que já vem no Windows), e "Salvar" pergunta onde guardar o arquivo. Word/Excel/PowerPoint para PDF só funciona se ela tiver o Microsoft Office.
- Para desinstalar: Configurações > Aplicativos > Editor de PDF.
- **Abrir PDFs com dois cliques:** no instalador, deixe marcado "Usar o Editor de PDF para abrir arquivos PDF". No fim, ele abre a tela de Aplicativos padrão do Windows: escolha o Editor de PDF para ".pdf" (o Windows não deixa nenhum programa se tornar o padrão sozinho). Também dá para clicar com o botão direito num PDF > Abrir com > Editor de PDF. Se o app já estiver aberto, o PDF abre numa janela nova.

## No iPhone, iPad ou qualquer navegador (sem instalar)

Endereço: **https://editorpdf.github.io/**

- No iPhone, abra no **Safari**, toque em **Compartilhar > Adicionar à Tela de Início**: aparece o ícone do Editor de PDF e ele abre em tela cheia, como um app.
- Os PDFs são processados no próprio aparelho: nada é enviado para o GitHub nem para lugar nenhum. O site só entrega a página.
- Depois do primeiro uso, funciona sem internet (o OCR precisa ter sido usado uma vez com internet para guardar os idiomas).
- Para abrir um PDF: botão de pasta > escolha em Arquivos. Para salvar: o app abre a janela de compartilhar do iOS; escolha **Salvar em Arquivos** (ou WhatsApp, e-mail...).
- Mesmas funções do APK (sem Word/Excel/PowerPoint, PDF/A e certificado). Não dá para abrir um PDF direto do WhatsApp no app da Tela de Início (limite do iPhone): salve em Arquivos e abra por lá.
- Para atualizar o site depois de mudanças: rode `web\publicar-web.ps1`.

## No celular (Android)

Mande o arquivo **`instalador\Editor de PDF.apk`** (22 MB) para o celular (WhatsApp como documento, Drive, cabo USB). Ao tocar nele, o Android pede para permitir a instalação de "fontes desconhecidas" para o app que abriu o arquivo (WhatsApp, Arquivos...): permita só para essa instalação. O app não está na Play Store, então o Play Protect pode avisar que é um app desconhecido: toque em "Instalar mesmo assim".

- Funciona sem internet e sem computador: o motor de PDF roda dentro do celular.
- Tem: editar texto de verdade, tarja que apaga, buscar e substituir, tarja automática, OCR (português e inglês), formulários, carimbos, assinatura desenhada, organizar páginas e as ferramentas (juntar, dividir, comprimir, marca d'água, numerar, cabeçalho, proteger, imagens...).
- Não tem (só no computador): converter para Word, Excel e PowerPoint, Office/HTML para PDF, PDF/A e assinatura com certificado digital.
- Os arquivos salvos vão para **Downloads/Editor de PDF**; depois de salvar dá para compartilhar (WhatsApp, e-mail, Drive).
- Para abrir um PDF que chegou no WhatsApp ou no e-mail: toque no arquivo > "Abrir com" > Editor de PDF.
- No celular o OCR leva alguns segundos por página, e PDFs muito grandes podem ficar lentos.
- Precisa de Android 8 ou mais novo. Não existe versão para iPhone.
- **Atualizações:** para instalar uma versão nova por cima, o APK precisa ser assinado com a mesma chave, que está em `android\chave`. Não apague essa pasta.

## Converter PDF para Word

Com o PDF aberto: **Exportar > Converter para Word** (ou o cartão "Converter para Word" na tela inicial). Escolha o documento inteiro ou só as páginas selecionadas. O arquivo `.docx` vai para a pasta de downloads. Se você tiver alterações ainda não salvas, elas entram na conversão.

- Mantém parágrafos, fontes, cores, tabelas e imagens de PDFs que têm texto.
- A aparência no Word nunca fica idêntica ao PDF (quebras de linha e espaçamentos podem mudar), principalmente em PDFs com layout complexo, várias colunas ou texto sobre imagens.
- **PDF escaneado** (só imagem): o app reconhece o texto por OCR e gera um Word só com o texto, sem o layout e as imagens originais. Revise o resultado.
- Só funciona no modo avançado (pelo painel). Outras pessoas da rede também podem usar.

## Reconhecer texto (OCR)

**Exportar > Reconhecer texto (OCR)** (ou o cartão na tela inicial) deixa o PDF escaneado pesquisável e copiável: o app cria uma camada de texto invisível sobre a imagem. Escolha o documento inteiro ou só as páginas selecionadas, o idioma (português e inglês, só português, só inglês) e se pula as páginas que já têm texto. Dá para desfazer com Ctrl+Z.

- Os dados de idioma ficam em `dados\tessdata` (`por`, `eng`, `osd`, baixados de github.com/tesseract-ocr/tessdata_fast). Para outro idioma, coloque o arquivo `xxx.traineddata` nessa pasta.
- As páginas reconhecidas viram imagens de 300 dpi com o texto por baixo, então o arquivo cresce (cerca de 200 KB por página nos testes). Demora cerca de 1 segundo por página.
- Escaneamentos tortos, borrados ou com letra pequena erram mais. O texto reconhecido não é perfeito: confira nomes, números e valores.
- Depois do OCR, "Editar texto" muda o texto invisível, mas a imagem original continua mostrando o texto antigo. Para corrigir um escaneado, use a tarja ou adicione texto por cima.

## Ferramentas (estilo iLovePDF)

Na tela inicial (rolando para baixo) ou no botão **Ferramentas** do topo. Cada ferramenta aceita um ou vários arquivos (arraste ou escolha), mostra as opções, e baixa o resultado (vários arquivos vêm num `.zip`). Com um PDF aberto no editor, use o botão "Usar o PDF aberto".

| Grupo | Ferramentas |
| --- | --- |
| Organizar | Juntar, Dividir (por intervalos, a cada N páginas ou uma por arquivo), Remover páginas, Extrair páginas, Girar, Cortar (margens ou automático) |
| Otimizar | Comprimir (3 níveis), Reparar, OCR |
| Editar e segurança | Marca d'água (texto ou imagem), Numerar páginas, Proteger com senha, Desbloquear (só com a senha), Comparar dois PDFs |
| Converter para PDF | Imagem para PDF, Word/Excel/PowerPoint para PDF, HTML para PDF |
| Converter de PDF | PDF para JPG/PNG, Word, Excel, PowerPoint e texto |

Observações:
- **Word/Excel/PowerPoint para PDF** usa o Microsoft Office instalado neste computador (macros desativadas). **HTML para PDF** usa o Edge ou o Chrome; para páginas da web só aceita endereços públicos. Por segurança, essas duas **só funcionam no próprio computador do servidor**, não para quem acessa pela rede.
- **PDF para Excel** acha tabelas desenhadas no PDF e converte números como `1.234,56` em números do Excel; tabelas sem linhas ou muito irregulares podem sair incompletas. Sem tabelas, coloca o texto, uma linha por célula.
- **PDF para PowerPoint:** "imagem" deixa os slides idênticos (não editáveis); "texto" cria caixas de texto editáveis, sem as imagens.
- **Comprimir** pode reduzir muito PDFs com fotos, mas pouco os que já são só texto. Se o resultado não ficar menor, o app devolve o original.
- **Desbloquear** não quebra senhas: precisa da senha. Em PDFs que abrem sem senha mas têm restrições (imprimir, copiar), remove as restrições.
- **Cortar** esconde o que ficou fora da área, mas o conteúdo continua dentro do arquivo.
- **Numerar, marca d'água e comparar** usam fontes padrão do PDF quando o texto cabe nelas (acentos do português incluídos).

## Novidades (formulários, carimbos, busca, grade, imagens, PDF/A, certificado)

- **Preencher formulários:** PDFs com campos (requisições, fichas) mostram os campos em azul; é só clicar e digitar, marcar caixas ou escolher na lista. No painel da direita, "Travar o formulário ao salvar" transforma as respostas em parte da página. Juntar, girar ou reordenar páginas depois de preencher grava as respostas e remove os campos.
- **Carimbo** (barra da esquerda): Aprovado, Recebido, Conferido, Pago, Reprovado… ou um texto seu, com data e nome. Entra no meio da página; arraste para o lugar.
- **Buscar e substituir** (lupa no topo ou Ctrl+F): destaca as ocorrências e "Substituir tudo" troca em todas as páginas, com a mesma fonte, tamanho e cor da linha (Ctrl+Z desfaz). Linhas que misturam estilos ficam com um estilo só; texto girado não é trocado.
- **Tarja automática** (Exportar > Tarja automática, ou o botão no painel da ferramenta Tarja): procura CPF, CNPJ, RG, e-mail, telefone, CEP, placa, datas e palavras suas e marca tarjas para você conferir; ao salvar, o conteúdo é apagado de verdade. PDF escaneado precisa de OCR antes.
- **Organizar** (topo): todas as páginas em grade, grandes; selecione (Ctrl/Shift), arraste para reordenar (as selecionadas vão juntas), gire, duplique, apague, extraia ou junte outro PDF.
- **Cabeçalho e rodapé** (Ferramentas): textos à esquerda, no centro e à direita, com {n}, {total}, {data} e {arquivo}, e logotipo.
- **Imagens** (Ferramentas > Imagens): comprimir, redimensionar, recortar, converter (JPG, PNG, WEBP, BMP, GIF, TIFF) e girar, várias de uma vez.
- **Converter para PDF/A** (Ferramentas > Otimizar): PDF/A-2b (ou 1b/3b) com o Ghostscript. Não validei os arquivos num validador oficial (veraPDF); confira no sistema que vai receber.
- **Assinatura digital com certificado A1** (.pfx/.p12): assinatura com validade jurídica, com carimbo visível opcional. Só funciona no computador do servidor (o certificado e a senha não passam pela rede). Certificado A3 (token/cartão) não é suportado. A data vem do relógio do computador (sem carimbo de tempo de servidor). Qualquer alteração depois de assinar invalida a assinatura.

## Visual

Tela inicial com os atalhos (editar, converter, juntar, organizar, assinar, tarja), barra lateral de ferramentas, painel de páginas e de propriedades que dá para esconder, barra de status com zoom, e tema claro/escuro (botão da lua/sol no topo).

## Compartilhar com outras pessoas

1. No painel, marque **"Compartilhar na rede"**. O servidor reinicia aceitando outros computadores da mesma rede.
2. Se o Windows perguntar sobre o Firewall, permita em **redes privadas**.
3. Clique em **"Copiar endereço da rede"** e mande o endereço (algo como `http://192.168.1.8:8768/`). Quem receber abre no navegador, sem instalar nada.
4. **Não há senha.** Quem estiver na sua rede e souber o endereço usa o editor. Desmarque a caixa quando terminar. O seu computador precisa ficar ligado e com o servidor ligado.

O servidor não guarda os PDFs: cada arquivo é processado na memória e devolvido. O registro (`dados\registros.log`) guarda só data, endereço de quem pediu, página e tamanho.

O PDF nunca sai do seu computador. O modo avançado também carrega duas bibliotecas de um CDN (precisa de internet).

O selo no topo mostra em que modo você está ("Modo avançado" ou "Modo básico").

## Diferença entre os modos

| | Modo avançado | Modo básico |
| --- | --- | --- |
| Trocar texto | apaga o texto antigo de verdade do arquivo | cobre o antigo; ele continua dentro do arquivo |
| Fonte | reaproveita a do PDF quando tem as letras; senão Arial, Times ou Courier | Helvetica, Times ou Courier |
| Parágrafos | edita o parágrafo inteiro, com quebra de linha automática | uma linha por vez |
| Tarja (redação) | remove texto, pixels de imagem e desenhos sob a tarja | só cobre com um retângulo preto |

## Como usar

1. **Abrir:** botão "Abrir…" ou arraste o PDF para a tela.
2. **Trocar texto:** ferramenta "Editar texto", clique no texto (no modo avançado, o parágrafo inteiro). Digite e aperte Enter; Esc cancela. Apague tudo para remover o trecho.
3. **Tarja:** ferramenta "Tarja", arraste sobre o que quer apagar de verdade. Vale também para dados sigilosos, **só no modo avançado**.
4. **Adicionar:** "Texto", "Imagem", "Assinar" (desenhar, digitar ou enviar imagem), "Nota".
5. **Marcar:** "Realçar", "Sublinhar", "Riscar", "Desenhar", "Retângulo", "Elipse", "Linha".
6. **Mover e ajustar:** "Selecionar", clique no objeto e arraste; a bolinha azul muda o tamanho. O painel da direita muda fonte, tamanho, cor e espessura. Delete apaga; setas movem.
7. **Páginas:** painel da esquerda. Clique para selecionar (Ctrl ou Shift para várias), arraste para reordenar, e use os botões para girar, duplicar, inserir página em branco, extrair, juntar outro PDF e apagar.
8. **Desfazer/refazer:** Ctrl+Z e Ctrl+Y. **Salvar:** "Salvar PDF" ou Ctrl+S (baixa `nome-editado.pdf`). As trocas de texto só são gravadas no arquivo ao salvar.

## Limites

- Só texto horizontal é editável. Páginas giradas usam o modo básico para trocar texto.
- Se o novo texto tiver letras que a fonte não tem (por exemplo emojis), elas viram vazio ou "?" e o app avisa.
- Um bloco que mistura estilos (negrito no meio da frase, cores diferentes) recebe um estilo só ao ser editado; o app avisa.
- Sem reflow entre blocos ou páginas, e sem OCR: PDF escaneado não tem texto para editar. PDF com senha não abre.
- A fonte exata do original só é reaproveitada quando o arquivo tem todas as letras novas. Fontes "subset" (só as letras usadas) costumam não ter, e aí entra uma fonte parecida do Windows. O Acrobat tem o mesmo limite.

## Testes feitos (2026-10-15, Chromium, PDFs de exemplo)

- **Servidor (Python):** leitura de blocos, troca de texto, parágrafo reescrito com quebra de linha, tarja; confirmado que o texto antigo **não aparece mais** na extração de texto do arquivo e que a faixa de fundo colorida foi preservada; reaproveitamento da fonte original embutida.
- **Editor no navegador:** troca de linha, parágrafo e remoção de trecho pelo fluxo real, salvando e reabrindo; tudo o que foi testado no modo básico (objetos, assinaturas, páginas, desfazer/refazer, página girada).
- **Não testei:** PDFs reais grandes ou com fontes incomuns, texto em colunas, tabelas complexas, PDFs escaneados, celular, Safari, Firefox, leitor de tela e arrastar com o mouse de verdade (usei eventos de script). Também não testei abrir pelo `Abrir editor.bat` com duplo clique (rodei o `servidor.py` direto).

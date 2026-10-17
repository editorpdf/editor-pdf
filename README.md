# Editor de PDF Fácil

Editor de PDF gratuito para Windows, Android e navegador (iPhone, iPad, qualquer computador).
Edita o texto existente do PDF, assina, preenche formulários, aplica tarja que remove o texto de verdade,
organiza páginas, converte para Word e de Office/imagens para PDF, reconhece texto (OCR) e converte para PDF/A.
Tudo é processado no próprio aparelho: nada é enviado para servidor nenhum.

- Site e versão para navegador: https://editorpdf.github.io
- Microsoft Store: https://apps.microsoft.com/detail/9P5JP86G028L
- Instalador do Windows e APK do Android: [versões](https://github.com/editorpdf/editorpdf.github.io/releases/latest)
- Política de privacidade: https://editorpdf.github.io/privacidade.html

## Licença

Copyright (C) 2026 TechMaster0202 (editorpdf)

Este programa é software livre: você pode redistribuí-lo e/ou modificá-lo nos termos da
**GNU Affero General Public License**, publicada pela Free Software Foundation, versão 3 ou
(a seu critério) qualquer versão posterior. Veja [LICENSE](LICENSE).

Ele é distribuído na esperança de ser útil, mas **SEM NENHUMA GARANTIA**, nem mesmo a garantia
implícita de COMERCIALIZAÇÃO ou de ADEQUAÇÃO A UM FIM ESPECÍFICO.

O app usa MuPDF, PyMuPDF, MuPDF.js e Ghostscript, da Artifex Software, que também são AGPL.
Os demais componentes e as licenças deles estão em [TERCEIROS.md](TERCEIROS.md).

A licença não dá direito de usar o nome "Editor de PDF Fácil" nem o ícone (AGPL, seção 7e):
quem distribuir uma versão modificada deve usar outro nome, para não confundir quem usa.

## Como o código está organizado

| Pasta | O que tem |
| --- | --- |
| `sistema/` | O app do Windows: `app.py` (janela própria com WebView2), `servidor.py` e `ferramentas.py` (motor com PyMuPDF, servido só em 127.0.0.1), `editor-pdf.html` (a interface, a mesma em todas as versões), `motor.js` (motor do celular e do site, com MuPDF.js), `lib/` (bibliotecas JavaScript), `editor-pdf.spec` (PyInstaller) e `instalador.iss` (Inno Setup). |
| `android/` | App Android: um WebView que carrega a interface e o `motor.js`. `gerar-apk.ps1` gera o APK. |
| `web/` | Scripts que montam e publicam o site (`gerar-web.ps1`, `publicar-web.ps1`) e as versões (`publicar-versao.ps1`). |
| `loja/` | Pacote MSIX da Microsoft Store (`gerar-msix.ps1`) e o guia de publicação. |
| `dados/tessdata/` | Dados de OCR do Tesseract (português, inglês e orientação). |
| `LEIA-ME.md`, `CONTEXTO.md` | Manual de uso e notas técnicas. |

## Como gerar

**Windows** (Python 3, Ghostscript instalado em `C:\Program Files\gs` e Inno Setup 6):

```
py -m pip install pymupdf pywebview pdf2docx python-docx python-pptx openpyxl pyhanko pillow pyinstaller
cd sistema
py -m PyInstaller editor-pdf.spec --noconfirm
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" instalador.iss
```

Para testar sem empacotar: `py sistema\app.py`.

**Android** (JDK 17+, Android SDK e Gradle em `%LOCALAPPDATA%\AndroidBuild`): `android\gerar-apk.ps1`.
Na primeira vez o script cria uma chave de assinatura nova em `android\chave` (a chave das versões oficiais não faz parte do código).

**Site:** `web\gerar-web.ps1` monta a pasta do site em `%LOCALAPPDATA%\EditorPDF-web\site`.

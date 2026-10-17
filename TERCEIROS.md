# Componentes de terceiros

O Editor de PDF Fácil usa os componentes abaixo. Cada um continua sob a licença do seu autor.

| Componente | Onde é usado | Autor | Licença |
| --- | --- | --- | --- |
| [MuPDF](https://mupdf.com) / [PyMuPDF](https://github.com/pymupdf/PyMuPDF) | Motor do Windows | Artifex Software | AGPL-3.0 |
| [MuPDF.js](https://github.com/ArtifexSoftware/mupdf.js) (`sistema/lib/mupdf`) | Motor do Android e do site | Artifex Software | AGPL-3.0 |
| [Ghostscript](https://www.ghostscript.com) | Conversão para PDF/A (Windows) | Artifex Software | AGPL-3.0 |
| [PDF.js](https://mozilla.github.io/pdf.js/) (`sistema/lib/pdf*.js`) | Mostrar as páginas, texto selecionável | Mozilla | Apache-2.0 |
| [pdf-lib](https://pdf-lib.js.org) (`sistema/lib/pdf-lib.min.js`) | Gravar edições no modo simples | Andrew Dillon | MIT |
| [Tesseract.js](https://github.com/naptha/tesseract.js) (`sistema/lib/tesseract`) e [dados do Tesseract](https://github.com/tesseract-ocr/tessdata_fast) | OCR | Google, Jerome Wu e colaboradores | Apache-2.0 |
| [pywebview](https://pywebview.flowrl.com) | Janela do Windows | Roman Sirokov | BSD-3-Clause |
| [pythonnet](https://github.com/pythonnet/pythonnet) | Ponte com o WebView2 | .NET Foundation | MIT |
| [pdf2docx](https://github.com/ArtifexSoftware/pdf2docx) | PDF para Word | Artifex Software e colaboradores | MIT |
| [python-docx](https://github.com/python-openxml/python-docx), [python-pptx](https://github.com/scanny/python-pptx) | Word e PowerPoint | Steve Canny | MIT |
| [openpyxl](https://openpyxl.readthedocs.io) | PDF para Excel | Eric Gazoni, Charlie Clark | MIT |
| [pyHanko](https://github.com/MatthiasValvekens/pyHanko) | Assinatura digital com certificado A1 | Matthias Valvekens | MIT |
| [Pillow](https://python-pillow.org) | Imagens | Jeffrey A. Clark e colaboradores | MIT-CMU |
| [OpenCV](https://opencv.org) (headless) | Usado pelo pdf2docx | OpenCV | Apache-2.0 |
| [NumPy](https://numpy.org) | Usado pelo pdf2docx e OpenCV | NumPy Developers | BSD-3-Clause |
| [Python](https://www.python.org) | Linguagem do app do Windows | Python Software Foundation | PSF-2.0 |
| [PyInstaller](https://pyinstaller.org) | Empacotar o app do Windows | PyInstaller Development Team | GPL-2.0 com exceção para o carregador |
| [AndroidX WebKit e Core](https://developer.android.com/jetpack/androidx) | App Android | Google | Apache-2.0 |
| [Microsoft Edge WebView2](https://developer.microsoft.com/microsoft-edge/webview2/) | Janela do Windows (já vem no Windows) | Microsoft | Licença do WebView2 Runtime |

O texto da licença AGPL-3.0 está em [LICENSE](LICENSE). Os textos das demais licenças estão nos sites de cada projeto;
o do MuPDF.js também está em `sistema/lib/mupdf/LICENSE`, e o do Ghostscript vai junto no app do Windows (pasta `gs`).

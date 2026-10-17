# Empacota o Editor de PDF como aplicativo (pasta com "Editor de PDF.exe").
# Gerar:  py -m PyInstaller editor-pdf.spec --noconfirm --distpath <saida> --workpath <temporario>
import glob
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

SIS = os.path.abspath(".")
TESS = os.path.join(os.path.dirname(SIS), "dados", "tessdata")
# Ghostscript (PDF/A): só o executável, a DLL (que já traz os recursos internos), os perfis de cor e a licença
GS = sorted(glob.glob(os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "gs", "gs*")))[-1]

datas = [
    ("editor-pdf.html", "."),
    # só as bibliotecas da página; o motor do celular (lib/mupdf, lib/tesseract) não é usado no Windows
    ("lib/pdf.min.js", "lib"), ("lib/pdf.worker.min.js", "lib"), ("lib/pdf-lib.min.js", "lib"),
    ("icone.ico", "."), ("versao.txt", "."),
    (TESS, "tessdata"),
    (os.path.join(GS, "bin", "gswin64c.exe"), "gs/bin"),
    (os.path.join(GS, "bin", "gsdll64.dll"), "gs/bin"),
    (os.path.join(GS, "iccprofiles"), "gs/iccprofiles"),
    (os.path.join(GS, "lib"), "gs/lib"),
]
for lic in ("COPYING", "LICENSE"):
    p = os.path.join(GS, "doc", lic)
    if os.path.exists(p):
        datas.append((p, "gs"))
for pacote in ("docx", "pptx", "openpyxl", "pdf2docx", "pyhanko", "pyhanko_certvalidator"):
    datas += collect_data_files(pacote)
# a pasta de origem do modelo do python-docx não é usada (ele usa o default.docx) e tem um arquivo
# "[Content_Types].xml", nome proibido dentro de um pacote da Microsoft Store
datas = [d for d in datas if "default-docx-template" not in d[0].replace("\\", "/")]

a = Analysis(
    ["app.py"],
    pathex=[SIS],
    datas=datas,
    hiddenimports=["servidor", "ferramentas", "pdf2docx", "docx", "pptx", "openpyxl", "PIL.Image",
                   "webview", "webview.platforms.winforms", "webview.platforms.edgechromium", "clr"]
                  + collect_submodules("pyhanko", filter=lambda n: ".cli" not in n and "opentype" not in n)
                  + collect_submodules("pyhanko_certvalidator"),
    excludes=["tkinter", "matplotlib", "IPython", "pytest"],
)
# o OpenCV (usado pelo pdf2docx para achar desenhos e girar imagens) traz o FFmpeg para vídeo, que o app não usa: 29 MB a menos
a.binaries = [b for b in a.binaries if "opencv_videoio_ffmpeg" not in b[0].lower()]
# (o gancho do PyInstaller para o docx também inclui a pasta do modelo: tira aqui)
a.datas = [d for d in a.datas if "default-docx-template" not in d[0].replace("\\", "/")]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Editor de PDF", icon="icone.ico",
          console=False, upx=False, version=None)
coll = COLLECT(exe, a.binaries, a.datas, name="Editor de PDF", upx=False)

"""Testes do motor do Windows (servidor.py e ferramentas.py), sem abrir janela.

Rode a partir da pasta testes:  py servidor_testes.py [pasta-das-amostras]
Precisa de EDITOR_PDF_TESSDATA apontando para Adobe\\dados\\tessdata (o rodar-testes.ps1 já define).
Imprime OK/FALHOU por item e sai com código 1 se algo falhar.
"""
import base64
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "sistema"))
import pymupdf  # noqa: E402
import servidor  # noqa: E402
import ferramentas  # noqa: E402

pasta = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ["TEMP"], "editorpdf-testes")
falhas = 0


def confere(cond, msg):
    global falhas
    print(("OK      " if cond else "FALHOU  ") + msg)
    falhas += 0 if cond else 1


def texto(dados, i=0):
    return pymupdf.open(stream=dados, filetype="pdf")[i].get_text()


# 1) troca de texto comum e tarja
d = pymupdf.open()
p = d.new_page()
p.insert_text((72, 100), "Contrato de prestacao de servicos", fontsize=16, fontname="tiro")
p.insert_text((72, 140), "Valor mensal: R$ 3.000,00", fontsize=12)
src = d.tobytes()
blocos = servidor.analyze(src, 0)["blocks"]
confere(len(blocos) == 2 and not any(b.get("ocr") for b in blocos), "analyze acha os 2 blocos de texto (sem marcar como OCR)")
b = blocos[1]
op = {"page": 0, "kind": "rep", "bbox": b["bbox"], "origin": b["origin"], "text": "Valor mensal: R$ 4.500,00", "size": b["size"], "color": b["color"],
      "font": b["font"], "family": b["family"], "bold": False, "italic": False, "align": "left", "lineh": 1.2, "multi": False}
r = servidor.apply_ops(src, [op, {"page": 0, "kind": "redact", "bbox": [70, 85, 200, 105], "fill": "#000000"}])
t = texto(base64.b64decode(r["pdf"]))
confere("4.500,00" in t and "3.000,00" not in t, "troca de texto apaga o antigo e escreve o novo")
confere("Contrato" not in t, "tarja remove o texto de verdade")

# 2) PDF escaneado: OCR e troca de texto na imagem
scan = open(os.path.join(pasta, "escaneado.pdf"), "rb").read()
ocr = base64.b64decode(servidor.ocr_pdf(scan, idioma="por")["pdf"])
blocos = servidor.analyze(ocr, 0)["blocks"]
confere(len(blocos) == 2 and all(b.get("ocr") for b in blocos), "OCR gera 2 blocos marcados como escaneados")
b = blocos[0]
confere("4521" in b["text"] and b.get("bg", "").startswith("#f"), "OCR lê o número e a cor do papel (%s)" % b.get("bg"))
op = {"page": 0, "kind": "rep", "bbox": b["bbox"], "origin": b["origin"], "text": b["text"].replace("4521", "9999"), "size": b["size"],
      "color": b["color"], "font": b["font"], "family": "sans", "bold": False, "italic": False, "align": b["align"], "lineh": b["lineh"],
      "multi": False, "ocr": True, "bg": b["bg"]}
out = base64.b64decode(servidor.apply_ops(ocr, [op])["pdf"])
t = texto(out)
confere("9999" in t and "4521" not in t, "troca no escaneado: texto novo no lugar do antigo")
pymupdf.open(stream=out, filetype="pdf")[0].get_pixmap(dpi=110, clip=pymupdf.Rect(60, 90, 420, 175)).save(os.path.join(pasta, "escaneado-editado.png"))

# 3) senha: desbloquear e proteger de novo
trava = open(os.path.join(pasta, "senha.pdf"), "rb").read()
try:
    ferramentas.desbloquear([("x.pdf", trava)], {"senha": "errada"})
    confere(False, "senha errada é recusada")
except ferramentas.Erro:
    confere(True, "senha errada é recusada")
livre = ferramentas.desbloquear([("x.pdf", trava)], {"senha": "abc123"})[0][0][1]
confere("Contrato secreto" in texto(livre), "senha certa abre o PDF")
de_novo = ferramentas.proteger([("x.pdf", livre)], {"senha": "abc123", "editar": True})[0][0][1]
confere(pymupdf.open(stream=de_novo, filetype="pdf").needs_pass, "proteger recoloca a senha")

# 4) comparar: relatório + páginas lado a lado
def doc(linhas, extra=False):
    d = pymupdf.open()
    p = d.new_page()
    for k, t in enumerate(linhas):
        p.insert_text((72, 100 + 22 * k), t, fontsize=13)
    if extra:
        d.new_page().insert_text((72, 100), "Anexo novo", fontsize=13)
    return d.tobytes()


saidas, _ = ferramentas.comparar([("v1.pdf", doc(["Valor: R$ 3.000,00", "Prazo: 12 meses"])), ("v2.pdf", doc(["Valor: R$ 3.500,00", "Prazo: 24 meses"], True))], {})
rel = pymupdf.open(stream=saidas[0][1], filetype="pdf")
confere(rel.page_count == 3 and rel[1].rect.width > rel[1].rect.height, "comparar gera relatório + 2 páginas lado a lado (deitadas)")
rel[1].get_pixmap(dpi=70).save(os.path.join(pasta, "comparar.png"))

print("\n%s: %d falha(s). Imagens para conferir em %s" % ("SERVIDOR", falhas, pasta))
sys.exit(1 if falhas else 0)

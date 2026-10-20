"""Servidor local do Editor de PDF.

Serve a página do editor e oferece duas funções que o navegador sozinho não faz:
  /api/analyze  lê os blocos de texto de uma página (fonte, tamanho, cor, posição)
  /api/apply    apaga de verdade o texto antigo (redação) e escreve o novo,
                reaproveitando a fonte original do PDF quando ela tem as letras.

Por padrão só este computador acessa. Com "Compartilhar na rede" ligado no painel
(dados\\config.json: {"rede": true}) outros computadores da mesma rede também acessam.
Nenhum PDF é guardado: cada arquivo é processado na memória e devolvido.

Uso:  py servidor.py [porta] [--no-browser]
      py servidor.py verificar        (confere se está tudo instalado)
Precisa de:  py -m pip install pymupdf
"""
import base64
import ipaddress
import json
import os
import re
import statistics
import sys
import threading
import time
import webbrowser
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, urlsplit

import pymupdf

HERE = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))  # no .exe, os arquivos ficam em _MEIPASS
sys.path.insert(0, HERE)
import ferramentas  # noqa: E402  (ferramentas em lote: juntar, dividir, comprimir, converter...)
PAGE_FILE = os.path.join(HERE, "editor-pdf.html")
# Configuração e registros ficam em ..\dados (EDITOR_PDF_DADOS troca o lugar).
DADOS = os.environ.get("EDITOR_PDF_DADOS") or os.path.join(os.path.dirname(HERE), "dados")
CONFIG_FILE = os.path.join(DADOS, "config.json")
LOG_FILE = os.path.join(DADOS, "registros.log")
FONTS_DIR = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
MAX_BODY = 150 * 1024 * 1024
PORT = 8768  # ajustado em main() pelo primeiro argumento numérico
REDE = False  # True = aceita outros computadores da rede local
_log_lock = threading.Lock()


def carregar_config():
    try:
        with open(CONFIG_FILE, encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return {}


def registrar(msg):
    """Uma linha por evento, sem conteúdo de PDF. Mantém o arquivo abaixo de ~1 MB."""
    try:
        os.makedirs(DADOS, exist_ok=True)
        with _log_lock:
            if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 1_000_000:
                os.replace(LOG_FILE, LOG_FILE + ".antigo")
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S") + "  " + msg + "\n")
    except Exception:
        pass


def host_permitido(host_header):
    """Só aceita localhost e, com o compartilhamento ligado, endereços IP de rede privada.
    Nomes de domínio são recusados (protege contra DNS rebinding)."""
    host_header = (host_header or "").lower().strip()
    if host_header.count(":") == 1:
        nome, _, porta = host_header.partition(":")
        if porta != str(PORT):
            return False
    elif ":" in host_header:  # IPv6 literal não é suportado
        return False
    else:
        return False  # sem porta explícita não é o nosso endereço
    if nome in ("localhost", "127.0.0.1"):
        return True
    if not REDE:
        return False
    try:
        ip = ipaddress.ip_address(nome)
    except ValueError:
        return False
    return ip.version == 4 and (ip.is_private or ip.is_link_local) and not ip.is_loopback

SYSTEM_FONTS = {
    # (família, negrito, itálico) -> arquivo em C:\Windows\Fonts
    ("sans", 0, 0): "arial.ttf", ("sans", 1, 0): "arialbd.ttf", ("sans", 0, 1): "ariali.ttf", ("sans", 1, 1): "arialbi.ttf",
    ("serif", 0, 0): "times.ttf", ("serif", 1, 0): "timesbd.ttf", ("serif", 0, 1): "timesi.ttf", ("serif", 1, 1): "timesbi.ttf",
    ("mono", 0, 0): "cour.ttf", ("mono", 1, 0): "courbd.ttf", ("mono", 0, 1): "couri.ttf", ("mono", 1, 1): "courbi.ttf",
}
BASE14 = {
    ("sans", 0, 0): "helv", ("sans", 1, 0): "hebo", ("sans", 0, 1): "heit", ("sans", 1, 1): "hebi",
    ("serif", 0, 0): "tiro", ("serif", 1, 0): "tibo", ("serif", 0, 1): "tiit", ("serif", 1, 1): "tibi",
    ("mono", 0, 0): "cour", ("mono", 1, 0): "cobo", ("mono", 0, 1): "coit", ("mono", 1, 1): "cobi",
}


def b64(data):
    return base64.b64encode(data).decode("ascii")


def gravar(doc):
    """PDF final em bytes. garbage=1 já tira do arquivo tudo o que ficou sem uso (o texto apagado sai de verdade);
    garbage=3 ainda junta objetos repetidos, mas em PDF grande leva segundos e quase nunca diminui o arquivo."""
    return doc.tobytes(garbage=3 if doc.page_count <= 40 else 1, deflate=True)


def classify_font(name, flags):
    n = name or ""
    bold = bool(flags & 16) or bool(re.search(r"bold|black|heavy|semibold|demi", n, re.I))
    italic = bool(flags & 2) or bool(re.search(r"italic|oblique", n, re.I))
    if (flags & 8) or re.search(r"courier|mono|consolas|typewriter", n, re.I):
        fam = "mono"
    elif re.search(r"times|garamond|georgia|palatino|cambria|book|minion|serif", n, re.I) and not re.search(r"sans", n, re.I):
        fam = "serif"
    elif flags & 4 and not re.search(r"arial|helvet|sans|calibri|verdana|tahoma", n, re.I):
        fam = "serif"
    else:
        fam = "sans"
    return fam, int(bold), int(italic)


def strip_subset(name):
    return re.sub(r"^[A-Z]{6}\+", "", name or "")


# ---------------------------------------------------------------- analisar
def separar_colunas(lines):
    """O PDF às vezes junta num bloco só as células de uma linha de tabela (textos lado a lado, na mesma altura).
    Esses textos não são um parágrafo: cada coluna vira um bloco próprio, com suas linhas empilhadas."""
    if len(lines) < 2:
        return [lines]

    def mesma_altura(a, b):
        sob = min(a["bbox"][3], b["bbox"][3]) - max(a["bbox"][1], b["bbox"][1])
        return sob > 0.5 * min(a["bbox"][3] - a["bbox"][1], b["bbox"][3] - b["bbox"][1])
    if not any(mesma_altura(a, b) for i, a in enumerate(lines) for b in lines[i + 1:]):
        return [lines]
    colunas = []
    for l in sorted(lines, key=lambda l: (l["bbox"][0], l["bbox"][1])):
        # entra numa coluna existente se fica logo embaixo dela e na mesma faixa horizontal
        for col in colunas:
            u = col[-1]
            if (not mesma_altura(u, l) and l["bbox"][0] < u["bbox"][2] and l["bbox"][2] > u["bbox"][0]
                    and 0 <= l["bbox"][1] - u["bbox"][3] < 2 * (u["bbox"][3] - u["bbox"][1])):
                col.append(l)
                break
        else:
            colunas.append([l])
    return [sorted(col, key=lambda l: l["bbox"][1]) for col in colunas]


def cores_da_area(page, rect):
    """Cor da letra e cor do papel numa área de página escaneada: os pixels mais escuros são a tinta, os mais claros o papel."""
    try:
        pix = page.get_pixmap(clip=rect + (-2, -2, 2, 2), dpi=96, colorspace=pymupdf.csRGB, alpha=False)
        n = pix.n
        px = [tuple(pix.samples[i:i + 3]) for i in range(0, len(pix.samples) - n + 1, n)]
        if len(px) < 10:
            raise ValueError
        px.sort(key=sum)
        k = max(1, len(px) // 10)
        media = lambda grupo: "#%02x%02x%02x" % tuple(round(sum(c[j] for c in grupo) / len(grupo)) for j in range(3))
        return media(px[:k]), media(px[-len(px) // 3:])
    except Exception:  # noqa: BLE001
        return "#000000", "#ffffff"


def analyze(pdf_bytes, pno):
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        if not 0 <= pno < doc.page_count:
            raise ValueError("página fora do documento")
        page = doc[pno]
        if page.rotation != 0:
            return {"rotated": True, "blocks": []}
        d = page.get_text("dict", flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES)
        out = []
        for b in d["blocks"]:
            if b.get("type") != 0:
                continue
            lines = []
            horizontal = True
            for l in b["lines"]:
                dx, dy = l["dir"]
                if abs(dy) > 0.02 or dx < 0.98:
                    horizontal = False
                    break
                spans = [s for s in l["spans"]]
                text = "".join(s["text"] for s in spans)
                if not text.strip():
                    continue
                main = max(spans, key=lambda s: len(s["text"].strip()))
                lines.append({
                    # texto invisível (camada do OCR sobre a imagem escaneada): o que se vê são os pixels da imagem
                    "ocr": all(s.get("alpha", 255) == 0 for s in spans if s["text"].strip()),
                    "bbox": [round(v, 2) for v in l["bbox"]],
                    "origin": [round(v, 2) for v in spans[0]["origin"]],
                    "text": text,
                    "size": round(main["size"], 2),
                    "font": main["font"],
                    "color": "#%06x" % main["color"],
                    "flags": main["flags"],
                    "styles": sorted({(strip_subset(s["font"]), round(s["size"], 1), s["color"]) for s in spans if s["text"].strip()}),
                })
            if not horizontal or not lines:
                continue
            for lines in separar_colunas(lines):  # células de tabela lado a lado viram blocos separados
                x0 = min(l["bbox"][0] for l in lines); y0 = min(l["bbox"][1] for l in lines)
                x1 = max(l["bbox"][2] for l in lines); y1 = max(l["bbox"][3] for l in lines)
                width = x1 - x0
                # parágrafo corrido (linhas cheias) junta com espaço; senão mantém as quebras
                wrapped = len(lines) > 1 and all((l["bbox"][2] - l["bbox"][0]) >= 0.85 * width for l in lines[:-1])
                if wrapped:
                    text = lines[0]["text"].rstrip()
                    for l in lines[1:]:
                        t = l["text"].strip()
                        text += ("" if text.endswith("-") and False else " ") + t
                else:
                    text = "\n".join(l["text"].rstrip() for l in lines)
                sizes = [l["size"] for l in lines]
                size = statistics.median(sizes)
                deltas = [lines[i + 1]["origin"][1] - lines[i]["origin"][1] for i in range(len(lines) - 1)]
                lineh = (statistics.median(deltas) / size) if deltas and size else 1.2
                lineh = max(0.9, min(2.5, lineh))
                if len(lines) > 1:
                    lefts = [l["bbox"][0] for l in lines]; rights = [l["bbox"][2] for l in lines]
                    centers = [(l["bbox"][0] + l["bbox"][2]) / 2 for l in lines]
                    if max(lefts) - min(lefts) < 2:
                        align = "left"
                    elif max(centers) - min(centers) < 2:
                        align = "center"
                    elif max(rights) - min(rights) < 2:
                        align = "right"
                    else:
                        align = "left"
                else:
                    align = "left"
                first = lines[0]
                fam, bold, italic = classify_font(first["font"], first["flags"])
                styles = {s for l in lines for s in l["styles"]}
                bloco = {
                    "bbox": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
                    "lines": lines, "text": text, "wrapped": wrapped, "size": size, "font": first["font"],
                    "color": first["color"], "family": fam, "bold": bool(bold), "italic": bool(italic),
                    "lineh": round(lineh, 3), "align": align, "origin": first["origin"], "mixed": len(styles) > 1,
                }
                if all(l["ocr"] for l in lines):
                    # página escaneada: a cor da letra e a do papel vêm dos pixels; a fonte do OCR não tem desenho
                    tinta, papel = cores_da_area(page, pymupdf.Rect(x0, y0, x1, y1))
                    bloco.update(ocr=True, color=tinta, bg=papel, font="", family="sans", bold=False, italic=False, mixed=False)
                out.append(bloco)
        return {"rotated": False, "blocks": out, "width": page.rect.width, "height": page.rect.height}
    finally:
        doc.close()


# ---------------------------------------------------------------- aplicar
class FontPicker:
    """Escolhe a fonte para escrever: a original do PDF (se tiver todas as letras) ou uma parecida do Windows."""

    def __init__(self, doc):
        self.doc = doc
        self.cache = {}
        self.n = 0

    def original(self, page, font_name):
        if not font_name:  # o usuário trocou a fonte: não reaproveita a original
            return None
        key = ("orig", page.number, font_name)
        if key in self.cache:
            return self.cache[key]
        buf = None
        try:
            # o nome que o texto informa nem sempre é igual ao nome da fonte do arquivo
            # ("TimesNewRomanPSMT" x "Times New Roman Regular"), então compara pelo começo do nome
            norm = lambda s: re.sub(r"[^a-z0-9]", "", strip_subset(s).lower())
            target = norm(font_name)
            want_bold = bool(re.search(r"bold|black|heavy|semibold|demi", font_name or "", re.I))
            want_ital = bool(re.search(r"italic|oblique", font_name or "", re.I))
            best, best_score = None, -1
            for f in page.get_fonts(full=True):
                cand = norm(f[3])
                common = 0
                for a, b in zip(cand, target):
                    if a != b:
                        break
                    common += 1
                if common < min(8, len(target), len(cand)):
                    continue
                score = common * 10
                score += 5 if bool(re.search(r"bold|black|heavy|semibold|demi", f[3], re.I)) == want_bold else 0
                score += 5 if bool(re.search(r"italic|oblique", f[3], re.I)) == want_ital else 0
                if score > best_score:
                    best, best_score = f, score
            if best is not None:
                _name, _ext, _type, content = self.doc.extract_font(best[0])
                if content:
                    buf = content
        except Exception:
            buf = None
        self.cache[key] = buf
        return buf

    def pick(self, page, op, text, warnings):
        chars = [c for c in set(text) if c not in "\n\r\t " ]
        # 1) a fonte original do documento, se ela já tem todas as letras
        buf = self.original(page, op.get("font"))
        if buf:
            try:
                f = pymupdf.Font(fontbuffer=buf)
                if all(f.has_glyph(ord(c)) for c in chars):
                    self.n += 1
                    name = "orig%d" % self.n
                    page.insert_font(fontname=name, fontbuffer=buf)
                    return name, f, "original"
            except Exception:
                pass
        fam, bold, italic = op.get("family", "sans"), int(bool(op.get("bold"))), int(bool(op.get("italic")))
        # 1b) o original era uma fonte padrão do PDF não embutida (Helvetica/Times/Courier): usa a mesma, se as letras couberem
        if re.match(r"^(helv|helvetica|arial|times|courier)", strip_subset(op.get("font") or ""), re.I) and not buf:
            try:
                "".join(chars).encode("cp1252")
                name = BASE14.get((fam, bold, italic), "helv")
                return name, pymupdf.Font(name), "padrao"
            except UnicodeEncodeError:
                pass
        # 2) fonte do Windows parecida
        path = os.path.join(FONTS_DIR, SYSTEM_FONTS.get((fam, bold, italic), "arial.ttf"))
        if os.path.exists(path):
            f = pymupdf.Font(fontfile=path)
            missing = [c for c in chars if not f.has_glyph(ord(c))]
            if missing:
                warnings.append("Caracteres sem glifo na fonte %s: %s" % (os.path.basename(path), "".join(sorted(missing))[:20]))
            self.n += 1
            name = "sys%d" % self.n
            page.insert_font(fontname=name, fontfile=path)
            return name, f, "sistema"
        # 3) fonte padrão do PDF
        name = BASE14.get((fam, bold, italic), "helv")
        return name, pymupdf.Font(name), "padrao"


def hex_rgb(h):
    h = (h or "#000000").lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    n = int(h, 16)
    return ((n >> 16 & 255) / 255, (n >> 8 & 255) / 255, (n & 255) / 255)


# ---------------------------------------------------------------- OCR
TESSDATA = os.environ.get("EDITOR_PDF_TESSDATA") or os.path.join(DADOS, "tessdata")  # por.traineddata, eng.traineddata... (o motor Tesseract já vem dentro do PyMuPDF)


def idiomas_ocr():
    try:
        return sorted(f[:-12] for f in os.listdir(TESSDATA) if f.endswith(".traineddata") and f[:-12] != "osd")
    except Exception:
        return []


def ocr_disponivel():
    return bool(idiomas_ocr())


def validar_idioma(idioma):
    idioma = (idioma or "por+eng").strip()
    if not re.fullmatch(r"[a-z]{3}(\+[a-z]{3})*", idioma):
        raise ValueError("idioma inválido")
    faltam = [l for l in idioma.split("+") if l not in idiomas_ocr()]
    if faltam:
        raise ValueError("falta o idioma de OCR: " + ", ".join(faltam))
    return idioma


def ocr_pdf(pdf_bytes, paginas=None, idioma="por+eng", pular_com_texto=True, dpi=300):
    """Devolve um PDF em que as páginas escolhidas ganham uma camada de texto invisível (pesquisável e copiável).
    As páginas viram imagens de 300 dpi com o texto reconhecido por baixo; as demais ficam como estavam."""
    idioma = validar_idioma(idioma)
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        if doc.needs_pass:
            raise ValueError("o PDF tem senha")
        total = doc.page_count
        alvo = set(range(total)) if paginas is None else {int(p) for p in paginas}
        if not alvo or any(not 0 <= p < total for p in alvo):
            raise ValueError("páginas fora do documento")
        out = pymupdf.open()
        feitas, puladas = 0, 0
        for i in range(total):
            pg = doc[i]
            if i not in alvo or (pular_com_texto and len(pg.get_text().strip()) >= 20):
                out.insert_pdf(doc, from_page=i, to_page=i)
                puladas += 1 if i in alvo else 0
                continue
            pix = pg.get_pixmap(dpi=dpi)
            camada = pymupdf.open(stream=pix.pdfocr_tobytes(language=idioma, tessdata=TESSDATA), filetype="pdf")
            nova = out.new_page(width=pg.rect.width, height=pg.rect.height)
            nova.show_pdf_page(nova.rect, camada, 0)
            camada.close()
            feitas += 1
        avisos = []
        if puladas:
            avisos.append("%d página(s) já tinham texto e foram mantidas como estavam." % puladas)
        if feitas == 0:
            avisos.append("Nenhuma página precisou de OCR.")
        return {"pdf": b64(gravar(out)), "reconhecidas": feitas, "avisos": avisos}
    finally:
        doc.close()


def docx_de_ocr(pdf_bytes, inicio, fim, idioma):
    """Word a partir de PDF escaneado: reconhece o texto (OCR) e monta parágrafos. Não mantém o layout nem as imagens."""
    import tempfile
    import docx as pydocx

    idioma = validar_idioma(idioma)
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    saida = pydocx.Document()
    try:
        for i in range(inicio, fim):
            pg = doc[i]
            pix = pg.get_pixmap(dpi=300)
            camada = pymupdf.open(stream=pix.pdfocr_tobytes(language=idioma, tessdata=TESSDATA), filetype="pdf")
            blocos = [b for b in camada[0].get_text("blocks", sort=True) if b[6] == 0 and b[4].strip()]
            # o OCR devolve uma linha por bloco: junta linhas seguidas do mesmo parágrafo
            # (mesma altura de letra, espaçamento pequeno, mesma margem esquerda)
            grupo, ant = [], None
            def fecha():
                if grupo:
                    saida.add_paragraph(" ".join(grupo))
            for b in blocos:
                texto = " ".join(l.strip() for l in b[4].splitlines() if l.strip())
                altura = b[3] - b[1]
                if ant is not None:
                    mesma = (abs(altura - ant[3] + ant[1]) < 0.25 * altura and 0 <= b[1] - ant[3] < 0.8 * altura
                             and abs(b[0] - ant[0]) < 20)
                    if not mesma:
                        fecha()
                        grupo = []
                grupo.append(texto)
                ant = b
            fecha()
            camada.close()
            if i < fim - 1:
                saida.add_page_break()
    finally:
        doc.close()
    with tempfile.TemporaryDirectory() as tmp:
        caminho = os.path.join(tmp, "saida.docx")
        saida.save(caminho)
        with open(caminho, "rb") as f:
            return f.read()


# ---------------------------------------------------------------- PDF para Word
_docx_ok = None


def docx_disponivel():
    """Só confere se os pacotes existem (sem importar: o pdf2docx traz OpenCV e NumPy e atrasava a abertura do editor)."""
    global _docx_ok
    if _docx_ok is None:
        import importlib.util
        try:
            _docx_ok = all(importlib.util.find_spec(m) is not None for m in ("pdf2docx", "docx"))
        except Exception:  # noqa: BLE001
            _docx_ok = False
    return _docx_ok


def converter_docx(pdf_bytes, inicio=0, fim=None, ocr="auto", idioma="por+eng"):
    """Converte o PDF (ou um intervalo de páginas, 0 = primeira) em .docx, na memória do servidor.
    Usa pdf2docx: mantém parágrafos, fontes, cores, tabelas e imagens de PDFs com texto.
    PDF escaneado (só imagem) não ganha texto: não há OCR."""
    import logging
    import tempfile
    from pdf2docx import Converter

    logging.getLogger().setLevel(logging.ERROR)
    logging.disable(logging.CRITICAL)  # pdf2docx escreve muito no console
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        if doc.needs_pass:
            raise ValueError("o PDF tem senha")
        total = doc.page_count
        if not 0 <= inicio < total:
            raise ValueError("página inicial fora do documento")
        fim = total if fim is None else min(int(fim), total)
        if fim <= inicio:
            raise ValueError("intervalo de páginas inválido")
        chars = sum(len(doc[i].get_text().strip()) for i in range(inicio, fim))
        imagens = sum(len(doc[i].get_images()) for i in range(inicio, fim))
    finally:
        doc.close()
    avisos = []
    if chars < 5 * (fim - inicio):
        if ocr != "nao" and ocr_disponivel():
            # PDF escaneado: reconhece o texto e monta o Word a partir dele
            data = docx_de_ocr(pdf_bytes, inicio, fim, idioma)
            avisos.append("PDF escaneado: o texto foi reconhecido por OCR. O Word tem só o texto (sem o layout e as imagens originais). Revise o resultado.")
            return {"docx": b64(data), "paginas": fim - inicio, "avisos": avisos, "imagens": imagens, "texto": chars, "ocr": True}
        avisos.append("Este PDF parece escaneado (quase não tem texto). O Word vai conter só as imagens das páginas; instale os dados de OCR para reconhecer o texto.")
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "entrada.pdf")
        out = os.path.join(tmp, "saida.docx")
        with open(src, "wb") as f:
            f.write(pdf_bytes)
        cv = Converter(src)
        try:
            cv.convert(out, start=inicio, end=fim)
        finally:
            cv.close()
        with open(out, "rb") as f:
            data = f.read()
    return {"docx": b64(data), "paginas": fim - inicio, "avisos": avisos, "imagens": imagens, "texto": chars}


def validar_ops(ops, npages):
    """O servidor pode receber pedidos de outros computadores da rede: confere tudo antes de usar."""
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and abs(v) < 1e6
    if not isinstance(ops, list) or len(ops) > 2000:
        raise ValueError("lista de operações inválida")
    for o in ops:
        if not isinstance(o, dict) or o.get("kind") not in ("rep", "redact"):
            raise ValueError("operação desconhecida")
        if not isinstance(o.get("page"), int) or not 0 <= o["page"] < npages:
            raise ValueError("página fora do documento")
        bb = o.get("bbox")
        if not (isinstance(bb, list) and len(bb) == 4 and all(num(v) for v in bb)):
            raise ValueError("área inválida")
        if o["kind"] == "rep":
            og = o.get("origin")
            if not (isinstance(og, list) and len(og) == 2 and all(num(v) for v in og)):
                raise ValueError("origem inválida")
            if not (num(o.get("size")) and 1 <= o["size"] <= 500):
                raise ValueError("tamanho de fonte inválido")
            if not isinstance(o.get("text", ""), str) or len(o.get("text", "")) > 50000:
                raise ValueError("texto inválido")


def apply_ops(pdf_bytes, ops):
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    validar_ops(ops, doc.page_count)
    warnings, report = [], []
    try:
        picker = FontPicker(doc)
        pages = sorted({op["page"] for op in ops})
        plans = []
        for pno in pages:
            page = doc[pno]
            reps = [o for o in ops if o["page"] == pno and o["kind"] == "rep"]
            reds = [o for o in ops if o["page"] == pno and o["kind"] == "redact"]
            for o in reps:
                if o.get("ocr"):
                    o["font"] = None  # a fonte do OCR (GlyphLessFont) não tem desenho: escreve com uma fonte do Windows
            normais = [o for o in reps if not o.get("ocr")]
            escaneados = [o for o in reps if o.get("ocr")]
            # 1) apaga o texto antigo (sem pintar nada por cima e sem mexer em imagens/gráficos)
            if normais:
                for o in normais:  # guarda a fonte original antes: depois da redação o PDF pode descartá-la
                    picker.original(page, o.get("font"))
                for o in normais:
                    r = pymupdf.Rect(o["bbox"])
                    r = pymupdf.Rect(r.x0 + 0.4, r.y0 + 0.4, r.x1 - 0.4, r.y1 - 0.4)
                    page.add_redact_annot(r, fill=False)
                page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,
                                      text=pymupdf.PDF_REDACT_TEXT_REMOVE)
            # 1b) texto de página escaneada: as letras são pixels da imagem, então apaga os pixels e pinta da cor do papel
            if escaneados:
                # a caixa do OCR é justa: aumenta um pouco (e mais embaixo, por causa das pernas de g, p, q, j)
                area = lambda o, m=0: pymupdf.Rect(o["bbox"]) + (-1.5 - m, -1.5 - m, 1.5 + m, 1.5 + 0.22 * float(o["size"]) + m)
                for o in escaneados:
                    page.add_redact_annot(area(o), fill=False)
                page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_PIXELS, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,
                                      text=pymupdf.PDF_REDACT_TEXT_REMOVE)
                # pinta a cor do papel um pouco além da área apagada, para não ficar borda clara dos pixels cortados
                for o in escaneados:
                    page.draw_rect(area(o, 1), color=None, fill=hex_rgb(o.get("bg") or "#ffffff"), overlay=True)
            # 2) tarjas: apagam texto, pixels de imagem e desenhos cobertos, e pintam de preto
            if reds:
                for o in reds:
                    page.add_redact_annot(pymupdf.Rect(o["bbox"]), fill=hex_rgb(o.get("fill") or "#000000"))
                page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_PIXELS, graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
                                      text=pymupdf.PDF_REDACT_TEXT_REMOVE)
            plans.append((pno, reps))
        # 3) escreve o texto novo
        for pno, reps in plans:
            page = doc[pno]
            for o in reps:
                text = o.get("text", "")
                if not text.strip():
                    report.append({"page": pno, "fonte": None, "apagado": True})
                    continue
                size = float(o["size"])
                color = hex_rgb(o.get("color"))
                name, font, kind = picker.pick(page, o, text, warnings)
                report.append({"page": pno, "fonte": kind})
                multi = ("\n" in text) or o.get("multi")
                x0, y0, x1, y1 = o["bbox"]
                if not multi:
                    w = font.text_length(text, fontsize=size)
                    ox, oy = o["origin"]
                    if o.get("align") == "center":
                        ox = (x0 + x1) / 2 - w / 2
                    elif o.get("align") == "right":
                        ox = x1 - w
                    page.insert_text(pymupdf.Point(ox, oy), text, fontname=name, fontsize=size, color=color)
                else:
                    align = {"left": 0, "center": 1, "right": 2}.get(o.get("align"), 0)
                    lineh = float(o.get("lineh", 1.2))
                    rect = pymupdf.Rect(x0 - 0.5, y0 - 0.5, x1 + 2, y1 + size * 0.6)
                    s = size
                    for _ in range(14):
                        rc = page.insert_textbox(rect, text, fontname=name, fontsize=s, color=color, align=align, lineheight=lineh)
                        if rc >= 0:
                            break
                        # não coube: primeiro estica para baixo, depois diminui a fonte
                        if rect.y1 < page.rect.y1 - 4 and rect.y1 - y1 < size * 6:
                            rect = pymupdf.Rect(rect.x0, rect.y0, rect.x1, min(page.rect.y1 - 2, rect.y1 + size))
                        else:
                            s *= 0.94
                    else:
                        warnings.append("Página %d: o texto não coube no bloco e não foi escrito." % (pno + 1))
        data = gravar(doc)
        return {"pdf": b64(data), "warnings": warnings, "report": report}
    finally:
        doc.close()


def substituir_texto(pdf_bytes, busca, troca, maiusc, inteira, paginas):
    """Buscar e substituir: reescreve só as linhas que contêm o termo, com a fonte/tamanho/cor da linha (via apply_ops)."""
    pad = re.escape(busca)
    if inteira:
        pad = r"(?<!\w)" + pad + r"(?!\w)"
    rg = re.compile(pad, 0 if maiusc else re.IGNORECASE)
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    ops, trocas, giradas, mistas = [], 0, 0, 0
    try:
        for pno in paginas:
            page = doc[pno]
            d = page.get_text("dict", flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES)
            for b in d["blocks"]:
                for l in b.get("lines", []):
                    spans = l["spans"]
                    text = "".join(s["text"] for s in spans)
                    n = len(rg.findall(text))
                    if not n:
                        continue
                    dx, dy = l["dir"]
                    if page.rotation or abs(dy) > 0.02 or dx < 0.98:
                        giradas += n
                        continue
                    main = max(spans, key=lambda s: len(s["text"].strip()))
                    if len({(strip_subset(s["font"]), round(s["size"], 1), s["color"]) for s in spans if s["text"].strip()}) > 1:
                        mistas += 1
                    fam, bold, italic = classify_font(main["font"], main["flags"])
                    # o texto começa onde estava o primeiro caractere visível
                    lead = len(text) - len(text.lstrip())
                    novo = rg.sub(lambda m: troca, text).strip()
                    x0 = l["bbox"][0]
                    ops.append({"kind": "rep", "page": pno, "bbox": list(l["bbox"]), "origin": [x0 if lead else spans[0]["origin"][0], spans[0]["origin"][1]],
                                "size": main["size"], "font": main["font"], "color": "#%06x" % main["color"], "family": fam,
                                "bold": bool(bold), "italic": bool(italic), "text": novo, "align": "left"})
                    trocas += n
    finally:
        doc.close()
    avisos = []
    if giradas:
        avisos.append("%d ocorrência(s) em texto girado ou inclinado não foram trocadas." % giradas)
    if mistas:
        avisos.append("%d linha(s) misturavam estilos (negrito, cores ou tamanhos) e ficaram com um estilo só." % mistas)
    if not ops:
        return {"pdf": b64(pdf_bytes), "trocas": 0, "avisos": avisos}
    r = apply_ops(pdf_bytes, ops)
    return {"pdf": r["pdf"], "trocas": trocas, "avisos": avisos + r["warnings"]}


# ---------------------------------------------------------------- HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = "EditorPDF/1.0"

    def log_message(self, fmt, *args):  # silencioso
        pass

    def _host_ok(self):
        return host_permitido(self.headers.get("Host"))

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self._host_ok():
            return self._send(403, {"error": "host não permitido"})
        path = self.path.split("?")[0]
        if path in ("/", "/editor-pdf.html"):
            with open(PAGE_FILE, "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if path.startswith("/api/arquivo/"):
            # PDF que o Windows mandou abrir (duplo clique); só os registrados pelo próprio aplicativo
            caminho = ARQUIVOS.get(path[len("/api/arquivo/"):])
            if not caminho or not os.path.isfile(caminho):
                return self._send(404, {"error": "arquivo não encontrado"})
            with open(caminho, "rb") as f:
                dados = f.read()
            registrar("abrir arquivo  %s  %d KB" % (os.path.basename(caminho), len(dados) // 1024))
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", str(len(dados)))
            self.send_header("X-Nome", quote(os.path.basename(caminho)))
            self.send_header("X-Doc", guardar_doc(dados))  # o editor já usa este número, sem reenviar o PDF
            self.send_header("X-Caminho", quote(caminho))  # para a lista de recentes do aplicativo
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(dados)
            return
        if path.startswith("/api/doc/"):
            dados = pegar_doc(path[len("/api/doc/"):])
            if dados is None:
                return self._send(410, {"error": "documento expirou"})
            return self._send(200, dados, "application/pdf")
        if path.startswith("/lib/") or path == "/motor.js":
            # bibliotecas do editor (inclui o motor MuPDF.js/Tesseract.js usado no celular); nunca sai da pasta lib
            base_lib = os.path.realpath(os.path.join(HERE, "lib"))
            alvo = os.path.realpath(os.path.join(HERE, "motor.js")) if path == "/motor.js" else os.path.realpath(os.path.join(base_lib, path[5:]))
            if (path != "/motor.js" and not alvo.startswith(base_lib + os.sep)) or not os.path.isfile(alvo) or ".." in path:
                return self._send(404, {"error": "não encontrado"})
            tipo = {".js": "text/javascript; charset=utf-8", ".wasm": "application/wasm"}.get(os.path.splitext(alvo)[1], "application/octet-stream")
            with open(alvo, "rb") as f:
                return self._send(200, f.read(), tipo)
        if path == "/api/ping":
            return self._send(200, {"ok": True, "versao": VERSAO, "loja": LOJA, "pymupdf": pymupdf.VersionBind, "rede": REDE, "docx": docx_disponivel(), "ocr": ocr_disponivel(), "idiomas": idiomas_ocr(),
                                         "office": ambiente()["office"] if self.client_address[0] in ("127.0.0.1", "::1") else [],
                                         "navegador": ambiente()["navegador"] and self.client_address[0] in ("127.0.0.1", "::1"),
                                         "pdfa": ambiente()["pdfa"],
                                         "assinatura": ambiente()["assinatura"] and self.client_address[0] in ("127.0.0.1", "::1")})
        self._send(404, {"error": "não encontrado"})

    def do_POST(self):
        if not self._host_ok():
            return self._send(403, {"error": "host não permitido"})
        origin = self.headers.get("Origin")
        if origin and urlsplit(origin).netloc.lower() != (self.headers.get("Host") or "").lower():
            return self._send(403, {"error": "origem não permitida"})
        t0 = time.time()
        quem = self.client_address[0]
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0 or n > MAX_BODY:
                return self._send(413, {"error": "arquivo grande demais"})
            if self.path == "/api/doc":
                # o editor manda o PDF uma vez só, em bytes; as chamadas seguintes usam só o número dele
                return self._send(200, {"id": guardar_doc(self.rfile.read(n))})
            body = json.loads(self.rfile.read(n).decode("utf-8"))
            if body.get("doc"):
                dados = pegar_doc(str(body["doc"]))
                if dados is None:
                    return self._send(410, {"error": "documento expirou"})  # o editor manda de novo
                body["pdf"] = dados
            if self.path == "/api/abrir":
                # outra cópia do aplicativo pede para abrir um PDF nesta janela: exige o segredo da instância
                if not SEGREDO or self.headers.get("X-Segredo") != SEGREDO or quem not in ("127.0.0.1", "::1"):
                    return self._send(403, {"error": "não permitido"})
                i = registrar_arquivo(str(body["caminho"])) if body.get("caminho") else None
                if NOVA_JANELA:
                    NOVA_JANELA(i)  # o app abre outra janela dele mesmo (com o PDF, se veio um)
                return self._send(200, {"id": i, "janela": bool(NOVA_JANELA)})
            if self.path == "/api/tool":
                if body.get("ferramenta") in ("office2pdf", "html2pdf", "assinar") and quem not in ("127.0.0.1", "::1"):
                    # abrem o Word/Excel/PowerPoint ou o navegador deste computador com arquivos de terceiros: só para quem está nele.
                    # "assinar" recebe o certificado e a senha, que pela rede passariam sem criptografia
                    registrar("%s  %s  recusado (só no computador do servidor)" % (quem, body.get("ferramenta")))
                    return self._send(403, {"error": "Por segurança, esta ferramenta só funciona no próprio computador onde o servidor está ligado."})
                arqs = [(str(f["nome"]), base64.b64decode(f["b64"])) for f in body.get("arquivos", [])]
                total_kb = sum(len(b) for _, b in arqs) // 1024
                try:
                    r = ferramentas.executar(str(body.get("ferramenta")), arqs, body.get("opcoes") or {}, CTX)
                except ferramentas.Erro as e:
                    registrar("%s  %s  recusado: %s" % (quem, body.get("ferramenta"), e))
                    return self._send(400, {"error": str(e)})
                registrar("%s  ferramenta %s  %d arquivo(s)  %d KB  %.1fs" % (quem, body.get("ferramenta"), len(arqs), total_kb, time.time() - t0))
                return self._send(200, {"nome": r["nome"], "mime": r["mime"], "b64": b64(r["bytes"]), "avisos": r["avisos"]})
            pdf = body["pdf"] if isinstance(body["pdf"], bytes) else base64.b64decode(body["pdf"])
            kb = len(pdf) // 1024
            binario = bool(body.get("doc"))  # quem mandou por número recebe o PDF novo também por número
            if self.path == "/api/buscar":
                try:
                    r = ferramentas.buscar(pdf, body.get("opcoes") or {})
                except ferramentas.Erro as e:
                    return self._send(400, {"error": str(e)})
                registrar("%s  buscar  %d resultado(s)  %d KB  %.1fs" % (quem, len(r), kb, time.time() - t0))
                return self._send(200, {"resultados": r})
            if self.path == "/api/analyze":
                r = analyze(pdf, int(body["page"]))
                registrar("%s  analisar  página %d  %d KB  %.1fs" % (quem, int(body["page"]) + 1, kb, time.time() - t0))
                return self._send(200, r)
            if self.path == "/api/apply":
                r = apply_ops(pdf, body["ops"])
                registrar("%s  aplicar   %d operação(ões)  %d KB  %.1fs" % (quem, len(body["ops"]), kb, time.time() - t0))
                return self._send(200, por_numero(r) if binario else r)
            if self.path == "/api/ocr":
                r = ocr_pdf(pdf, body.get("paginas"), body.get("idioma", "por+eng"), bool(body.get("pular_com_texto", True)))
                registrar("%s  OCR        %d página(s) reconhecida(s)  %d KB  %.1fs" % (quem, r["reconhecidas"], kb, time.time() - t0))
                return self._send(200, por_numero(r) if binario else r)
            if self.path == "/api/pdf2docx":
                if not docx_disponivel():
                    return self._send(501, {"error": "conversão para Word não instalada (py -m pip install pdf2docx python-docx)"})
                ini = int(body.get("inicio", 0))
                fim = body.get("fim")
                r = converter_docx(pdf, ini, None if fim is None else int(fim), body.get("ocr", "auto"), body.get("idioma", "por+eng"))
                registrar("%s  para Word  %d página(s)  %d KB  %.1fs" % (quem, r["paginas"], kb, time.time() - t0))
                return self._send(200, r)
            return self._send(404, {"error": "não encontrado"})
        except Exception as e:  # noqa: BLE001
            registrar("%s  ERRO  %s: %s" % (quem, type(e).__name__, e))
            return self._send(500, {"error": "%s: %s" % (type(e).__name__, e)})


# PDFs que o editor já mandou (id aleatório -> bytes). Assim cada clique não reenvia o arquivo inteiro.
# Guarda os mais recentes, até DOCS_MAX bytes no total; se um sumir, o editor recebe 410 e manda de novo.
DOCS = OrderedDict()
DOCS_MAX = 600 * 1024 * 1024
DOCS_TRAVA = threading.Lock()


def guardar_doc(dados):
    import secrets
    i = secrets.token_hex(16)
    with DOCS_TRAVA:
        DOCS[i] = bytes(dados)
        while len(DOCS) > 1 and sum(len(v) for v in DOCS.values()) > DOCS_MAX:
            DOCS.popitem(last=False)
    return i


def pegar_doc(i):
    with DOCS_TRAVA:
        dados = DOCS.get(i)
        if dados is not None:
            DOCS.move_to_end(i)
        return dados


def por_numero(r):
    """Troca o PDF em base64 da resposta pelo número dele (o editor baixa os bytes em /api/doc/<id>)."""
    r = dict(r)
    r["doc"] = guardar_doc(base64.b64decode(r.pop("pdf")))
    return r


# Arquivos abertos pelo Windows (só no aplicativo .exe): id aleatório -> caminho do PDF
ARQUIVOS = {}
SEGREDO = None  # definido pelo app.py; sem ele, /api/abrir fica desligado
NOVA_JANELA = None  # definido pelo app.py: função(id do arquivo ou None) que abre outra janela do app
VERSAO = None  # versão do aplicativo do Windows (o editor compara com a do site para avisar de atualização)
LOJA = False  # instalado pela Microsoft Store: a Loja atualiza, o editor não mostra o aviso


def registrar_arquivo(caminho):
    import secrets
    caminho = os.path.abspath(caminho)
    if not caminho.lower().endswith(".pdf") or not os.path.isfile(caminho):
        raise ValueError("não é um PDF")
    i = secrets.token_hex(16)
    ARQUIVOS[i] = caminho
    return i


CTX = {"ocr_pdf": ocr_pdf, "converter_docx": converter_docx, "substituir_texto": substituir_texto}
_cache_ambiente = {}


def ambiente():
    """Programas do computador que algumas ferramentas usam (descobertos uma vez e guardados).
    O resultado da última vez fica em ambiente.json: o editor abre na hora com ele e a checagem roda por trás."""
    if not _cache_ambiente:
        arq = os.path.join(DADOS, "ambiente.json")
        with _trava_ambiente:
            if not _cache_ambiente:
                try:
                    with open(arq, encoding="utf-8") as f:
                        _cache_ambiente.update(json.load(f))
                    threading.Thread(target=_descobrir_ambiente, args=(arq,), daemon=True).start()
                except Exception:
                    _descobrir_ambiente(arq)
    return _cache_ambiente


_trava_ambiente = threading.Lock()


def _descobrir_ambiente(arq):
    import subprocess
    try:
        out = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                              "foreach($p in 'Word.Application','Excel.Application','PowerPoint.Application'){ if([type]::GetTypeFromProgID($p)){$p.Split('.')[0]} }"],
                             capture_output=True, text=True, timeout=30, creationflags=0x08000000).stdout.split()
    except Exception:
        out = []
    pf = [os.environ.get("ProgramFiles(x86)", ""), os.environ.get("ProgramFiles", "")]
    nav = any(os.path.exists(os.path.join(p, r)) for p in pf for r in (r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe"))
    try:
        import pyhanko.sign  # noqa: F401
        assin = True
    except Exception:
        assin = False
    _cache_ambiente.update(office=out, navegador=nav, pdfa=bool(ferramentas.ghostscript()), assinatura=assin)
    try:
        with open(arq, "w", encoding="utf-8") as f:
            json.dump(_cache_ambiente, f)
    except OSError:
        pass


def verificar():
    print("PyMuPDF", pymupdf.VersionBind)
    faltam = [f for f in set(SYSTEM_FONTS.values()) if not os.path.exists(os.path.join(FONTS_DIR, f))]
    print("Converter PDF para Word:", "ok" if docx_disponivel() else "NÃO instalado (py -m pip install pdf2docx python-docx)")
    print("OCR (reconhecer texto):", ("ok, idiomas: " + ", ".join(idiomas_ocr())) if ocr_disponivel() else "SEM idiomas em " + TESSDATA + " (baixe por.traineddata de github.com/tesseract-ocr/tessdata_fast)")
    mods = []
    for m in ("PIL", "openpyxl", "pptx"):
        try:
            __import__(m)
        except Exception:
            mods.append(m)
    print("Ferramentas de imagem, Excel e PowerPoint:", "ok" if not mods else "faltam " + ", ".join(mods) + " (py -m pip install pillow openpyxl python-pptx)")
    import subprocess
    office = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                             "foreach($p in 'Word.Application','Excel.Application','PowerPoint.Application'){ if([type]::GetTypeFromProgID($p)){$p.Split('.')[0]} }"],
                            capture_output=True, text=True, creationflags=0x08000000).stdout.split()
    print("Microsoft Office (para converter para PDF):", ", ".join(office) if office else "não encontrado")
    print("Fontes do Windows:", "ok" if not faltam else "faltam " + ", ".join(sorted(faltam)))
    print("Página do editor:", "ok" if os.path.exists(PAGE_FILE) else "NÃO ENCONTRADA")
    try:
        os.makedirs(DADOS, exist_ok=True)
        print("Pasta de dados:", DADOS, "(gravável)")
    except Exception as e:  # noqa: BLE001
        print("Pasta de dados com problema:", e)
    print("Compartilhar na rede:", "ligado" if carregar_config().get("rede") else "desligado")
    print("OK")


def main():
    global PORT, REDE
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "verificar" in args:
        return verificar()
    for a in args:
        if a.isdigit():
            PORT = int(a)
    REDE = bool(carregar_config().get("rede"))
    bind = "0.0.0.0" if REDE else "127.0.0.1"
    httpd = ThreadingHTTPServer((bind, PORT), Handler)
    url = "http://127.0.0.1:%d/" % PORT
    threading.Thread(target=ambiente, daemon=True).start()  # descobre o Office e o navegador em segundo plano
    registrar("servidor ligado  porta %d  %s" % (PORT, "REDE (outros computadores podem acessar)" if REDE else "somente este computador"))
    print("Editor de PDF rodando em", url, "(rede ligada)" if REDE else "(só este computador)")
    print("Deixe esta janela aberta enquanto usa o editor. Feche-a para encerrar.")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        registrar("servidor desligado")


if __name__ == "__main__":
    main()

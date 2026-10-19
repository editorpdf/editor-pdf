"""Gera os PDFs de amostra dos testes na pasta indicada (padrão: %TEMP%\\editorpdf-testes).

senha.pdf      PDF protegido com a senha abc123 ("Contrato secreto 123")
escaneado.pdf  página que é só imagem (fundo amarelado, tinta azul-escura), como um documento escaneado
"""
import os
import sys

import pymupdf

pasta = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ["TEMP"], "editorpdf-testes")
os.makedirs(pasta, exist_ok=True)

d = pymupdf.open()
d.new_page().insert_text((72, 100), "Contrato secreto 123", fontsize=20)
open(os.path.join(pasta, "senha.pdf"), "wb").write(d.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="abc123", user_pw="abc123"))

p = pymupdf.open().new_page()
p.draw_rect(p.rect, color=None, fill=(0.97, 0.95, 0.88))
p.insert_text((72, 120), "Recibo de pagamento numero 4521", fontsize=18, color=(0.1, 0.1, 0.35))
p.insert_text((72, 160), "Valor total: R$ 1.250,00 pago em 10/10/2026", fontsize=14, color=(0.1, 0.1, 0.35))
pix = p.get_pixmap(dpi=150)
e = pymupdf.open()
q = e.new_page(width=p.rect.width, height=p.rect.height)
q.insert_image(q.rect, stream=pix.tobytes("png"))
open(os.path.join(pasta, "escaneado.pdf"), "wb").write(e.tobytes())
print("Amostras em", pasta)

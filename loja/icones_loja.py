"""Gera os ícones do pacote da Microsoft Store a partir de sistema\\icone.png.  py icones_loja.py <icone.png> <pasta Assets>"""
import os, sys
from PIL import Image

origem, destino = sys.argv[1], sys.argv[2]
os.makedirs(destino, exist_ok=True)
im = Image.open(origem).convert("RGBA")


def quadrado(lado, margem=0.0):
    """Ícone centralizado num quadrado transparente (margem = fração de folga em cada lado)."""
    tela = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    n = max(1, round(lado * (1 - 2 * margem)))
    ic = im.resize((n, n), Image.LANCZOS)
    tela.alpha_composite(ic, ((lado - n) // 2, (lado - n) // 2))
    return tela


def largo(w, h):
    tela = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    n = round(h * 0.66)
    tela.alpha_composite(im.resize((n, n), Image.LANCZOS), ((w - n) // 2, (h - n) // 2))
    return tela


salvar = lambda img, nome: img.save(os.path.join(destino, nome))
for esc in (100, 125, 150, 200, 400):
    f = esc / 100
    salvar(quadrado(round(44 * f)), "Square44x44Logo.scale-%d.png" % esc)
    salvar(quadrado(round(150 * f), 0.16), "Square150x150Logo.scale-%d.png" % esc)
    salvar(largo(round(310 * f), round(150 * f)), "Wide310x150Logo.scale-%d.png" % esc)
    salvar(quadrado(round(50 * f)), "StoreLogo.scale-%d.png" % esc)
# barra de tarefas e menu Iniciar: tamanhos exatos, sem o fundo da cor de destaque
for t in (16, 20, 24, 30, 32, 36, 40, 48, 60, 64, 72, 80, 96, 256):
    salvar(quadrado(t), "Square44x44Logo.targetsize-%d.png" % t)
    salvar(quadrado(t), "Square44x44Logo.targetsize-%d_altform-unplated.png" % t)
    salvar(quadrado(t), "Square44x44Logo.targetsize-%d_altform-lightunplated.png" % t)
print("ícones:", len(os.listdir(destino)))

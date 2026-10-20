"""Janela do app vista pelo Windows (para testar "Abrir junto com o Windows").

  py janela.py visivel <pid>   imprime True/False: o processo tem a janela "Editor de PDF" visível?
  py janela.py fechar <pid>    manda fechar a janela visível (como clicar no X)
"""
import ctypes
import ctypes.wintypes as wt
import sys

u = ctypes.windll.user32
PROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)


def achar(pid, so_visivel=True):
    achada = []

    def cada(h, _):
        p = wt.DWORD()
        u.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and (not so_visivel or u.IsWindowVisible(h)):
            buf = ctypes.create_unicode_buffer(200)
            u.GetWindowTextW(h, buf, 200)
            if buf.value == "Editor de PDF":
                achada.append(h)
                return False
        return True
    u.EnumWindows(PROC(cada), 0)
    return achada[0] if achada else None


if __name__ == "__main__":
    acao, pid = sys.argv[1], int(sys.argv[2])
    if acao == "visivel":
        print(bool(achar(pid)))
    elif acao == "fechar":
        h = achar(pid)
        if h:
            u.PostMessageW(h, 0x0010, 0, 0)  # WM_CLOSE
        print(bool(h))

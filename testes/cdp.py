"""Conversa com a janela do app pelo DevTools (porta em EDITORPDF_CDP_PORTA, padrão 9333).

O app precisa ter sido aberto com WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=<porta>
(o rodar-testes.ps1 já faz isso).

  py cdp.py js <arquivo.js> [pasta-das-amostras]   roda o JavaScript na página e imprime o resultado
  py cdp.py ir <url>                                navega a janela (ex.: /?motor=js para o motor do celular)
  py cdp.py esperar <segundos>                      espera o editor terminar de abrir
  py cdp.py foto <arquivo.png>                      captura a janela

No .js, __SENHA_B64__ e __ESCANEADO_B64__ viram os PDFs de amostra (gerados pelo amostras.py) em base64.
"""
import base64
import json
import os
import sys
import time
import urllib.request

import websocket  # pip install websocket-client

# porta do DevTools da janela do app (o rodar-testes.ps1 escolhe uma livre e passa em EDITORPDF_CDP_PORTA)
PORTA = os.environ.get("EDITORPDF_CDP_PORTA", "9333")


def conectar():
    for _ in range(40):
        try:
            paginas = json.loads(urllib.request.urlopen("http://127.0.0.1:%s/json" % PORTA, timeout=2).read())
            alvo = [p for p in paginas if p.get("type") == "page"][0]
            return websocket.create_connection(alvo["webSocketDebuggerUrl"], timeout=900, suppress_origin=True)
        except Exception:  # noqa: BLE001  (o app ainda está abrindo)
            time.sleep(0.5)
    raise SystemExit("Não achei a janela do app na porta %s." % PORTA)


def comando(ws, metodo, params, n=[0]):
    n[0] += 1
    ws.send(json.dumps({"id": n[0], "method": metodo, "params": params}))
    while True:
        r = json.loads(ws.recv())
        if r.get("id") == n[0]:
            return r


def main():
    acao, alvo = sys.argv[1], sys.argv[2]
    ws = None if acao == "esperar" else conectar()
    if acao == "js":
        codigo = open(alvo, encoding="utf-8-sig").read()
        pasta = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.environ["TEMP"], "editorpdf-testes")
        for marca, arq in (("__SENHA_B64__", "senha.pdf"), ("__ESCANEADO_B64__", "escaneado.pdf")):
            if marca in codigo:
                codigo = codigo.replace(marca, base64.b64encode(open(os.path.join(pasta, arq), "rb").read()).decode())
        r = comando(ws, "Runtime.evaluate", {"expression": codigo, "awaitPromise": True, "returnByValue": True, "timeout": 890000})
        res = r.get("result", {})
        if "exceptionDetails" in res:
            print(json.dumps({"falhas": 1, "log": ["FALHOU erro de JavaScript: " + json.dumps(res["exceptionDetails"], ensure_ascii=False)[:600]]}, ensure_ascii=False))
        else:
            print(res.get("result", {}).get("value"))
    elif acao == "ir":
        comando(ws, "Runtime.evaluate", {"expression": "location.href=%s" % json.dumps(alvo)})
    elif acao == "esperar":  # espera o editor carregar (a janela começa na tela "Abrindo…"); alvo = segundos
        fim = time.time() + float(alvo)
        while time.time() < fim:
            try:
                if ws:
                    ws.close()
                ws = None
                ws = conectar()
                r = comando(ws, "Runtime.evaluate", {"expression": "typeof S!=='undefined'&&!!document.querySelector('#bOpen')", "returnByValue": True})
                if r.get("result", {}).get("result", {}).get("value") is True:
                    print("editor pronto")
                    return
            except (Exception, SystemExit):  # noqa: BLE001  (a janela ainda não abriu ou a página trocou no meio da consulta)
                pass
            time.sleep(1)
        raise SystemExit("O editor não carregou em %s s." % alvo)
    elif acao == "foto":
        r = comando(ws, "Page.captureScreenshot", {"format": "png"})
        open(alvo, "wb").write(base64.b64decode(r["result"]["data"]))


if __name__ == "__main__":
    main()

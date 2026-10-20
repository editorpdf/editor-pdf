"""Mede o desempenho do editor com um PDF grande (300 páginas com texto e imagem).

Rode com o app aberto pelo rodar-testes (ou com WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS e EDITORPDF_CDP_PORTA definidos):
  py desempenho.py [pasta]
Gera grande.pdf na pasta (padrão %TEMP%\\editorpdf-testes) e imprime os tempos em segundos.
"""
import json
import os
import sys
import time

import pymupdf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cdp  # noqa: E402

pasta = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ["TEMP"], "editorpdf-testes")
os.makedirs(pasta, exist_ok=True)
arq = os.path.join(pasta, "grande.pdf")
if not os.path.exists(arq):
    foto = pymupdf.open()
    p = foto.new_page(width=600, height=400)
    for k in range(40):
        p.draw_rect(pymupdf.Rect(k * 15, 0, k * 15 + 15, 400), color=None, fill=(k / 40, 0.4, 1 - k / 40))
    img = p.get_pixmap(dpi=150).tobytes("jpg")
    d = pymupdf.open()
    for i in range(300):
        pg = d.new_page()
        pg.insert_text((72, 60), "Relatório de manutenção — página %d" % (i + 1), fontsize=16)
        for l in range(28):
            pg.insert_text((72, 90 + l * 14), "Linha %d: equipamento TS-%04d revisado, peças trocadas e teste de funcionamento ok." % (l + 1, i * 30 + l), fontsize=9.5)
        pg.insert_image(pymupdf.Rect(72, 500, 520, 790), stream=img)
    d.save(arq, garbage=3, deflate=True)
print("PDF: %.1f MB, 300 páginas" % (os.path.getsize(arq) / 1048576))

ws = cdp.conectar()


def js(expr, timeout=600):
    r = cdp.comando(ws, "Runtime.evaluate", {"expression": expr, "awaitPromise": True, "returnByValue": True, "timeout": timeout * 1000})
    res = r.get("result", {})
    if "exceptionDetails" in res:
        raise SystemExit("erro: " + json.dumps(res["exceptionDetails"])[:500])
    return res.get("result", {}).get("value")


cdp.comando(ws, "Performance.enable", {})
# janela escondida ou minimizada não desenha (o requestAnimationFrame para) e os tempos saem errados: traz para a frente
cdp.comando(ws, "Page.bringToFront", {})
cdp.comando(ws, "Emulation.setFocusEmulationEnabled", {"enabled": True})
codigo = open(arq, "rb").read()
import base64  # noqa: E402
b64 = base64.b64encode(codigo).decode()
js("window.__b=Uint8Array.from(atob(%s),c=>c.charCodeAt(0));1" % json.dumps(b64))
res = json.loads(js(r"""(async()=>{
  const t=()=>performance.now()/1000,sl=ms=>new Promise(r=>setTimeout(r,ms)),out={};
  window.confirm=()=>true;download=()=>'baixado';
  let t0=t();await openFile(new File([window.__b],'grande.pdf',{type:'application/pdf'}));out.abrir=t()-t0;
  // primeira página desenhada
  t0=t();for(let k=0;k<200&&!document.querySelector('.page canvas');k++)await sl(20);out.primeira_pagina_extra=t()-t0;
  // rolar até o fim e voltar (o app solta as páginas longe da tela)
  const v=document.querySelector('#view');t0=t();
  for(let k=0;k<=20;k++){v.scrollTop=v.scrollHeight*k/20;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))}
  v.scrollTop=0;out.rolar_20_saltos=t()-t0;
  // "Editar texto": primeiro clique (blocos da página 1)
  t0=t();setTool('edittext');await getBlocks(0);out.editar_texto_1o_clique=t()-t0;
  // trocar uma linha e salvar
  await startReplaceBlock(0,1);const o=S.objs[S.objs.length-1];o.text=o.text.replace('revisado','REVISADO');o.edited=true;
  t0=t();const sv=await bake(S.bytes,S.objs);out.salvar_com_troca=t()-t0;out.tamanho_salvo_mb=sv.length/1048576;
  setTool('select');S.objs=[];
  // miniaturas desenhadas
  out.miniaturas_desenhadas=document.querySelectorAll('.thumbs canvas').length;
  out.paginas_com_imagem_em_memoria=S.pages.filter(p=>p.el&&p.el.querySelector('canvas')).length;
  return JSON.stringify(out)})()"""))
m = {x["name"]: x["value"] for x in cdp.comando(ws, "Performance.getMetrics", {})["result"]["metrics"]}
res["memoria_js_mb"] = round(m.get("JSHeapUsedSize", 0) / 1048576, 1)
res["nos_na_pagina"] = int(m.get("Nodes", 0))
for k, v in res.items():
    print("%-30s %s" % (k, round(v, 3) if isinstance(v, float) else v))

"""Editor de PDF como aplicativo (.exe): sem painel e sem janela de servidor.

Liga o servidor por dentro, só para este computador, numa porta livre, e abre o editor numa janela própria
(pywebview com o WebView2 que já vem no Windows): ícone e nome do app na barra de tarefas, sem nada do navegador.
Quando a última janela fecha, o aplicativo encerra. Se o app já estiver aberto, abre outra janela nele.
Sem o WebView2 (Windows muito antigo), cai na janela do Edge em modo aplicativo, como nas versões até a 1.4.
"""
import base64, json, os, socket, subprocess, sys, threading, time

BASE = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
DADOS = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "EditorPDF")
os.makedirs(DADOS, exist_ok=True)
os.environ["EDITOR_PDF_DADOS"] = DADOS
if os.path.isdir(os.path.join(BASE, "tessdata")):
    os.environ["EDITOR_PDF_TESSDATA"] = os.path.join(BASE, "tessdata")
PERFIL = os.path.join(DADOS, "janela")       # perfil do Edge (só no modo antigo, sem WebView2)
WEBVIEW = os.path.join(DADOS, "webview")     # tema, preferências e cache da janela própria
INSTANCIA = os.path.join(DADOS, "instancia.json")
TITULO = "Editor de PDF"
try:
    with open(os.path.join(BASE, "versao.txt"), encoding="utf-8") as _f:
        VERSAO = _f.read().strip()
except OSError:
    VERSAO = None


def instalado_pela_loja():
    """True quando o app roda como pacote MSIX (Microsoft Store): aí quem atualiza é a Loja, não o próprio app."""
    try:
        import ctypes
        n = ctypes.c_uint32(0)
        return ctypes.windll.kernel32.GetCurrentPackageFullName(ctypes.byref(n), None) != 15700  # 15700 = sem pacote
    except Exception:  # noqa: BLE001
        return False


LOJA = instalado_pela_loja()
# atualizações vêm só destes endereços (versão publicada no site; instalador nas versões do GitHub)
ORIGENS_ATUALIZACAO = ("https://github.com/editorpdf/editorpdf.github.io/releases/", "https://editorpdf.github.io/")
# tela mostrada no instante em que a janela abre, enquanto o motor carrega (segue o tema claro/escuro do Windows)
ABRINDO = """<!doctype html><meta charset="utf-8"><style>
html,body{margin:0;height:100%;font:15px "Segoe UI Variable Text","Segoe UI",sans-serif;background:#f3f3f3;color:#5c5c5c}
@media(prefers-color-scheme:dark){html,body{background:#202020;color:#c5c5c5}}
body{display:flex;align-items:center;justify-content:center;flex-direction:column;gap:18px}
.r{width:28px;height:28px;border:3px solid #0067c0;border-right-color:transparent;border-radius:50%;animation:g .8s linear infinite}
@keyframes g{to{transform:rotate(360deg)}}</style><div class="r"></div><div>Abrindo…</div>"""


# ------------------------------------------------------------ "Abrir junto com o Windows"
# Com a opção ligada, o Windows abre o app com --fundo ao entrar na conta: o motor e a janela carregam escondidos e,
# quando o usuário abre o app, a janela só aparece (sem esperar o Python e o WebView2). Fechar a janela principal
# esconde em vez de encerrar, e ela volta para a tela inicial. Desligando a opção, fechar encerra como antes.
RUN_CHAVE = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NOME = "Editor de PDF"
FUNDO = {"principal": None, "base": None, "escondida": False, "saindo": False}


def inicio_ligado():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_CHAVE) as k:
            winreg.QueryValueEx(k, RUN_NOME)
        return True
    except OSError:
        return False


def ligar_inicio(ligar):
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_CHAVE, 0, winreg.KEY_SET_VALUE) as k:
        if ligar:
            winreg.SetValueEx(k, RUN_NOME, 0, winreg.REG_SZ, '"%s" --fundo' % sys.executable)
        else:
            try:
                winreg.DeleteValue(k, RUN_NOME)
            except OSError:
                pass


def ao_fechar_principal():
    """Fechar a janela principal: com a opção ligada, esconde e volta ao início (o app continua pronto)."""
    if FUNDO["saindo"] or not inicio_ligado():
        return True
    try:  # o Windows está desligando ou saindo da conta: fecha de verdade (senão travaria o desligamento)
        import ctypes
        if ctypes.windll.user32.GetSystemMetrics(0x2000):  # SM_SHUTTINGDOWN
            return True
    except Exception:  # noqa: BLE001
        pass

    def esconder():
        j = FUNDO["principal"]
        try:
            j.hide()
            FUNDO["escondida"] = True
            j.load_url(FUNDO["base"])  # tela inicial: o PDF aberto sai da memória
        except Exception:  # noqa: BLE001
            pass
    threading.Thread(target=esconder, daemon=True).start()
    return False


def mostrar_principal(url=None):
    """Pedido para abrir o app (atalho, duplo clique num PDF) enquanto ele está escondido: só mostra a janela."""
    j = FUNDO["principal"]
    FUNDO["escondida"] = False
    if url:
        j.load_url(url)
    j.show()
    try:
        from System import Action
        form = j.native
        form.Invoke(Action(lambda: (form.Activate(), form.BringToFront())))
    except Exception:  # noqa: BLE001
        pass


def responde(porta):
    s = socket.socket()
    s.settimeout(0.3)
    try:
        return s.connect_ex(("127.0.0.1", porta)) == 0
    finally:
        s.close()


# ------------------------------------------------------------ modo antigo: janela do Edge
def navegador():
    pf, pf86, loc = (os.environ.get(k, "") for k in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"))
    for c in (pf86 + r"\Microsoft\Edge\Application\msedge.exe", pf + r"\Microsoft\Edge\Application\msedge.exe",
              pf + r"\Google\Chrome\Application\chrome.exe", pf86 + r"\Google\Chrome\Application\chrome.exe",
              loc + r"\Google\Chrome\Application\chrome.exe"):
        if os.path.exists(c):
            return c
    return None


def abrir_navegador(url):
    nav = navegador()
    if not nav:
        os.startfile(url)
        return None
    return subprocess.Popen([nav, "--app=" + url, "--user-data-dir=" + PERFIL, "--window-size=1360,860",
                             "--no-first-run", "--no-default-browser-check", "--disable-features=Translate"])


def navegador_aberto():
    # o Edge do app é o único processo com este perfil na linha de comando
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "(Get-CimInstance Win32_Process -Filter \"Name='msedge.exe' OR Name='chrome.exe'\" | "
                          "Where-Object { $_.CommandLine -like '*%s*' } | Measure-Object).Count" % PERFIL.replace("'", "''")],
                         capture_output=True, text=True, creationflags=0x08000000).stdout.strip()
    return out not in ("", "0")


def rodar_no_navegador(url):
    p = abrir_navegador(url)
    if p is None:
        while True:          # sem Edge/Chrome: fica no ar até o Windows encerrar
            time.sleep(3600)
    p.wait()
    # o Edge pode entregar a janela a um processo já aberto com o mesmo perfil: espera ele fechar também
    time.sleep(2)
    while navegador_aberto():
        time.sleep(3)


# ------------------------------------------------------------ janela própria
def pasta_downloads():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as k:
            return winreg.QueryValueEx(k, "{374DE290-123F-4565-9164-39C4925E467B}")[0]
    except OSError:
        return os.path.join(os.path.expanduser("~"), "Downloads")


class Api:
    """Funções que a página chama pela janela (window.pywebview.api)."""

    def __init__(self):
        self._janela = None
        self._pasta = None   # última pasta onde o usuário salvou
        self._pasta_abrir = None

    def abrir(self):
        """Janela "Abrir" do Windows; o PDF escolhido fica registrado no servidor e a página busca por /api/arquivo/<id>."""
        import webview
        r = self._janela.create_file_dialog(webview.FileDialog.OPEN, directory=self._pasta_abrir or "",
                                            file_types=("PDF (*.pdf)", "Todos os arquivos (*.*)"))
        if not r:
            return {}
        caminho = r if isinstance(r, str) else r[0]
        self._pasta_abrir = os.path.dirname(caminho)
        return self.recente(caminho)

    def recente(self, caminho):
        """Reabre um PDF da lista de recentes (só .pdf que ainda existe)."""
        import servidor
        try:
            return {"id": servidor.registrar_arquivo(str(caminho))}
        except Exception:  # noqa: BLE001
            return {"erro": "Não encontrei o arquivo. Ele pode ter sido movido ou apagado."}

    def restaurar(self):
        """Botão "Restaurar o app": apaga o que o app guardou fora da página (a página limpa o resto sozinha)."""
        import shutil
        for nome in ("ambiente.json", "registros.log"):
            try:
                os.remove(os.path.join(DADOS, nome))
            except OSError:
                pass
        shutil.rmtree(PERFIL, ignore_errors=True)  # perfil antigo do Edge
        return {"ok": True}

    def link(self, url):
        """Links de "Sobre e licenças": abre no navegador padrão (só https)."""
        url = str(url)
        if url.startswith("https://") and not any(c in url for c in '"<> \r\n'):
            os.startfile(url)
        return {}

    def atualizar(self, url):
        """Baixa o instalador da versão nova, abre (ele mostra a tela "Atualizar") e fecha o app."""
        import tempfile, urllib.request, webview
        url = str(url)
        if LOJA:
            return {"erro": "Este app foi instalado pela Microsoft Store: ela atualiza sozinha."}
        if not url.startswith(ORIGENS_ATUALIZACAO):
            return {"erro": "Endereço de atualização não reconhecido."}
        destino = os.path.join(tempfile.gettempdir(), "Instalar-Editor-de-PDF.exe")
        try:
            with urllib.request.urlopen(url, timeout=60) as r, open(destino + ".parte", "wb") as f:
                while True:
                    bloco = r.read(1 << 20)
                    if not bloco:
                        break
                    f.write(bloco)
            os.replace(destino + ".parte", destino)
        except Exception as e:  # noqa: BLE001
            return {"erro": "Não consegui baixar a atualização (%s). Verifique a internet." % e}
        try:
            subprocess.Popen([destino])
        except OSError:
            # o Windows pode bloquear um programa baixado; mostra o arquivo para abrir com dois cliques
            subprocess.Popen(["explorer", "/select,", destino])
            return {"erro": "O Windows não deixou abrir o instalador sozinho. Abri a pasta: dê dois cliques em “Instalar-Editor-de-PDF”."}

        def fechar():
            time.sleep(1.5)
            FUNDO["saindo"] = True  # encerra de verdade, mesmo com "Abrir junto com o Windows" ligado
            for w in list(webview.windows):
                w.destroy()
        threading.Thread(target=fechar, daemon=True).start()
        return {"ok": True}

    def inicio(self, ligar=None):
        """Configurações: "Abrir junto com o Windows". Só no app instalado pelo instalador (não na Loja nem rodando do código)."""
        if LOJA or not getattr(sys, "frozen", False):
            return {"disponivel": False}
        if ligar is not None:
            try:
                ligar_inicio(bool(ligar))
            except OSError as e:
                return {"disponivel": True, "ligado": inicio_ligado(), "erro": str(e)}
        return {"disponivel": True, "ligado": inicio_ligado()}

    def sair(self):
        """Configurações: "Fechar o app de vez" (com "Abrir junto com o Windows" ligado, fechar a janela só esconde)."""
        import webview

        def fechar():
            time.sleep(0.3)
            FUNDO["saindo"] = True
            for w in list(webview.windows):
                w.destroy()
        threading.Thread(target=fechar, daemon=True).start()
        return {"ok": True}

    def salvar(self, nome, b64):
        import webview
        nome = os.path.basename(str(nome)) or "documento.pdf"
        ext = os.path.splitext(nome)[1].lower()
        tipos = ("Arquivo %s (*%s)" % (ext[1:].upper(), ext), "Todos os arquivos (*.*)") if ext else ()
        try:
            r = self._janela.create_file_dialog(webview.FileDialog.SAVE, directory=self._pasta or pasta_downloads(),
                                               save_filename=nome, file_types=tipos)
        except Exception:  # noqa: BLE001  (filtro recusado: tenta sem)
            r = self._janela.create_file_dialog(webview.FileDialog.SAVE, directory=self._pasta or pasta_downloads(),
                                               save_filename=nome)
        if not r:
            return {}
        caminho = r if isinstance(r, str) else r[0]
        if ext and not os.path.splitext(caminho)[1]:
            caminho += ext
        try:
            with open(caminho, "wb") as f:
                f.write(base64.b64decode(b64))
        except OSError as e:
            return {"erro": e.strerror or str(e)}
        self._pasta = os.path.dirname(caminho)
        return {"caminho": caminho}


def soltar_filtro(janela):
    """O pywebview pede ao WebView2 para passar toda requisição pelo Python (só para ler cabeçalhos).
    Com isso, mandar um PDF grande ao servidor local fica muito lento; o app não usa esse recurso, então desliga."""
    def ao_carregar():
        try:
            from System import Action
            from Microsoft.Web.WebView2.Core import CoreWebView2WebResourceContext
            form = janela.native

            def tirar():
                try:
                    form.browser.webview.CoreWebView2.RemoveWebResourceRequestedFilter("*", CoreWebView2WebResourceContext.All)
                except Exception:  # noqa: BLE001
                    pass
            form.Invoke(Action(tirar))
        except Exception:  # noqa: BLE001
            pass
    janela.events.loaded += ao_carregar


def nova_janela(url):
    import webview
    api = Api()
    api._janela = webview.create_window(TITULO, url, js_api=api, width=1360, height=860, min_size=(820, 560),
                                       text_select=True, background_color="#F3F3F3")
    soltar_filtro(api._janela)
    return api._janela


def main():
    # PDF pedido pelo Windows (duplo clique, "Abrir com" ou arrastado para o ícone)
    caminho = next((a for a in sys.argv[1:] if a.lower().endswith(".pdf") and os.path.isfile(a)), None)
    fundo = "--fundo" in sys.argv  # aberto pelo Windows ao entrar na conta: carrega tudo escondido

    # já aberto? pede para a cópia aberta mostrar outra janela (com o PDF, se veio um)
    try:
        with open(INSTANCIA) as f:
            inst = json.load(f)
        porta = inst["porta"]
        if responde(porta):
            if fundo:
                return  # já está pronto
            import urllib.request
            try:  # deixa a cópia aberta trazer a janela para a frente (o Windows só deixa quem o usuário acabou de abrir)
                import ctypes
                ctypes.windll.user32.AllowSetForegroundWindow(int(inst.get("pid") or -1))
            except Exception:  # noqa: BLE001
                pass
            url = "http://127.0.0.1:%d/" % porta
            req = urllib.request.Request(url + "api/abrir", json.dumps({"caminho": caminho or ""}).encode(),
                                         {"Content-Type": "application/json", "X-Segredo": inst.get("segredo", "")})
            with urllib.request.urlopen(req, timeout=10) as r:
                j = json.loads(r.read())
            if not j.get("janela"):          # a cópia aberta está no modo do Edge
                abrir_navegador(url + ("?abrir=" + j["id"] if j.get("id") else ""))
            return
    except Exception:
        pass

    # o motor (servidor + PyMuPDF) carrega em paralelo; a janela aparece na hora com "Abrindo…" e entra no editor quando ele fica pronto
    pronto = {}
    carregado = threading.Event()

    def ligar_motor():
        try:
            import servidor
            from http.server import ThreadingHTTPServer
            servidor.REDE = False
            servidor.VERSAO = VERSAO
            servidor.LOJA = LOJA
            # porta fixa (o tema e as preferências da janela ficam guardados por endereço); se estiver ocupada, uma livre
            try:
                httpd = ThreadingHTTPServer(("127.0.0.1", 8770), servidor.Handler)
            except OSError:
                httpd = ThreadingHTTPServer(("127.0.0.1", 0), servidor.Handler)
            porta = httpd.server_address[1]
            servidor.PORT = porta
            import secrets
            servidor.SEGREDO = secrets.token_hex(24)  # outra cópia do app usa para pedir "abra este PDF" (fica só no perfil do usuário)
            with open(INSTANCIA, "w") as f:
                json.dump({"porta": porta, "pid": os.getpid(), "segredo": servidor.SEGREDO}, f)
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
            threading.Thread(target=servidor.ambiente, daemon=True).start()
            servidor.registrar("aplicativo aberto  porta %d" % porta)
            base = "http://127.0.0.1:%d/" % porta
            pronto.update(servidor=servidor, httpd=httpd, base=base,
                          url=base + ("?abrir=" + servidor.registrar_arquivo(caminho) if caminho else ""))
        finally:
            carregado.set()

    threading.Thread(target=ligar_motor, daemon=True).start()
    try:
        import webview
        webview.settings["ALLOW_DOWNLOADS"] = True   # se algum download escapar do "Salvar como", o Windows pergunta onde salvar
        api = Api()
        api._janela = webview.create_window(TITULO, html=ABRINDO, js_api=api, width=1360, height=860, min_size=(820, 560),
                                            text_select=True, background_color="#F3F3F3", hidden=fundo)
        soltar_filtro(api._janela)
        FUNDO.update(principal=api._janela, escondida=fundo)
        api._janela.events.closing += ao_fechar_principal

        def abrir_janela(i):
            # app escondido (aberto com o Windows ou fechado com a opção ligada): mostra a janela que já está pronta
            url = FUNDO["base"] + ("?abrir=" + i if i else "")
            if FUNDO["escondida"]:
                mostrar_principal(url if i else None)
            else:
                nova_janela(url)

        def entrar():
            carregado.wait()
            if "url" not in pronto:
                api._janela.load_html(ABRINDO.replace("Abrindo…", "Não foi possível iniciar o editor. Feche e abra de novo."))
                if fundo:
                    api._janela.show()
                return
            FUNDO["base"] = pronto["base"]
            pronto["servidor"].NOVA_JANELA = abrir_janela
            api._janela.load_url(pronto["url"])

        webview.start(entrar, gui="edgechromium", private_mode=False, storage_path=WEBVIEW,
                      icon=os.path.join(BASE, "icone.ico"))
    except Exception as e:  # noqa: BLE001  sem WebView2: janela do Edge
        carregado.wait()
        if "url" not in pronto:
            raise
        pronto["servidor"].NOVA_JANELA = None
        pronto["servidor"].registrar("janela própria indisponível (%s: %s); usando o Edge" % (type(e).__name__, e))
        rodar_no_navegador(pronto["url"])
    if "httpd" in pronto:
        pronto["httpd"].shutdown()
    try:
        os.remove(INSTANCIA)
    except OSError:
        pass


if __name__ == "__main__":
    main()

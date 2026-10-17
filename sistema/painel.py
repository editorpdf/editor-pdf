"""Painel do Editor de PDF: liga/desliga o servidor, compartilha na rede e mostra o estado.

Abre uma janela do Edge/Chrome (modo aplicativo) com a página do painel, servida só neste computador
(127.0.0.1:8769). O painel se encerra sozinho quando a janela é fechada.
  pyw painel.py            abre o painel
  pyw painel.py --ligar    só liga o servidor do editor se estiver desligado (início do Windows)
  pyw painel.py --teste    imprime o estado e sai
"""
import json, os, socket, subprocess, sys, threading, time, re, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SISTEMA = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(SISTEMA)
DADOS = os.path.join(RAIZ, "dados")
CONFIG = os.path.join(DADOS, "config.json")
LOG = os.path.join(DADOS, "registros.log")
PORTA_EDITOR = 8768
PORTA_PAINEL = 8769
STARTUP = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Startup",
                       "Editor de PDF - servidor.lnk")
SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)
ULTIMO_PING = [time.time()]
LOCK = threading.Lock()
TRABALHOS = {}  # nome -> {"fim": bool, "texto": str}


def escuta(porta):
    s = socket.socket()
    s.settimeout(0.25)
    try:
        return s.connect_ex(("127.0.0.1", porta)) == 0
    finally:
        s.close()


def config():
    try:
        with open(CONFIG, encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return {}


def definir_rede(on):
    os.makedirs(DADOS, exist_ok=True)
    c = config()
    c["rede"] = bool(on)
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(c, f, indent=2)


def meu_ip():
    # IP da conexão que tem saída para a rede: o UDP connect não envia nada
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        return None if ip.startswith("127.") else ip
    except Exception:
        return None
    finally:
        s.close()


def python_exe():
    d = os.path.dirname(sys.executable)
    p = os.path.join(d, "python.exe")
    return p if os.path.exists(p) else sys.executable


def pids_do_servidor():
    try:
        out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True,
                             creationflags=SEM_JANELA, timeout=10).stdout.decode("latin-1")
    except Exception:
        return []
    r = set()
    for l in out.splitlines():
        p = l.split()
        if len(p) >= 5 and p[2].endswith(":0") and p[1].endswith(":%d" % PORTA_EDITOR):
            r.add(p[4])
    return sorted(r)


def ligar():
    if escuta(PORTA_EDITOR):
        return True
    # sem janela, desanexado e fora do "job" do pyw.exe (senão o servidor morre quando o painel fecha)
    flags = SEM_JANELA | 0x00000008 | 0x00000200
    cmd = [python_exe(), "servidor.py", str(PORTA_EDITOR), "--no-browser"]
    kw = dict(cwd=SISTEMA, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        subprocess.Popen(cmd, creationflags=flags | 0x01000000, **kw)  # CREATE_BREAKAWAY_FROM_JOB
    except OSError:
        subprocess.Popen(cmd, creationflags=flags, **kw)
    for _ in range(60):
        if escuta(PORTA_EDITOR):
            return True
        time.sleep(0.15)
    return False


def desligar():
    for pid in pids_do_servidor():
        subprocess.run(["taskkill", "/F", "/T", "/PID", pid], capture_output=True, creationflags=SEM_JANELA)
    for _ in range(30):
        if not escuta(PORTA_EDITOR):
            return True
        time.sleep(0.1)
    return not escuta(PORTA_EDITOR)


def abrir_editor():
    url = "http://localhost:%d/" % PORTA_EDITOR
    abrir_app(url, "1360,860")


def abrir_app(url, tamanho):
    pf, pf86, loc = (os.environ.get(k, "") for k in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"))
    for c in (pf86 + r"\Microsoft\Edge\Application\msedge.exe", pf + r"\Microsoft\Edge\Application\msedge.exe",
              pf + r"\Google\Chrome\Application\chrome.exe", pf86 + r"\Google\Chrome\Application\chrome.exe",
              loc + r"\Google\Chrome\Application\chrome.exe"):
        if os.path.exists(c):
            subprocess.Popen([c, "--app=" + url, "--window-size=" + tamanho])
            return
    os.startfile(url)


def inicio_windows():
    return os.path.exists(STARTUP)


def definir_inicio(on):
    if not on:
        try:
            os.remove(STARTUP)
        except FileNotFoundError:
            pass
        return
    vbs = os.path.join(SISTEMA, "ligar-servidor.vbs")
    ps = ("$l=(New-Object -ComObject WScript.Shell).CreateShortcut('%s');$l.TargetPath='wscript.exe';"
          "$l.Arguments='//B \"%s\"';$l.WorkingDirectory='%s';$l.WindowStyle=7;$l.Save()"
          % (STARTUP.replace("'", "''"), vbs.replace("'", "''"), SISTEMA.replace("'", "''")))
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, creationflags=SEM_JANELA, timeout=30)


def ler_log(n=200):
    try:
        with open(LOG, "rb") as f:
            f.seek(0, 2)
            tam = f.tell()
            f.seek(max(0, tam - 60000))
            linhas = f.read().decode("utf-8", "replace").splitlines()
        return linhas[-n:]
    except Exception:
        return []


def ultima_atividade(linhas):
    for l in reversed(linhas):
        if re.search(r"analisar|aplicar|ocr|ferramenta|pdf2docx", l):
            m = re.match(r"(\d{4})-(\d\d)-(\d\d) (\d\d:\d\d)", l)
            if m:
                return "%s/%s/%s %s" % (m[3], m[2], m[1], m[4])
    return None


def ping_editor():
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/api/ping" % PORTA_EDITOR, timeout=1) as r:
            return json.loads(r.read())
    except Exception:
        return None


def estado():
    on = escuta(PORTA_EDITOR)
    rede = config().get("rede") is True
    ip = meu_ip()
    return {
        "ligado": on, "rede": rede, "ip": ip,
        "enderecoRede": ("http://%s:%d/" % (ip, PORTA_EDITOR)) if ip else None,
        "enderecoLocal": "http://localhost:%d/" % PORTA_EDITOR,
        "inicio": inicio_windows(), "ultima": ultima_atividade(ler_log(400)),
        "ocupado": [k for k, v in TRABALHOS.items() if not v["fim"]],
        "ping": ping_editor() if on else None,
    }


def verificar():
    r = subprocess.run([python_exe(), "servidor.py", "verificar"], cwd=SISTEMA, capture_output=True,
                       creationflags=SEM_JANELA, timeout=120)
    return (r.stdout + r.stderr).decode("utf-8", "replace").strip()


def em_segundo_plano(nome, fn):
    with LOCK:
        if nome in TRABALHOS and not TRABALHOS[nome]["fim"]:
            return
        TRABALHOS[nome] = {"fim": False, "texto": ""}

    def run():
        try:
            TRABALHOS[nome]["texto"] = fn() or ""
        except Exception as e:
            TRABALHOS[nome]["texto"] = "Erro: %s" % e
        TRABALHOS[nome]["fim"] = True
    threading.Thread(target=run, daemon=True).start()


def acao(corpo):
    a = corpo.get("acao")
    if a == "ligar":
        em_segundo_plano("ligar", lambda: "Servidor ligado." if ligar() else "Não foi possível ligar. Use \"Verificar instalação\".")
    elif a == "desligar":
        em_segundo_plano("desligar", lambda: "Servidor desligado." if desligar() else "Não foi possível desligar.")
    elif a == "abrir":
        def f():
            if not ligar():
                return "Não foi possível ligar o servidor."
            abrir_editor()
            return "Abrindo o editor…"
        em_segundo_plano("abrir", f)
    elif a == "rede":
        on = bool(corpo.get("valor"))
        definir_rede(on)

        def f():
            if escuta(PORTA_EDITOR):
                desligar()
                ligar()
            return ("Compartilhamento ligado. Se o Windows perguntar sobre o Firewall, permita em redes privadas."
                    if on else "Compartilhamento desligado: só este computador acessa.")
        em_segundo_plano("rede", f)
    elif a == "inicio":
        on = bool(corpo.get("valor"))
        em_segundo_plano("inicio", lambda: (definir_inicio(on), "O servidor vai ligar junto com o Windows." if on
                                            else "O servidor não liga mais sozinho com o Windows.")[1])
    elif a == "verificar":
        em_segundo_plano("verificar", verificar)
    elif a == "pasta":
        os.startfile(DADOS if corpo.get("qual") == "dados" else SISTEMA)
    else:
        return {"erro": "ação desconhecida"}
    return {"ok": True}


class H(BaseHTTPRequestHandler):
    server_version = "PainelEditor"

    def log_message(self, *a):
        pass

    def _ok_host(self):
        host = (self.headers.get("Host") or "").lower()
        if host not in ("127.0.0.1:%d" % PORTA_PAINEL, "localhost:%d" % PORTA_PAINEL):
            self.send_error(403)
            return False
        o = self.headers.get("Origin")
        if o and o.lower() not in ("http://" + host,):
            self.send_error(403)
            return False
        return True

    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if not self._ok_host():
            return
        ULTIMO_PING[0] = time.time()
        p = self.path.split("?")[0]
        if p == "/":
            b = open(os.path.join(SISTEMA, "painel.html"), "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        elif p == "/api/estado":
            self._json(estado())
        elif p == "/api/log":
            self._json({"linhas": ler_log(300)})
        elif p == "/api/trabalho":
            nome = self.path.split("nome=")[-1]
            t = TRABALHOS.get(nome)
            self._json(t or {"fim": True, "texto": ""})
        else:
            self.send_error(404)

    def do_POST(self):
        if not self._ok_host():
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
            corpo = json.loads(self.rfile.read(min(n, 10000)) or b"{}")
        except Exception:
            return self._json({"erro": "pedido inválido"}, 400)
        if self.path == "/api/acao":
            self._json(acao(corpo))
        else:
            self.send_error(404)


def vigia(srv):
    # fecha o painel quando a janela some (a página avisa a cada 2 s)
    while True:
        time.sleep(3)
        if time.time() - ULTIMO_PING[0] > 25:
            srv.shutdown()
            return


def main():
    if "--ligar" in sys.argv:
        ligar()
        return
    if "--teste" in sys.argv:
        print(json.dumps(estado(), ensure_ascii=False, indent=1))
        return
    url = "http://127.0.0.1:%d/" % PORTA_PAINEL
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", PORTA_PAINEL), H)
    except OSError:
        abrir_app(url, "520,740")  # já está rodando: só mostra a janela
        return
    threading.Thread(target=vigia, args=(srv,), daemon=True).start()
    abrir_app(url, "520,740")
    srv.serve_forever()


if __name__ == "__main__":
    main()

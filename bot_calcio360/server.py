"""Server locale: mostra la pagina e la rigenera col tasto AGGIORNA DATI.

Uso:
  python server.py                  # serve reports_auto, apre il browser
  python server.py --out reports_x  # altra cartella
Il bottone AGGIORNA DATI rilancia il bot e ricarica la pagina.
Solo standard library.
"""
import argparse
import subprocess
import sys
import threading
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
OUT = "reports_auto"
_running = False


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, outdir="reports_auto", **k):
        self.outdir = outdir
        super().__init__(*a, directory=str(ROOT / outdir), **k)

    def log_message(self, *a):
        pass

    def do_POST(self):
        global _running
        if self.path != "/aggiorna":
            self.send_error(404)
            return
        if _running:
            self._ok("gia in corso")
            return
        _running = True
        try:
            subprocess.run(
                [sys.executable, "batch_main.py", "--auto", "--out", self.outdir],
                cwd=str(ROOT), timeout=1800)
            self._ok("ok")
        except Exception as e:  # noqa: BLE001
            self._ok(f"errore: {e}")
        finally:
            _running = False

    def _ok(self, msg: str):
        body = msg.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port),
                              partial(H, outdir=args.out))
    url = f"http://127.0.0.1:{args.port}/_report.html"
    print(f"Pagina: {url}")
    print("Il tasto AGGIORNA DATI nella pagina rilancia il bot da solo.")
    if not args.no_open:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    srv.serve_forever()


if __name__ == "__main__":
    main()

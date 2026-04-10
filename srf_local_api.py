#!/usr/bin/env python3
"""
Prototipo HTTP minimo (stdlib) para ler estado do monitor e servir uma pagina HTML simples.

  python srf_local_api.py --port 8765 --pid 12345

Abre http://127.0.0.1:8765/ — sem dependencias extra.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from srf_monitor_state import default_state_path, ler_estado

_HTML = """<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>SRF — estado local</title>
<style>
body{font-family:system-ui,sans-serif;max-width:880px;margin:2rem auto;padding:0 1rem;background:#0f1419;color:#e6edf3}
h1{font-size:1.25rem}a{color:#58a6ff}pre{background:#161b22;padding:1rem;border-radius:8px;overflow:auto;font-size:12px}
.muted{color:#8b949e}
</style></head><body>
<h1>SRF — painel local (prototipo)</h1>
<p class="muted">Wizard modo→fazenda e dropdown EQUIPE ficam no fluxo atm_v5 / desktop; aqui só leitura do JSON de sessao.</p>
<p>PID: <strong id="p"></strong> | <a href="/api/state">/api/state</a></p>
<pre id="j">Carregando…</pre>
<script>
const u=new URL(location.href); const pid=u.searchParams.get('pid')||'';
fetch('/api/state'+ (pid?'?pid='+encodeURIComponent(pid):'')).then(r=>r.json()).then(d=>{
  document.getElementById('j').textContent=JSON.stringify(d,null,2);
  document.getElementById('p').textContent=d._pid||'?';
}).catch(e=>{document.getElementById('j').textContent=String(e)});
</script>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "SRF-Local/0.1"

    def _pid(self) -> int:
        qs = urllib.parse.urlparse(self.path).query
        q = urllib.parse.parse_qs(qs)
        raw = (q.get("pid") or [None])[0]
        envp = os.environ.get("SRF_MONITOR_PID", "").strip()
        if raw and str(raw).isdigit():
            return int(raw)
        if envp.isdigit():
            return int(envp)
        return os.getpid()

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(_HTML.encode("utf-8"))
            return
        if path == "/api/state":
            pid = self._pid()
            data = ler_estado(default_state_path(pid))
            data["_pid"] = pid
            body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def log_message(self, fmt, *args):
        return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--pid", type=int, default=None, help="PID sessao principal (tambem aceito na query /api/state?pid=)")
    args = ap.parse_args()
    if args.pid is not None:
        os.environ["SRF_MONITOR_PID"] = str(args.pid)

    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"SRF local http://127.0.0.1:{args.port}/  (api: /api/state)")
    srv.serve_forever()


if __name__ == "__main__":
    main()

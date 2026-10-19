# -*- coding: utf-8 -*-
"""스튜디오 로컬 서버: 정적파일 + 이미지 프록시(캔버스 CORS 해결용)
실행: python serve.py  →  http://localhost:8090/index.html"""
import json
import os
import subprocess
import sys
import threading
import urllib.request
import urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).parent
IMG_CACHE = {}
EXTRACT_LOCK = threading.Lock()


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def log_message(self, *a):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/proxy":
            q = urllib.parse.parse_qs(parsed.query)
            u = (q.get("u") or [""])[0]
            if not u.startswith("http"):
                self.send_error(400)
                return
            try:
                if u in IMG_CACHE:
                    data, ctype = IMG_CACHE[u]
                else:
                    req = urllib.request.Request(u, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126",
                        "Referer": "https://brand.naver.com/"})
                    with urllib.request.urlopen(req, timeout=20) as r:
                        data = r.read(8 * 1024 * 1024)
                        ctype = r.headers.get_content_type() or "image/jpeg"
                    IMG_CACHE[u] = (data, ctype)
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "max-age=86400")
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_error(502, str(e)[:100])
            return
        if parsed.path == "/extract":
            q = urllib.parse.parse_qs(parsed.query)
            u = (q.get("u") or [""])[0].strip()
            if not u.startswith("http"):
                self.send_error(400, "bad url")
                return
            try:
                datafile = ROOT / "data.json"
                with EXTRACT_LOCK:
                    try:
                        datafile.unlink()          # 이전 결과(다른 URL) 재사용 방지
                    except Exception:
                        pass
                    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
                    proc = subprocess.run(
                        [sys.executable, str(ROOT / "extract.py"), u],
                        cwd=str(ROOT), capture_output=True, timeout=300, env=env)
                    out = (proc.stdout or b"").decode("utf-8", "replace")
                    data = None
                    if datafile.exists():
                        two = (proc.stderr or b"").decode("utf-8", "replace")
                        if two:
                            out += "\n" + two
                        data = json.loads(datafile.read_text(encoding="utf-8"))
                imgs = (data or {}).get("imgs") or []
                payload = json.dumps({"ok": bool(imgs), "data": data, "log": out}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(payload)
            except subprocess.TimeoutExpired:
                self.send_error(504, "extract timeout")
            except Exception as e:
                self.send_error(500, str(e)[:150])
            return
        return super().do_GET()


if __name__ == "__main__":
    import socket

    class V6(ThreadingHTTPServer):
        address_family = socket.AF_INET6

    try:
        srv = V6(("::", 8090), H)
        srv.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    except Exception:
        srv = ThreadingHTTPServer(("127.0.0.1", 8090), H)
    print("STUDIO http://127.0.0.1:8090/index.html")
    srv.serve_forever()

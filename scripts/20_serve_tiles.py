from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import urllib.parse, re

ROOT = Path('tiles').resolve()

class H(BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def _fp(self):
        rel = urllib.parse.unquote(self.path.split('?', 1)[0]).lstrip('/')
        fp = (ROOT / rel).resolve()
        if not str(fp).startswith(str(ROOT)) or not fp.is_file():
            raise FileNotFoundError(rel)
        return fp

    def _serve(self, head=False):
        try:
            fp = self._fp()
        except FileNotFoundError:
            self.send_error(404); return
        size = fp.stat().st_size
        start, end, code = 0, size - 1, 200
        rng = self.headers.get('Range')
        if rng:
            m = re.fullmatch(r'bytes=(\d*)-(\d*)', rng)
            if m:
                a, b = m.groups()
                if a: start = int(a)
                if b: end = min(int(b), size - 1)
                if start <= end: code = 206
        length = end - start + 1
        self.send_response(code)
        self.send_header('Content-Type', 'application/octet-stream')
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(length))
        if code == 206:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        if not head:
            with fp.open('rb') as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(65536, remaining))
                    if not chunk: break
                    self.wfile.write(chunk); remaining -= len(chunk)

    def do_GET(self): self._serve(False)
    def do_HEAD(self): self._serve(True)

ThreadingHTTPServer(('0.0.0.0', 8080), H).serve_forever()

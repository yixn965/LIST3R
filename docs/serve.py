#!/usr/bin/env python
"""Tiny static server for the LIST3R page that sends no-cache headers, so the
browser always fetches the latest assets during development."""
import http.server
import socketserver

PORT = 8731


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), NoCacheHandler) as httpd:
        print(f"Serving LIST3R page (no-cache) at http://0.0.0.0:{PORT}")
        httpd.serve_forever()

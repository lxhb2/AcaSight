#!/usr/bin/env python3
""""
\"\"\"
Python学习平台 - 本地服务器启动器
用法: python start.py
\"\"\"
"""
import os
import sys
import webbrowser
import http.server
import socketserver
from functools import partial

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def end_headers(self):
        # 允许跨域访问
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def options(self):
        self.send_response(200)
        self.end_headers()

def main():
    os.chdir(DIRECTORY)
    
    Handler.extensions_map.update({
        '.html': 'text/html',
        '.js': 'application/javascript',
        '.css': 'text/css',
        '.json': 'application/json',
        '.woff': 'application/font-woff',
        '.woff2': 'application/font-woff2',
    })
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}/index.html"
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║                   Python 学习平台 v2.0                       ║
╠══════════════════════════════════════════════════════════════╣
║  服务已启动                                                    ║
║                                                              ║
║  访问地址: http://localhost:{PORT}                             ║
║                                                              ║
║  按 Ctrl+C 停止服务器                                        ║
╚══════════════════════════════════════════════════════════════╝
        """)
        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务器已停止")
            sys.exit(0)

if __name__ == "__main__":
    main()

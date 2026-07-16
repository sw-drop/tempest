#!/usr/bin/env python3
import http.server
import socketserver
import os

PORT = 8025
Handler = http.server.SimpleHTTPRequestHandler

# Ensure correct javascript mime type
Handler.extensions_map.update({
    '.js': 'application/javascript',
    '.json': 'application/json',
    '.html': 'text/html',
    '.css': 'text/css',
})

# Change directory to the script's directory so it serves files from the correct root
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print("==================================================")
    print(f"SFRO-Dash Local Test Server running at:")
    print(f"👉 http://localhost:{PORT}/index.html")
    print("==================================================")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server. Goodbye!")

import json
import sqlite3
import requests
import tempfile
import os
import re
from datetime import datetime
import pandas as pd
from http.server import BaseHTTPRequestHandler
import openai

# Configuration
GOOGLE_DRIVE_FILE_ID = '1WXgnZRn2nw72xXjABCPbJjON2CUr6O6L'

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            user_message = data.get('message', '')
            api_key = data.get('api_key', '')
            
            if not api_key or not api_key.startswith('sk-'):
                self.send_response_json({
                    'error': "Valid OpenAI API key required (starts with 'sk-')",
                    'sql_query': None,
                    'data': []
                }, status_code=400)
                return
            
            # Test response for now
            self.send_response_json({
                'response': f"✅ Connected! Your message: {user_message}",
                'sql_query': "SELECT COUNT(*) FROM pharma_sales",
                'data': [{"status": "API key validated"}],
                'total_rows': 1
            })
                
        except Exception as e:
            self.send_response_json({
                'error': f"Server error: {str(e)}",
                'sql_query': None,
                'data': []
            }, status_code=500)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def send_response_json(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

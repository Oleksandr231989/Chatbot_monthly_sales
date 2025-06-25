import json
import sqlite3
import requests
import tempfile
import os
import re
import pandas as pd
from http.server import BaseHTTPRequestHandler
import openai

# Configuration
GOOGLE_DRIVE_FILE_ID = '1WXgnZRn2nw72xXjABCPbJjON2CUr6O6L'

class PharmaDataManager:
    def __init__(self, db_path):
        self.db_path = db_path

    def execute_query(self, query):
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df, None
        except Exception as e:
            return None, str(e)

class ChatGPTQueryProcessor:
    def __init__(self, api_key):
        self.client = openai.OpenAI(api_key=api_key)

    def generate_sql_query(self, user_question):
        try:
            system_prompt = """
You are a SQL expert for pharmaceutical sales data.

Table: pharma_sales
Columns: country, brands_new, sales_euro, year, month, corp_new

Rules:
1. Use 'brands_new' not 'brand_original'  
2. Use 'sales_euro' as primary metric
3. For Sb brand: WHERE brands_new = 'Sb'
4. Generate ONLY valid SQLite SQL

Return only SQL, no explanations.
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Convert to SQL: {user_question}"}
                ],
                temperature=0.1,
                max_tokens=200
            )

            sql_query = response.choices[0].message.content.strip()
            sql_query = re.sub(r'```sql\n?', '', sql_query)
            sql_query = re.sub(r'```\n?', '', sql_query)
            
            return sql_query, None
        except Exception as e:
            return None, f"SQL generation error: {str(e)}"

    def generate_response(self, user_question, results):
        try:
            if results is not None and not results.empty:
                results_text = results.to_string(index=False, max_rows=10)
            else:
                results_text = "No results found"

            prompt = f"""
Question: {user_question}
Data: {results_text}

Provide clear business analysis of this pharmaceutical sales data.
Focus on key numbers and trends.
"""

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a pharmaceutical data analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=400
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Response generation error: {str(e)}"

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
                    'error': "Valid OpenAI API key required",
                    'sql_query': None,
                    'data': []
                }, 400)
                return
            
            # Download database
            db_path = self.download_database()
            
            # Process query
            data_manager = PharmaDataManager(db_path)
            query_processor = ChatGPTQueryProcessor(api_key)
            
            # Test simple query first
            if user_message.lower() == 'test connection':
                test_df, test_error = data_manager.execute_query("SELECT COUNT(*) as total FROM pharma_sales LIMIT 1")
                if test_error:
                    self.send_response_json({
                        'error': f"Database error: {test_error}",
                        'sql_query': None,
                        'data': []
                    })
                else:
                    self.send_response_json({
                        'response': f"✅ Connected! Database has {test_df.iloc[0]['total']:,} records",
                        'sql_query': "SELECT COUNT(*) as total FROM pharma_sales",
                        'data': test_df.to_dict('records'),
                        'total_rows': len(test_df)
                    })
                return
            
            # Generate and execute SQL
            sql_query, sql_error = query_processor.generate_sql_query(user_message)
            if sql_error:
                self.send_response_json({
                    'error': sql_error,
                    'sql_query': None,
                    'data': []
                })
                return
            
            results_df, db_error = data_manager.execute_query(sql_query)
            if db_error:
                self.send_response_json({
                    'error': f"Database error: {db_error}",
                    'sql_query': sql_query,
                    'data': []
                })
                return
            
            # Generate response
            response = query_processor.generate_response(user_message, results_df)
            
            # Prepare data
            data_for_response = []
            if results_df is not None and not results_df.empty:
                data_for_response = results_df.head(10).to_dict('records')
                for record in data_for_response:
                    for key, value in record.items():
                        if pd.isna(value):
                            record[key] = None
            
            self.send_response_json({
                'response': response,
                'sql_query': sql_query,
                'data': data_for_response,
                'total_rows': len(results_df) if results_df is not None else 0
            })
            
            # Cleanup
            if os.path.exists(db_path):
                os.unlink(db_path)
                
        except Exception as e:
            self.send_response_json({
                'error': f"Server error: {str(e)}",
                'sql_query': None,
                'data': []
            }, 500)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def download_database(self):
        try:
            url = f"https://drive.google.com/uc?export=download&id={GOOGLE_DRIVE_FILE_ID}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
            temp_file.write(response.content)
            temp_file.close()
            
            return temp_file.name
        except Exception as e:
            raise Exception(f"Database download failed: {str(e)}")
    
    def send_response_json(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

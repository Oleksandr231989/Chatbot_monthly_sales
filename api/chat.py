# =============================================================================
# COMPLETE PHARMA SALES CHATBOT API - GPT-4o Mini Version
# Model: GPT-4o Mini for fast, cost-effective analysis
# Features: Advanced SQL generation, Multi-language support, Trend analysis
# =============================================================================

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

# MODEL SPECIFICATION: GPT-4o Mini
# - 200x cheaper than GPT-4 (~$0.15 vs $30 per 1M tokens)
# - Much faster response times
# - Still excellent for SQL generation and analysis
OPENAI_MODEL = "gpt-4o-mini"

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

    def get_schema_info(self):
        schema_info = {
            "table_name": "pharma_sales",
            "columns": {
                "country": "TEXT - Country name (e.g., 'Mexico', 'Brazil', 'France')",
                "date": "DATE - Date of the record",
                "competitive_market": "TEXT - Market category (e.g., 'Gut Microbiota Care', 'Ear Drops')",
                "submarket_1": "TEXT - Submarket level 1 (e.g., 'Probiotic', 'Non Probiotic')",
                "corp_new": "TEXT - PRIORITY: Consolidated corporation name (use this over corporation_original)",
                "brands_new": "TEXT - PRIORITY: Consolidated brand name (use this over brand_original)",
                "sales_euro": "REAL - Sales converted to EUR (PRIMARY SALES METRIC)",
                "sales_units": "INTEGER - Sales units/volume",
                "year": "INTEGER - Year (2023, 2024, 2025)",
                "month": "INTEGER - Month (1-12)"
            },
            "key_entities": {
                "biocodex_corporation": "Use WHERE corp_new LIKE '%biocodex%' OR corp_new LIKE '%BIOCODEX%'",
                "sb_brand": "Use WHERE brands_new = 'Sb' (this is a major Biocodex brand)",
                "market_share_calculation": "Brand Sales ÷ Total Market Sales × 100"
            }
        }
        return schema_info

class ChatGPTQueryProcessor:
    def __init__(self, api_key, data_manager):
        self.client = openai.OpenAI(api_key=api_key)
        self.data_manager = data_manager
        self.schema_info = data_manager.get_schema_info()

    def create_system_prompt(self):
        return """
You are a specialized SQL query generator for pharmaceutical sales data analysis with TREND ANALYSIS capabilities.

DATABASE SCHEMA:
Table: pharma_sales

EXACT COLUMN NAMES (case-sensitive):
- country: TEXT - Country name (e.g., 'Mexico', 'Brazil', 'France', 'Ukraine')
- date: DATE - Date of the record
- competitive_market: TEXT - Market category (e.g., 'Gut Microbiota Care', 'Ear Drops')
- submarket_1: TEXT - Submarket level 1 (e.g., 'Probiotic', 'Non Probiotic')
- submarket_2: TEXT - Submarket level 2
- corporation_original: TEXT - Original corporation name
- brand_original: TEXT - Original brand name
- product: TEXT - Product/SKU name
- sales_local_currency: REAL - Sales in local currency
- sales_units: INTEGER - Sales units/volume
- currency: TEXT - Local currency code
- sales_euro: REAL - Sales converted to EUR (PRIMARY SALES METRIC)
- corp_new: TEXT - PRIORITY: Consolidated corporation name (use this over corporation_original)
- brands_new: TEXT - PRIORITY: Consolidated brand name (use this over brand_original)
- year: INTEGER - Year (2023, 2024, 2025)
- month: INTEGER - Month (1-12)

KEY BUSINESS RULES:
1. ALWAYS use 'corp_new' instead of 'corporation_original'
2. ALWAYS use 'brands_new' instead of 'brand_original'
3. 'sales_euro' is the PRIMARY metric for sales comparisons
4. For Biocodex queries: WHERE corp_new LIKE '%biocodex%' OR corp_new LIKE '%BIOCODEX%'
5. Brand 'Sb' is a major Biocodex brand
6. Market share = (Brand Sales / Total Market Sales) * 100

CRITICAL TREND ANALYSIS REQUIREMENTS:
7. For YEARLY data: ALWAYS include year-over-year growth comparison
8. For MONTHLY data: ALWAYS include month-over-month AND year-over-year comparison
9. For PERIOD data: Compare same periods (e.g., Jan-May 2025 vs Jan-May 2024)
10. NEVER provide absolute figures without context - always show growth rates

MANDATORY QUERY PATTERNS:

FOR YEARLY ANALYSIS:
- Current year sales + Previous year same months comparison
- Calculate growth rate: ((Current - Previous) / Previous) * 100
- Example: 2025 sales vs same months in 2024

FOR MONTHLY ANALYSIS:
- Current month vs previous month (sequential)
- Current month vs same month previous year
- Show both month-over-month and year-over-year trends

FOR PERIOD ANALYSIS (e.g., Q1, Jan-Mar, etc.):
- Current period vs same period previous year
- Calculate percentage growth

TREND ANALYSIS QUERY STRUCTURE:
```sql
WITH current_period AS (
    SELECT SUM(sales_euro) as current_sales, SUM(sales_units) as current_units
    FROM pharma_sales
    WHERE [current period conditions]
),
previous_period AS (
    SELECT SUM(sales_euro) as previous_sales, SUM(sales_units) as previous_units
    FROM pharma_sales
    WHERE [previous period conditions]
)
SELECT
    cp.current_sales,
    cp.current_units,
    pp.previous_sales,
    pp.previous_units,
    ROUND(((cp.current_sales - pp.previous_sales) / pp.previous_sales * 100), 2) as sales_growth_percent,
    ROUND(((cp.current_units - pp.previous_units) / pp.previous_units * 100), 2) as units_growth_percent
FROM current_period cp, previous_period pp
```

SPECIFIC EXAMPLES:

For "Sb sales in Ukraine 2025":
- Query 2025 data AND same months of 2024
- Calculate 2025 vs 2024 growth rate

For "Sb sales in Mexico March 2025":
- Query March 2025 data
- Compare to February 2025 (month-over-month)
- Compare to March 2024 (year-over-year)

For "Sb sales Q1 2025":
- Query Jan-Mar 2025 data
- Compare to Jan-Mar 2024 data
- Calculate Q1 growth rate

CRITICAL COLUMN USAGE:
- Use 'sales_euro' NOT 'Sales euro' or ' Sales euro '
- Use 'sales_units' NOT 'Sales, units' or ' Sales, units '
- Use 'brands_new' NOT 'Brand' or 'Brands new'
- Use 'corp_new' NOT 'Corporation' or 'Corp new'
- Use 'country' NOT 'Country'
- Use 'competitive_market' NOT 'Competitive market'

SAMPLE COUNTRIES: Mexico, Brazil, France, Germany, Belgium, Poland, Ukraine, Russia, Turkey, US
SAMPLE BRANDS: Sb, OTIPAX, SAFORELLE, MUCOGYNE, HYDROMEGA, GALACTOGIL, SYMBIOSYS
SAMPLE MARKETS: Gut Microbiota Care, Ear Drops, Intimate Dryness, Immunity, Urinary
DATA YEARS: 2023, 2024, 2025 (use for trend comparisons)

QUERY GENERATION RULES:
1. Generate ONLY valid SQLite SQL queries with CTE structure for trend analysis
2. ALWAYS include growth rate calculations when possible
3. Use exact column names as specified above
4. Include appropriate GROUP BY and ORDER BY clauses
5. Use LIMIT for top/bottom queries
6. Handle case-insensitive searches with LIKE and wildcards
7. For market share calculations, use subqueries or CTEs
8. MANDATORY: Include previous period comparison for context

Return ONLY the SQL query with trend analysis, no explanations or markdown formatting.
"""

    def generate_sql_query(self, user_question):
        """
        Generate SQL query using GPT-4o Mini
        Fast, cost-effective SQL generation with advanced capabilities
        """
        try:
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,  # GPT-4o Mini: Fast & Cost-effective
                messages=[
                    {"role": "system", "content": self.create_system_prompt()},
                    {"role": "user", "content": f"Convert this question to SQL: {user_question}"}
                ],
                temperature=0.1,  # Low temperature for consistent SQL generation
                max_tokens=500
            )

            sql_query = response.choices[0].message.content.strip()
            sql_query = re.sub(r'```sql\n?', '', sql_query)
            sql_query = re.sub(r'```\n?', '', sql_query)
            sql_query = sql_query.strip()

            return sql_query, None
        except Exception as e:
            return None, f"Error generating SQL query: {str(e)}"

    def generate_response(self, user_question, query_results, sql_query):
        """
        Generate natural language response using GPT-4o Mini
        Multi-language support with factual analysis
        """
        try:
            if query_results is not None and not query_results.empty:
                results_text = query_results.to_string(index=False, max_rows=20)
                results_summary = f"Query returned {len(query_results)} rows"
            else:
                results_text = "No results found"
                results_summary = "Query returned no data"

            # Extract specific entities from the question for focused analysis
            brand_mentioned = None
            country_mentioned = None
            market_mentioned = None
            company_mentioned = None

            # Common entities
            brands = ['Sb', 'OTIPAX', 'SAFORELLE', 'MUCOGYNE', 'HYDROMEGA', 'GALACTOGIL', 'SYMBIOSYS', 'MEDIKINET', 'STERIMAR', 'GESTARELLE']
            countries = ['Mexico', 'Brazil', 'France', 'Germany', 'Belgium', 'Poland', 'Ukraine', 'Russia', 'Turkey', 'US', 'India', 'Italy', 'Romania', 'Bulgaria', 'Estonia', 'Finland', 'Greece', 'Hungary', 'Latvia', 'Lithuania', 'Morocco', 'Portugal']
            markets = ['Gut Microbiota Care', 'Ear Drops', 'Intimate Dryness', 'Immunity', 'Urinary', 'Intimate Care', 'Pregnancy', 'Weight Control']

            for brand in brands:
                if brand.lower() in user_question.lower():
                    brand_mentioned = brand
                    break

            for country in countries:
                if country.lower() in user_question.lower():
                    country_mentioned = country
                    break

            for market in markets:
                if market.lower() in user_question.lower():
                    market_mentioned = market
                    break

            if 'biocodex' in user_question.lower():
                company_mentioned = 'Biocodex'

            # Determine response type
            if brand_mentioned and country_mentioned:
                response_type = "BRAND_COUNTRY_SPECIFIC"
            elif brand_mentioned:
                response_type = "BRAND_SPECIFIC"
            elif company_mentioned:
                response_type = "COMPANY_SPECIFIC"
            elif market_mentioned or country_mentioned:
                response_type = "MARKET_SPECIFIC"
            else:
                response_type = "GENERIC"

            response_prompt = f"""
You are a pharmaceutical data analyst providing FACTUAL analysis based only on database results.

ANALYSIS TYPE: {response_type}
USER QUESTION: {user_question}
ENTITIES IDENTIFIED: Brand: {brand_mentioned}, Country: {country_mentioned}, Market: {market_mentioned}, Company: {company_mentioned}
QUERY RESULTS: {results_text}

CRITICAL REQUIREMENTS:
1. Use ONLY factual data from the database results
2. DO NOT speculate about marketing campaigns, customer acquisition, or external factors
3. DO NOT mention causes you cannot verify from the data
4. Stick to mathematical comparisons and observable data trends
5. Use ONLY the data provided - no assumptions or industry knowledge
6. RESPOND IN THE SAME LANGUAGE AS THE USER'S QUESTION (MOST IMPORTANT)

MULTI-LANGUAGE SUPPORT:
- If user asks in English, respond in English
- If user asks in Spanish (¿Cuáles son...?, ¿Qué...?, etc.), respond in Spanish
- If user asks in French (Quelles sont...?, Quel est...?, etc.), respond in French
- If user asks in German (Wie hoch sind...?, Was sind...?, etc.), respond in German
- If user asks in Portuguese (Quais são...?, Qual é...?, etc.), respond in Portuguese
- If user asks in Italian (Quali sono...?, Qual è...?, etc.), respond in Italian
- Detect the language from the question and match it exactly

RESPONSE STRUCTURE:
```
📊 {brand_mentioned or 'DATA'} ANALYSIS{' - ' + country_mentioned.upper() if country_mentioned else ''}
═══════════════════════════════════════
Current Performance: [State exact figures from database]
Growth Comparison: [Mathematical comparison with previous periods from data]

🔍 KEY INSIGHTS:
• Data Observations: [What the numbers show without speculation]
• Comparative Analysis: [How metrics compare to previous periods based on data]
• Quantitative Trends: [Mathematical trends visible in the data]
• Measurable Changes: [Specific percentage changes and numerical differences]
```

FACTUAL LANGUAGE TO USE (translate to user's language):
- "The data shows..." / "Los datos muestran..." / "Les données montrent..." / "Die Daten zeigen..." / "Os dados mostram..."
- "According to database records..." / "Según los registros de la base de datos..." / "Selon les enregistrements de la base de données..." / "Laut Datenbankaufzeichnungen..." / "De acordo com os registros do banco de dados..."
- "Mathematical comparison reveals..." / "La comparación matemática revela..." / "La comparaison mathématique révèle..." / "Der mathematische Vergleich zeigt..." / "A comparação matemática revela..."
- "Numerical analysis indicates..." / "El análisis numérico indica..." / "L'analyse numérique indique..." / "Die numerische Analyse zeigt..." / "A análise numérica indica..."

AVOID COMPLETELY:
- Speculation about marketing campaigns
- Assumptions about customer behavior
- External market factors not in database
- Business strategy recommendations
- Causal explanations without data support
- Industry knowledge not present in results

FOCUS ON:
- Exact numerical values
- Mathematical comparisons
- Percentage calculations
- Data trends visible in numbers
- Factual observations only

Provide only data-driven insights based on the database query results in the EXACT SAME LANGUAGE as the user's question.
"""

            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,  # GPT-4o Mini: Fast & Cost-effective
                messages=[
                    {"role": "system", "content": f"You are a pharmaceutical data analyst. Provide ONLY factual analysis based on the database results. CRITICAL: Always respond in the same language as the user's question. If user asks in Spanish, respond in Spanish. If user asks in French, respond in French. If user asks in German, respond in German. If user asks in Portuguese, respond in Portuguese. Match the user's language exactly. Do not speculate about marketing campaigns, customer acquisition, or external factors not present in the data."},
                    {"role": "user", "content": response_prompt}
                ],
                temperature=0,  # Factual responses, no creativity
                max_tokens=1200
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error generating response: {str(e)}"

class handler(BaseHTTPRequestHandler):
    """
    Main API handler for Vercel deployment
    Processes pharmaceutical sales data queries with GPT-4o Mini
    """
    
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
            
            # Download database from Google Drive
            db_path = self.download_database()
            
            # Initialize processors
            data_manager = PharmaDataManager(db_path)
            query_processor = ChatGPTQueryProcessor(api_key, data_manager)
            
            # Handle test connection
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
                        'response': f"✅ Connected! Database has {test_df.iloc[0]['total']:,} records. Using GPT-4o Mini for fast, cost-effective analysis.",
                        'sql_query': "SELECT COUNT(*) as total FROM pharma_sales",
                        'data': test_df.to_dict('records'),
                        'total_rows': len(test_df)
                    })
                return
            
            # Generate SQL query using GPT-4o Mini
            sql_query, sql_error = query_processor.generate_sql_query(user_message)
            if sql_error:
                self.send_response_json({
                    'error': sql_error,
                    'sql_query': None,
                    'data': []
                })
                return
            
            # Execute SQL query
            results_df, db_error = data_manager.execute_query(sql_query)
            if db_error:
                self.send_response_json({
                    'error': f"Database error: {db_error}",
                    'sql_query': sql_query,
                    'data': []
                })
                return
            
            # Generate response using GPT-4o Mini
            response = query_processor.generate_response(user_message, results_df, sql_query)
            
            # Prepare data for response
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
            
            # Cleanup temporary database file
            if os.path.exists(db_path):
                os.unlink(db_path)
                
        except Exception as e:
            self.send_response_json({
                'error': f"Server error: {str(e)}",
                'sql_query': None,
                'data': []
            }, 500)
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def download_database(self):
        """Download SQLite database from Google Drive"""
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
        """Send JSON response with CORS headers"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

# =============================================================================
# MODEL INFORMATION
# =============================================================================
"""
🤖 AI MODEL: GPT-4o Mini

📊 CAPABILITIES:
✅ Advanced SQL query generation with trend analysis
✅ Multi-language support (EN/ES/FR/DE/PT/IT)  
✅ Entity recognition (brands, countries, markets)
✅ Factual-only analysis (no speculation)
✅ Year-over-year and month-over-month comparisons
✅ Market share calculations with CTEs

⚡ PERFORMANCE:
• Response time: ~1-2 seconds (vs 5-10s for GPT-4)
• Cost: ~$0.15 per 1M tokens (vs $30 for GPT-4)
• Quality: Excellent for structured tasks like SQL generation

💰 COST EFFICIENCY:
• 200x cheaper than GPT-4
• Perfect for production chatbots
• Maintained high accuracy for pharmaceutical analysis

🌍 LANGUAGES SUPPORTED:
• English, Spanish, French, German, Portuguese, Italian
• Automatic language detection and matching
"""

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
5. Brand 'Sb' is a major Biocodex brand: Use WHERE brands_new = 'Sb' (EXACT match, not LIKE)
6. Market share = (Brand Sales / Total Market Sales) * 100

CRITICAL TREND ANALYSIS REQUIREMENTS:
7. DEFAULT PERIOD: If no period specified, use MAT (Moving Annual Total) - last 12 months
8. SALES METRICS: Always provide BOTH sales_euro AND sales_units unless specifically asked for one
9. MANDATORY: Always include previous year comparison for vs PY,% calculation
10. For YEARLY data: Include year-over-year growth comparison
11. For MONTHLY data: Include month-over-month AND year-over-year comparison
12. For PERIOD data: Compare same periods (e.g., Jan-May 2025 vs Jan-May 2024)
13. Keep analysis simple and factual - avoid complex interpretations

DEFAULT MAT QUERY STRUCTURE (when no period specified):
```sql
WITH current_mat AS (
    SELECT SUM(sales_euro) as current_sales, SUM(sales_units) as current_units
    FROM pharma_sales
    WHERE date >= date('now', '-12 months') AND [other conditions]
),
previous_mat AS (
    SELECT SUM(sales_euro) as previous_sales, SUM(sales_units) as previous_units
    FROM pharma_sales
    WHERE date >= date('now', '-24 months') AND date < date('now', '-12 months') AND [other conditions]
)
SELECT
    cp.current_sales,
    cp.current_units,
    pp.previous_sales,
    pp.previous_units,
    ROUND(((cp.current_sales - pp.previous_sales) / pp.previous_sales * 100), 2) as sales_growth_percent,
    ROUND(((cp.current_units - pp.previous_units) / pp.previous_units * 100), 2) as units_growth_percent
FROM current_mat cp, previous_mat pp
```

FOR MONTHLY ANALYSIS:
- Current month vs previous month (sequential)
- Current month vs same month previous year
- Show both month-over-month and year-over-year trends

FOR PERIOD ANALYSIS (e.g., Q1, Jan-Mar, etc.):
- Current period vs same period previous year
- Calculate percentage growth

SPECIFIC EXAMPLES:

For "Sb sales in Ukraine 2025":
- Query 2025 data AND same months of 2024
- Use WHERE brands_new = 'Sb' (EXACT match)
- Calculate 2025 vs 2024 growth rate

For "Sb sales in Mexico March 2025":
- Query March 2025 data
- Use WHERE brands_new = 'Sb' (EXACT match)
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
BRAND MATCHING RULES:
- For exact brand names like 'Sb': Use brands_new = 'Sb' (EXACT match)
- For partial brand searches: Use brands_new LIKE '%brand%' only when appropriate
- Always prefer EXACT matches for specific brand names
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
You are a pharmaceutical data analyst providing SIMPLE, FACTUAL analysis based only on database results.

USER QUESTION: {user_question}
QUERY RESULTS: {results_text}

CRITICAL REQUIREMENTS:
1. Respond in the same language as the user's question
2. Keep responses SIMPLE and FACTUAL - just state the numbers
3. Always provide BOTH sales in euros AND units when available
4. ALWAYS include comparison vs same period previous year (vs PY,%)
5. Calculate vs PY,% as: ((current sales - previous year sales) / previous year sales) * 100
6. ALWAYS specify the exact period for which data is extracted
7. Place "vs PY,%" immediately after each absolute value
8. If user asks for "table" or "show table", provide data in table format
9. Use clear, simple language

SIMPLE RESPONSE FORMAT:

First, provide a descriptive introduction with the EXACT PERIOD, then show the sales results.

INTRODUCTION TEMPLATE:
"The sales of [product/brand] in [country/market] for [EXACT PERIOD] show the following results:"

Then follow with:
**Sales Results:**
- Sales (Euros): [exact amount from data] (vs PY,% [percentage change])
- Sales (Units): [exact amount from data] (vs PY,% [percentage change])

EXAMPLE OUTPUT:
"The sales of product 'Sb' in Ukraine for January-June 2025 show the following results:"

**Sales Results:**
- Sales (Euros): 2,761,788 (vs PY,% -64.6%)
- Sales (Units): 301,955 (vs PY,% -66.3%)

PERIOD SPECIFICATION EXAMPLES:
- "for 2025" (full year)
- "for January-March 2025" (quarterly)
- "for June 2025" (monthly)
- "for MAT ending June 2025" (moving annual total)
- "for Q1 2025" (quarterly)
- "for H1 2025" (half year)

KEY ELEMENTS:
1. Always mention: product name in quotes, country/market, and EXACT time period
2. Natural transition: Use "show the following results" to bridge to the data
3. MANDATORY: Always include vs PY,% comparison immediately after each value
4. Format percentage with one decimal place and + or - sign
5. Be specific about the period (avoid vague terms like "current period")
6. Respond in the same language as the user's question automatically

If user requests table format, present data as a simple table with vs PY,% column.

ALWAYS include previous year comparison and specify exact period. No exceptions.

Provide only factual numbers in the same language as the user's question.
"""

            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,  # GPT-4o Mini: Fast & Cost-effective
                messages=[
                    {"role": "system", "content": f"You are a pharmaceutical data analyst. Respond in the same language as the user's question. Provide ONLY factual analysis based on the database results. Do not speculate about marketing campaigns, customer acquisition, or external factors not present in the data."},
                    {"role": "user", "content": response_prompt}
                ],
                temperature=0.2,  # 20% temperature for more factual responses
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
✅ Enhanced language detection and consistency
✅ Mandatory vs PY,% calculations
✅ Hidden SQL queries with toggle functionality

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
• Enhanced automatic language detection and matching
• Consistent single-language responses (no mixing)

📊 OUTPUT FEATURES:
• Always includes vs PY,% comparison
• Hidden SQL queries with show/hide toggle
• Clean, professional response format
• Exact brand matching (Sb = 'Sb', not LIKE '%Sb%')
"""

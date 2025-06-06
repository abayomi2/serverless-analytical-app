from flask import Flask, jsonify
import os
import boto3
import json
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# --- Database Configuration (Reads same env vars as the other app) ---
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME')
DB_USERNAME = os.environ.get('DB_USERNAME')
DB_PASSWORD_SECRET_ARN = os.environ.get('DB_PASSWORD_SECRET_ARN')
AWS_REGION = os.environ.get('AWS_REGION')

db_password = None

def get_db_password():
    global db_password
    if db_password:
        return db_password

    try:
        client = boto3.client('secretsmanager', region_name=AWS_REGION)
        response = client.get_secret_value(SecretId=DB_PASSWORD_SECRET_ARN)
        secret = json.loads(response['SecretString'])
        db_password = secret['password']
        return db_password
    except Exception as e:
        app.logger.error(f"Reporting App: Error retrieving DB secret: {e}")
        return None

def get_db_connection():
    password = get_db_password()
    if not all([DB_HOST, DB_NAME, DB_USERNAME, password]):
        return None
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USERNAME, password=password
        )
        return conn
    except Exception as e:
        app.logger.error(f"Reporting App: Error connecting to DB: {e}")
        return None

@app.route('/reporting')
def home():
    return "Reporting Service is online."

@app.route('/reporting/property-summary')
def get_property_summary():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT region, COUNT(*) as property_count FROM properties WHERE region IS NOT NULL GROUP BY region ORDER BY property_count DESC;")
            summary = cur.fetchall()
        return jsonify(summary)
    except Exception as e:
        app.logger.error(f"Reporting App: Error fetching summary: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
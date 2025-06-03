from flask import Flask, jsonify, request
import os
import boto3
import json
import psycopg2
from psycopg2 import sql # For safe SQL query construction
from psycopg2.extras import RealDictCursor # To get results as dictionaries

app = Flask(__name__)

# --- Database Configuration ---
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT', '5432') # Default PostgreSQL port
DB_NAME = os.environ.get('DB_NAME')
DB_USERNAME = os.environ.get('DB_USERNAME')
DB_PASSWORD_SECRET_ARN = os.environ.get('DB_PASSWORD_SECRET_ARN')
AWS_REGION = os.environ.get('AWS_REGION')

db_password = None

def get_db_password():
    global db_password
    if db_password:
        return db_password

    if not DB_PASSWORD_SECRET_ARN or not AWS_REGION:
        app.logger.error("DB_PASSWORD_SECRET_ARN or AWS_REGION environment variables not set.")
        return None
    
    try:
        client = boto3.client('secretsmanager', region_name=AWS_REGION)
        get_secret_value_response = client.get_secret_value(SecretId=DB_PASSWORD_SECRET_ARN)
        secret = get_secret_value_response['SecretString']
        db_password = json.loads(secret)['password'] # Assuming the secret stores a JSON with a 'password' key
        return db_password
    except Exception as e:
        app.logger.error(f"Error retrieving DB password from Secrets Manager: {e}")
        return None

def get_db_connection():
    password = get_db_password()
    if not all([DB_HOST, DB_PORT, DB_NAME, DB_USERNAME, password]):
        app.logger.error("One or more database connection parameters are missing.")
        return None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USERNAME,
            password=password
        )
        return conn
    except Exception as e:
        app.logger.error(f"Error connecting to database: {e}")
        return None

def initialize_db():
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS properties (
                        id SERIAL PRIMARY KEY,
                        address VARCHAR(255) NOT NULL,
                        price INTEGER NOT NULL,
                        type VARCHAR(50),
                        region VARCHAR(50)
                    );
                """)
                # Check if table is empty, then insert mock data if so
                cur.execute("SELECT COUNT(*) FROM properties;")
                if cur.fetchone()[0] == 0:
                    mock_initial_properties = [
                        {"address": "123 Green St, Sydney", "price": 1200000, "type": "House", "region": "NSW"},
                        {"address": "456 Blue Rd, Melbourne", "price": 850000, "type": "Apartment", "region": "VIC"},
                        {"address": "789 Red Av, Sydney", "price": 2500000, "type": "House", "region": "NSW"},
                    ]
                    insert_query = sql.SQL("INSERT INTO properties (address, price, type, region) VALUES ({}) RETURNING id;").format(
                        sql.SQL(', ').join([sql.Placeholder()] * 4) # For 4 columns
                    )
                    for prop in mock_initial_properties:
                         cur.execute(insert_query, (prop['address'], prop['price'], prop['type'], prop['region']))
                conn.commit()
            app.logger.info("Database initialized successfully (table created/checked, mock data inserted if empty).")
        except Exception as e:
            app.logger.error(f"Error initializing database table: {e}")
            conn.rollback() # Rollback in case of error
        finally:
            conn.close()
    else:
        app.logger.error("Could not connect to database for initialization.")

# Initialize DB when app starts (in a Fargate context, this runs when the container starts)
# For local dev, this might run multiple times due to reloader.
# In a more robust app, use Flask's @app.before_first_request or similar, or a migration tool.
with app.app_context():
     initialize_db()


@app.route('/')
def home():
    return "Welcome to the Property Insights API! Now connected to PostgreSQL."

@app.route('/api/properties', methods=['GET'])
def get_properties():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur: # RealDictCursor returns dicts
            cur.execute("SELECT id, address, price, type, region FROM properties;")
            properties = cur.fetchall()
        return jsonify(properties)
    except Exception as e:
        app.logger.error(f"Error fetching properties: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/properties', methods=['POST'])
def add_property():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ('address', 'price')):
            return jsonify({"error": "Missing address or price"}), 400

        address = data['address']
        price = data['price']
        prop_type = data.get('type') # Optional
        region = data.get('region')   # Optional

        insert_query = sql.SQL("""
            INSERT INTO properties (address, price, type, region) 
            VALUES (%s, %s, %s, %s) RETURNING id, address, price, type, region;
        """)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(insert_query, (address, price, prop_type, region))
            new_property = cur.fetchone()
            conn.commit()
        return jsonify(new_property), 201
    except Exception as e:
        app.logger.error(f"Error adding property: {e}")
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/analytics/summary', methods=['GET'])
def get_analytics_summary():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*) AS total_properties, AVG(price) AS average_price FROM properties;")
            summary_stats = cur.fetchone()
            
            cur.execute("""
                SELECT region, COUNT(*) AS count 
                FROM properties 
                WHERE region IS NOT NULL 
                GROUP BY region;
            """)
            properties_by_region_list = cur.fetchall()
            properties_by_region_dict = {row['region']: row['count'] for row in properties_by_region_list}

        # Ensure average_price is formatted nicely if it exists
        if summary_stats and summary_stats['average_price'] is not None:
             avg_price_formatted = f"{float(summary_stats['average_price']):,.2f}"
        else:
             avg_price_formatted = "N/A"


        return jsonify({
            "total_properties": summary_stats['total_properties'] if summary_stats else 0,
            "average_price": avg_price_formatted,
            "properties_by_region": properties_by_region_dict
        })
    except Exception as e:
        app.logger.error(f"Error fetching analytics summary: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # For local development, you might want to set these env vars manually or use a .env file
    # For cloud deployment, these are set by CDK/Fargate.
    if not all([DB_HOST, DB_PORT, DB_NAME, DB_USERNAME, DB_PASSWORD_SECRET_ARN, AWS_REGION]):
         print("Warning: Some DB environment variables might not be set for local execution.")
         print("Please set: DB_HOST, DB_PORT, DB_NAME, DB_USERNAME, DB_PASSWORD_SECRET_ARN, AWS_REGION")
         # For local testing without full AWS setup, you might want to fall back to mock data or local DB
    
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
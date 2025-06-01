from flask import Flask, jsonify
import os

# Create the Flask app instance
app = Flask(__name__)

# Mock data for property listings (replace with more complex data later if desired)
mock_properties = [
    {"id": 1, "address": "123 Green St, Sydney", "price": 1200000, "type": "House", "region": "NSW"},
    {"id": 2, "address": "456 Blue Rd, Melbourne", "price": 850000, "type": "Apartment", "region": "VIC"},
    {"id": 3, "address": "789 Red Av, Sydney", "price": 2500000, "type": "House", "region": "NSW"},
    {"id": 4, "address": "101 Yellow Wy, Brisbane", "price": 650000, "type": "Townhouse", "region": "QLD"},
    {"id": 5, "address": "202 Purple Ln, Sydney", "price": 950000, "type": "Apartment", "region": "NSW"},
]

@app.route('/')
def home():
    return "Welcome to the Property Insights API!"

@app.route('/api/properties', methods=['GET'])
def get_properties():
    return jsonify(mock_properties)

@app.route('/api/analytics/summary', methods=['GET'])
def get_analytics_summary():
    if not mock_properties:
        return jsonify({"error": "No property data available"}), 404

    total_properties = len(mock_properties)
    average_price = sum(p['price'] for p in mock_properties) / total_properties

    properties_by_region = {}
    for prop in mock_properties:
        region = prop.get("region", "Unknown")
        properties_by_region[region] = properties_by_region.get(region, 0) + 1

    return jsonify({
        "total_properties": total_properties,
        "average_price": f"{average_price:,.2f}", # Formatted as string
        "properties_by_region": properties_by_region
    })

if __name__ == '__main__':
    # Get port from environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000)) 
    app.run(debug=True, host='0.0.0.0', port=port)
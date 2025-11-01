from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import csv
import io
from functools import wraps
import os

app = Flask(__name__)
CORS(app)

# Simple in-memory data storage (for production use a database like MongoDB/PostgreSQL)
metrics_db = {
    'revenue': {'value': 4523450, 'change': 12.5, 'trend': 'up'},
    'users': {'value': 8456, 'change': 8.3, 'trend': 'up'},
    'campaigns': {'value': 24, 'change': 3.2, 'trend': 'up'},
    'roi': {'value': 3.8, 'change': -2.1, 'trend': 'down'}
}

campaigns_db = [
    {'id': 1, 'name': 'समर सेल 2025', 'status': 'Active', 'reach': 25000, 'engagement': 4.2, 'roi': 2.8},
    {'id': 2, 'name': 'ब्र्याण्ड अवेयरनेस', 'status': 'Active', 'reach': 42000, 'engagement': 3.8, 'roi': 2.1},
    {'id': 3, 'name': 'नए उत्पाद लॉन्च', 'status': 'Completed', 'reach': 18000, 'engagement': 5.1, 'roi': 3.4},
    {'id': 4, 'name': 'ईमेल न्यूजलेटर', 'status': 'Active', 'reach': 12000, 'engagement': 2.9, 'roi': 1.8},
]

monthly_revenue_db = [
    {'month': 'जन', 'revenue': 35000, 'target': 40000},
    {'month': 'फर', 'revenue': 38000, 'target': 40000},
    {'month': 'मार', 'revenue': 42000, 'target': 40000},
    {'month': 'अप्र', 'revenue': 39000, 'target': 40000},
    {'month': 'मई', 'revenue': 45000, 'target': 45000},
    {'month': 'जून', 'revenue': 48000, 'target': 45000},
]

# Simple token-based authentication
VALID_TOKEN = "your-secret-token-123"

def require_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if token != VALID_TOKEN and token != '':
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Routes

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0'
    }), 200

@app.route('/api/metrics', methods=['GET'])
@require_token
def get_metrics():
    """Get all key metrics"""
    formatted_metrics = {}
    for key, data in metrics_db.items():
        if key == 'roi':
            formatted_metrics[key] = {
                'value': f"{data['value']}x",
                'change': f"{'+' if data['change'] > 0 else ''}{data['change']}%",
                'trend': data['trend']
            }
        elif key == 'revenue':
            formatted_metrics[key] = {
                'value': f"₹{data['value']:,}",
                'change': f"{'+' if data['change'] > 0 else ''}{data['change']}%",
                'trend': data['trend']
            }
        else:
            formatted_metrics[key] = {
                'value': f"{data['value']:,}",
                'change': f"{'+' if data['change'] > 0 else ''}{data['change']}%",
                'trend': data['trend']
            }
    return jsonify(formatted_metrics), 200

@app.route('/api/metrics/<metric_id>', methods=['GET', 'PUT'])
@require_token
def handle_metric(metric_id):
    """Get or update a specific metric"""
    if metric_id not in metrics_db:
        return jsonify({'error': 'Metric not found'}), 404
    
    if request.method == 'GET':
        return jsonify(metrics_db[metric_id]), 200
    
    elif request.method == 'PUT':
        data = request.json
        if 'value' in data:
            metrics_db[metric_id]['value'] = data['value']
        if 'change' in data:
            metrics_db[metric_id]['change'] = data['change']
        if 'trend' in data:
            metrics_db[metric_id]['trend'] = data['trend']
        return jsonify({'message': 'Metric updated', 'data': metrics_db[metric_id]}), 200

@app.route('/api/campaigns', methods=['GET', 'POST'])
@require_token
def campaigns():
    """Get all campaigns or create new campaign"""
    if request.method == 'GET':
        return jsonify(campaigns_db), 200
    
    elif request.method == 'POST':
        data = request.json
        new_campaign = {
            'id': max([c['id'] for c in campaigns_db]) + 1,
            'name': data.get('name'),
            'status': 'Active',
            'reach': data.get('reach', 0),
            'engagement': data.get('engagement', 0),
            'roi': data.get('roi', 0)
        }
        campaigns_db.append(new_campaign)
        return jsonify(new_campaign), 201

@app.route('/api/campaigns/<int:campaign_id>', methods=['GET', 'PUT', 'DELETE'])
@require_token
def campaign_detail(campaign_id):
    """Get, update, or delete a specific campaign"""
    campaign = next((c for c in campaigns_db if c['id'] == campaign_id), None)
    
    if not campaign:
        return jsonify({'error': 'Campaign not found'}), 404
    
    if request.method == 'GET':
        return jsonify(campaign), 200
    
    elif request.method == 'PUT':
        data = request.json
        campaign.update(data)
        return jsonify(campaign), 200
    
    elif request.method == 'DELETE':
        campaigns_db.remove(campaign)
        return jsonify({'message': 'Campaign deleted'}), 200

@app.route('/api/revenue', methods=['GET'])
@require_token
def get_monthly_revenue():
    """Get monthly revenue data"""
    return jsonify(monthly_revenue_db), 200

@app.route('/api/revenue/update', methods=['POST'])
@require_token
def update_revenue():
    """Update revenue for a specific month"""
    data = request.json
    month = data.get('month')
    revenue = data.get('revenue')
    
    for entry in monthly_revenue_db:
        if entry['month'] == month:
            entry['revenue'] = revenue
            return jsonify({'message': 'Revenue updated', 'data': entry}), 200
    
    return jsonify({'error': 'Month not found'}), 404

@app.route('/api/export/csv', methods=['GET'])
@require_token
def export_csv():
    """Export campaigns data as CSV"""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['id', 'name', 'status', 'reach', 'engagement', 'roi'])
    writer.writeheader()
    
    for campaign in campaigns_db:
        writer.writerow(campaign)
    
    output.seek(0)
    response = send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"campaigns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )
    return response

@app.route('/api/dashboard/summary', methods=['GET'])
@require_token
def dashboard_summary():
    """Get complete dashboard summary"""
    total_reach = sum(c['reach'] for c in campaigns_db)
    avg_engagement = sum(c['engagement'] for c in campaigns_db) / len(campaigns_db) if campaigns_db else 0
    active_campaigns = len([c for c in campaigns_db if c['status'] == 'Active'])
    
    return jsonify({
        'metrics': metrics_db,
        'campaigns_count': len(campaigns_db),
        'active_campaigns': active_campaigns,
        'total_reach': total_reach,
        'avg_engagement': round(avg_engagement, 2),
        'revenue_data': monthly_revenue_db,
        'last_updated': datetime.now().isoformat()
    }), 200

# Error handlers

@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
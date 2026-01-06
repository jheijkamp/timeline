
#!/usr/bin/env python3

from flask import Flask, request, render_template
import mysql.connector
from mysql.connector import Error
# import folium
from math import radians, sin, cos, sqrt, atan2
from collections import deque
from datetime import datetime, timedelta
import pytz
from config import DB_CONFIG
import json

# =====================
# CONFIGURATIE
# =====================



MAX_ACC = 20        
MIN_DIST = 3        
SMOOTH_WINDOW = 3   
local_tz = pytz.timezone('Europe/Amsterdam')

app = Flask(__name__)

# =====================
# HULPFUNCTIES
# =====================

def distance_m(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def init_db():
    """Initialiseer MariaDB tabel"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                readable_time DATETIME,
                SSID VARCHAR(255),
                acc FLOAT,
                alt FLOAT,
                batt INT,
                bs INT,
                cog FLOAT,
                conn VARCHAR(50),
                created_at BIGINT,
                lat DOUBLE,
                lon DOUBLE,
                m INT,
                source VARCHAR(50),
                tid VARCHAR(10),
                topic VARCHAR(255),
                vac FLOAT,
                vel FLOAT,
                timestamp BIGINT,
                INDEX (readable_time)
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Error as e:
        print(f"Fout bij init DB: {e}")

# =====================
# STATE (IN MEMORY)
# =====================

last_points = deque(maxlen=SMOOTH_WINDOW)
last_saved_point = None

# =====================
# ROUTES
# =====================

@app.route("/pub", methods=["POST"])
def receive_location():
    global last_saved_point

    data = request.get_json(force=True)
    if data.get("_type") != "location":
        return "ignored", 200

    lat, lon, acc = data.get("lat"), data.get("lon"), data.get("acc")
    
    if lat is None or lon is None or acc is None:
        return "bad request", 400

    if acc > MAX_ACC:
        return "ignored", 200

    if last_saved_point:
        dist = distance_m(last_saved_point[0], last_saved_point[1], lat, lon)
        if dist < MIN_DIST:
            return "ignored", 200

    last_points.append((lat, lon))
    if len(last_points) < SMOOTH_WINDOW:
        return "buffering", 200

    lat_smooth = sum(p[0] for p in last_points) / len(last_points)
    lon_smooth = sum(p[1] for p in last_points) / len(last_points)

    tst = data.get('tst')
    dt_nl = datetime.fromtimestamp(tst, pytz.utc).astimezone(local_tz)
    readable_time = dt_nl.strftime('%Y-%m-%d %H:%M:%S')

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        sql = """INSERT INTO locations (readable_time, SSID, acc, alt, batt, bs, cog, conn, 
                 created_at, lat, lon, m, source, tid, topic, vac, vel, timestamp) 
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        
        cur.execute(sql, (readable_time, data.get("SSID"), acc, data.get("alt"),
                          data.get("batt"), data.get("bs"), data.get("cog"), data.get("conn"),
                          data.get("created_at"), lat, lon, data.get("m"),
                          data.get("source"), data.get("tid"), data.get("topic"),
                          data.get("vac"), data.get("vel"), tst))
        conn.commit()
        cur.close()
        conn.close()
        last_saved_point = (lat_smooth, lon_smooth)
        print(f"Opgeslagen: {readable_time}")
    except Error as e:
        print("Fout bij opslaan:", e)
        return "error", 500

    return "ok", 200

@app.route("/")
def index():
    day_str = request.args.get('day')
    if not day_str or not day_str.strip():
        day_str = datetime.now(local_tz).strftime('%Y-%m-%d')
    
    points = []
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        # We gebruiken CAST(... AS CHAR) om de datum direct als tekst op te halen
        cur.execute("""
            SELECT 
                lat, 
                lon, 
                CAST(readable_time AS CHAR) as readable_time 
            FROM locations 
            WHERE DATE(readable_time) = %s 
            ORDER BY timestamp ASC
        """, (day_str,))
        points = cur.fetchall()
        cur.close()
        conn.close()
    except Error as e:
        print(f"Database error: {e}")

    # Bereken navigatie
    current_dt = datetime.strptime(day_str, '%Y-%m-%d')
    prev_day = (current_dt - timedelta(days=1)).strftime('%Y-%m-%d')
    next_day = (current_dt + timedelta(days=1)).strftime('%Y-%m-%d')

    return render_template(
        "timeline.html",
        day=day_str,
        prev=prev_day,
        next=next_day,
        points_json=json.dumps(points) # Cruciaal: zet de lijst om naar tekst
    )

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
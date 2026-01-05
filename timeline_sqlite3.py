#!/usr/bin/env python3

from flask import Flask, request
from flask import render_template
import sqlite3
import time
from math import radians, sin, cos, sqrt, atan2
from collections import deque
from datetime import datetime
import os
import pytz


# =====================
# CONFIGURATIE
# =====================


MAX_ACC = 20        # meter – alles erboven weggooien
MIN_DIST = 3        # meter – minimale verplaatsing
SMOOTH_WINDOW = 3   # aantal punten voor smoothing
local_tz = pytz.timezone('Europe/Amsterdam')

# =====================
# FLASK APP
# =====================

app = Flask(__name__)

# =====================
# HULPFUNCTIES
# =====================

def distance_m(lat1, lon1, lat2, lon2):
    """Bereken afstand tussen twee GPS-punten in meters"""
    R = 6371000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def init_db():
    """Initialiseer database indien nodig"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            readable_time TEXT,
            SSID TEXT,
            acc REAL,
            alt REAL,
            batt INTEGER,
            bs INTEGER,
            cog REAL,
            conn TEXT,
            created_at INTEGER,
            lat REAL,
            lon REAL,
            m INTEGER,
            source TEXT,
            tid TEXT,
            topic TEXT,
            vac REAL,
            vel REAL,
            timestamp INTEGER
        )
    """)
    conn.commit()
    conn.close()


def get_db():
    """Open database"""
    return sqlite3.connect(DB_PATH, check_same_thread=False)


# =====================
# STATE (IN MEMORY)
# =====================

last_points = deque(maxlen=SMOOTH_WINDOW)
last_saved_point = None

db = None

# =====================
# ROUTES
# =====================

@app.route("/pub", methods=["POST"])
def receive_location():
    global last_saved_point, db

    data = request.get_json(force=True)

    msg_type = data.get("_type")

    # 👉 Alleen location-berichten verwerken
    if msg_type != "location":
        print(f"Niet-locatie bericht genegeerd: type={msg_type}")
        return "ignored", 200

    lat = data.get("lat")
    lon = data.get("lon")
    acc = data.get("acc")
    
    print(
    f"type={msg_type}, "
    f"lat={data.get('lat')}, "
    f"acc={data.get('acc')}"
)


    if lat is None or lon is None or acc is None:
        print("Ongeldige data ontvangen:", data)
        return "bad request", 400

    # 1️⃣ Accuracy-filter
    if acc > MAX_ACC:
        print(f"GPS punt genegeerd (acc={acc}m)")
        return "ignored", 200

    # 2️⃣ Minimum-afstand filter
    if last_saved_point:
        dist = distance_m(
            last_saved_point[0],
            last_saved_point[1],
            lat,
            lon
        )
        if dist < MIN_DIST:
            print(f"Punt genegeerd (afstand={dist:.1f}m)")
            return "ignored", 200

    # 3️⃣ Smoothing
    last_points.append((lat, lon))

    if len(last_points) < SMOOTH_WINDOW:
        print("Bufferen voor smoothing...")
        return "buffering", 200

    lat_smooth = sum(p[0] for p in last_points) / len(last_points)
    lon_smooth = sum(p[1] for p in last_points) / len(last_points)

    tst = data.get('tst')
    # Omzetten naar leesbare tijd
    dt_utc = datetime.fromtimestamp(tst, pytz.utc)
    dt_nl = dt_utc.astimezone(local_tz)
    readable_time = dt_nl.strftime('%Y-%m-%d %H:%M:%S')

    # Opslaan
    try:
        cur = db.cursor()
        cur.execute("""
                    INSERT INTO locations (
                    readable_time,
                    SSID,
                    acc,
                    alt,
                    batt,
                    bs,
                    cog,
                    conn,
                    created_at,
                    lat,
                    lon,
                    m,
                    source,
                    tid,
                    topic,
                    vac,
                    vel,
                    timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )""",
                    (
                        readable_time,
                        data.get("SSID"),
                        acc,
                        data.get("alt"),
                        data.get("batt"),
                        data.get("bs"),
                        data.get("cog"),
                        data.get("conn"),
                        data.get("created_at"),
                        lat,
                        lon,
                        data.get("m"),
                        data.get("source"),
                        data.get("tid"),
                        data.get("topic"),
                        data.get("vac"),
                        data.get("vel"),
                        tst)
                    )
        db.commit()
        last_saved_point = (lat_smooth, lon_smooth)

        print(
            f"Opgeslagen: lat={lat_smooth:.6f}, "
            f"lon={lon_smooth:.6f}, acc={acc}m, "
            f"time={readable_time}"
            )

    except Exception as e:
        print("Fout bij opslaan in DB:", e)
        return "error", 500

    return "ok", 200


@app.route("/")
def index():
    return render_template(
        "timeline.html",
        day=day,
        prev=prev_day,
        next=next_day,
        map=map_html
)


# =====================
# MAIN
# =====================

if __name__ == "__main__":
    print("Controleren database op:", DB_PATH)
    init_db()
    db = get_db()
    print("Database is gereed.")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )

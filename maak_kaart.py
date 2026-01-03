#!/usr/bin/env python3

from flask import Flask, request, render_template
import sqlite3
import time
from math import radians, sin, cos, sqrt, atan2
from collections import deque
from datetime import datetime, date, timedelta
import os
import folium

# =====================
# CONFIGURATIE
# =====================
DB_PATH = "/home/jan/mnt/nas/web/timeline/location_data.db"
# DB_PATH = "/volume1/web/timeline/location_data.db"

MAX_ACC = 20        # meter
MIN_DIST = 3        # meter
SMOOTH_WINDOW = 3

# =====================
# FLASK APP
# =====================

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


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lat REAL,
            lon REAL,
            acc REAL,
            timestamp INTEGER
        )
    """)
    conn.commit()
    conn.close()


def get_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


# =====================
# STATE
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
    lat = data.get("lat")
    lon = data.get("lon")
    acc = data.get("acc")

    if None in (lat, lon, acc):
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

    lat_s = sum(p[0] for p in last_points) / len(last_points)
    lon_s = sum(p[1] for p in last_points) / len(last_points)
    ts = int(time.time())

    cur = db.cursor()
    cur.execute(
        "INSERT INTO locations (lat, lon, acc, timestamp) VALUES (?, ?, ?, ?)",
        (lat_s, lon_s, acc, ts)
    )
    db.commit()

    last_saved_point = (lat_s, lon_s)
    print("Opgeslagen", datetime.fromtimestamp(ts))
    return "ok", 200


@app.route("/")
def timeline():
    day_str = request.args.get("day")
    if day_str:
        day = datetime.strptime(day_str, "%Y-%m-%d").date()
    else:
        day = date.today()

    start_ts = int(datetime.combine(day, datetime.min.time()).timestamp())
    end_ts = int(datetime.combine(day, datetime.max.time()).timestamp())

    cur = db.cursor()
    cur.execute(
        "SELECT lat, lon FROM locations WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp",
        (start_ts, end_ts)
    )
    points = cur.fetchall()

    if points:
        m = folium.Map(location=points[0], zoom_start=13)
        folium.PolyLine(points, color="blue", weight=4).add_to(m)
        folium.Marker(points[0], tooltip="Start").add_to(m)
        folium.Marker(points[-1], tooltip="Einde").add_to(m)
    else:
        m = folium.Map(location=[52.0, 5.0], zoom_start=7)

    map_html = m._repr_html_()

    prev_day = day - timedelta(days=1)
    next_day = day + timedelta(days=1)

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
    print("Init DB")
    init_db()
    db = get_db()
    app.run(host="0.0.0.0", port=5000)

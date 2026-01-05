import sqlite3
import mysql.connector
from config import DB_CONFIG

# CONFIGURATIE
SQLITE_DB = "/home/jan/code_github/timeline/location_data.db"

def migrate():
    # 1. Verbinding maken met beide databases
    print("🔄 Verbinding maken met databases...")
    lite_conn = sqlite3.connect(SQLITE_DB)
    lite_cur = lite_conn.cursor()
    
    maria_conn = mysql.connector.connect(**DB_CONFIG)
    maria_cur = maria_conn.cursor()

    # 2. Data ophalen uit SQLite
    # We halen alles op behalve de 'id' kolom, want MariaDB nummert zelf opnieuw
    print("📖 Data inladen uit SQLite...")
    lite_cur.execute("""
        SELECT readable_time, SSID, acc, alt, batt, bs, cog, conn, 
               created_at, lat, lon, m, source, tid, topic, vac, vel, timestamp 
        FROM locations
    """)
    rows = lite_cur.fetchall()
    print(f"📦 {len(rows)} rijen gevonden.")

    # 3. Data invoegen in MariaDB
    print("✍️ Data wegschrijven naar MariaDB...")
    sql = """
        INSERT INTO locations (
            readable_time, SSID, acc, alt, batt, bs, cog, conn, 
            created_at, lat, lon, m, source, tid, topic, vac, vel, timestamp
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    # We doen dit in één keer voor maximale snelheid
    maria_cur.executemany(sql, rows)
    
    maria_conn.commit()
    print("✅ Migratie voltooid!")

    # Sluiten
    lite_conn.close()
    maria_conn.close()

if __name__ == "__main__":
    migrate()
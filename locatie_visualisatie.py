#!/usr/bin/env python3

'''
Dit script visualiseert de locatiegegevens uit de MariaDB database op een interactieve kaart.

Gebruik:
1. Zorg ervoor dat de databaseverbinding correct is ingesteld in config.py
2. Voer het script uit met: python locatie_visualisatie.py
3. Open de gegenereerde HTML-bestanden in een webbrowser

'''


import mysql.connector
import folium
from datetime import datetime, timedelta
import pytz
from config import DB_CONFIG

def get_db_connection():
    """Maak verbinding met de MariaDB database"""
    return mysql.connector.connect(**DB_CONFIG)

def get_locations_for_date(date_str):
    """Haal locaties op voor een specifieke datum"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Zet de datum om naar de lokale tijdzone
    local_tz = pytz.timezone('Europe/Amsterdam')
    
    try:
        cursor.execute("""
            SELECT lat, lon, readable_time, acc, vel 
            FROM locations 
            WHERE DATE(readable_time) = %s 
            ORDER BY timestamp ASC
        """, (date_str,))
        
        locations = cursor.fetchall()
        
        # Voeg extra informatie toe aan elk punt
        for loc in locations:
            # Controleer of readable_time al een datetime object is
            if isinstance(loc['readable_time'], str):
                loc['datetime'] = datetime.strptime(loc['readable_time'], '%Y-%m-%d %H:%M:%S')
            else:
                loc['datetime'] = loc['readable_time']
        
        return locations
    
    except mysql.connector.Error as e:
        print(f"Fout bij ophalen locaties: {e}")
        return []
    
    finally:
        cursor.close()
        conn.close()

def create_route_map(locations):
    """Maak een Folium-kaart met de route"""
    if not locations:
        return None
    
    # Maak een kaart gecentreerd op het eerste punt
    m = folium.Map(location=[locations[0]['lat'], locations[0]['lon']], zoom_start=13)
    
    # Teken de route
    route_points = [(loc['lat'], loc['lon']) for loc in locations]
    folium.PolyLine(route_points, color='blue', weight=4, opacity=0.8).add_to(m)
    
    # Markeer start- en eindpunt
    folium.Marker(
        [locations[0]['lat'], locations[0]['lon']], 
        popup=f"Start: {locations[0]['readable_time']}", 
        icon=folium.Icon(color='green')
    ).add_to(m)
    
    folium.Marker(
        [locations[-1]['lat'], locations[-1]['lon']], 
        popup=f"Einde: {locations[-1]['readable_time']}", 
        icon=folium.Icon(color='red')
    ).add_to(m)
    
    # Voeg details toe aan elke locatie
    for loc in locations:
        folium.CircleMarker(
            [loc['lat'], loc['lon']],
            radius=3,
            popup=f"Tijd: {loc['readable_time']}, Acc: {loc['acc']}m, Snelheid: {loc['vel']} km/h",
            color='red',
            fill=True,
            fillColor='red'
        ).add_to(m)
    
    return m

def main():
    # Vraag de gebruiker om een datum
    date_input = input("Geef een datum (YYYY-MM-DD) of druk Enter voor vandaag: ")
    
    if not date_input:
        date_input = datetime.now().strftime('%Y-%m-%d')
    
    # Haal locaties op
    locations = get_locations_for_date(date_input)
    
    if not locations:
        print(f"Geen locaties gevonden voor {date_input}")
        return
    
    # Maak de kaart
    route_map = create_route_map(locations)
    
    # Sla de kaart op als HTML
    output_file = f'route_map_{date_input}.html'
    route_map.save(output_file)
    
    print(f"Kaart opgeslagen als {output_file}")
    print(f"Aantal locatiepunten: {len(locations)}")
    print(f"Eerste punt: {locations[0]['readable_time']}")
    print(f"Laatste punt: {locations[-1]['readable_time']}")

if __name__ == "__main__":
    main()
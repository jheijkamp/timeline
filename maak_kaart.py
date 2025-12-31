
import sqlite3
import folium
from datetime import datetime

# Instellingen
DB_PATH = "/home/jan/mnt/nas/web/timeline/location_data.db"
GAP_THRESHOLD_SECONDS = 900  # 15 minuten (900 seconden) zonder data = nieuwe rit

def haal_ritten_op():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT lat, lon, tst, readable_time FROM locations ORDER BY tst ASC")
    punten = cursor.fetchall()
    conn.close()

    if not punten:
        return []

    ritten = []
    huidige_rit = [punten[0]]

    for i in range(1, len(punten)):
        tijd_verschil = punten[i][2] - punten[i-1][2]
        
        if tijd_verschil > GAP_THRESHOLD_SECONDS:
            # Tijdgat gevonden, sla huidige rit op en start nieuwe
            ritten.append(huidige_rit)
            huidige_rit = []
        
        huidige_rit.append(punten[i])
    
    ritten.append(huidige_rit) # Laatste rit toevoegen
    return ritten

def maak_rit_kaart():
    ritten = haal_ritten_op()
    if not ritten:
        print("Geen ritten gevonden.")
        return

    # Start kaart op de laatste bekende locatie
    laatste_punt = ritten[-1][-1]
    m = folium.Map(location=[laatste_punt[0], laatste_punt[1]], zoom_start=13)

    # Voeg voor elke rit een eigen laag toe
    for idx, rit in enumerate(ritten):
        start_tijd = rit[0][3]
        eind_tijd = rit[-1][3]
        rit_naam = f"Rit {idx+1}: {start_tijd.split(' ')[1]} tot {eind_tijd.split(' ')[1]}"
        
        # Maak een groep voor deze rit
        groep = folium.FeatureGroup(name=rit_naam)
        
        # Teken de lijn
        coords = [[p[0], p[1]] for p in rit]
        folium.PolyLine(coords, color="blue", weight=4, opacity=0.6, tooltip=rit_naam).add_to(groep)
        
        # Voeg markers toe voor start en eind van de rit
        folium.Marker([rit[0][0], rit[0][1]], popup=f"START: {start_tijd}", icon=folium.Icon(color='green')).add_to(groep)
        folium.Marker([rit[-1][0], rit[-1][1]], popup=f"EIND: {eind_tijd}", icon=folium.Icon(color='red')).add_to(groep)

        groep.add_to(m)

    # Voeg de laag-selectie rechtsboven toe
    folium.LayerControl().add_to(m)
    
    m.save("ritten_kaart.html")
    print(f"Kaart met {len(ritten)} ritten opgeslagen als 'ritten_kaart.html'")

if __name__ == "__main__":
    maak_rit_kaart()
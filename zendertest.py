import requests
import time

# Instellingen
# NAS_URL = "http://192.168.1.200:5000/pub"  # Pas IP aan naar je NAS
NAS_URL = "http://192.168.1.78:5000/pub"  # Pas IP aan naar je NAS


def stuur_test_locatie(lat, lon, tid="test-laptop"):
    payload = {
        "BSSID": "78:d3:8d:fd:09:dd",
        "SSID": "weiler12",  # SSID point
        "_type": "location",
        "_id": "dfcb9056",  # Unieke ID voor dit bericht
        "acc": 5,  # Nauwkeurigheid 5m
        "alt": 54,  # Hoogte 12m
        "batt": 79,  # Batterij 79%
        "bs": 1,  # 1 = GPS, 2 = WiFi, 3 = Fused (GPS + WiFi)
        "cog": 0,  # Richting 0 graden
        "conn": "w",  # 1 = GPS, 2 = WiFi, 3 = Fused (GPS + WiFi)
        "created_at": 1767293077,  # `{timestamp}`
        "lat": 52.1885381,
        "lon": 5.3213312, 
        "m": 1,  # 1 = GPS, 2 = WiFi, 3 = Fused (GPS + WiFi)
        "source": "fused",  # 1 = GPS, 2 = WiFi, 3 = Fused (GPS + WiFi)
        "tid": "xm",  # Tracker ID
        "topic": "owntracks/ajan/a14xm",  # Topic met username en device
        "tst": 1767292555,  # timestamp
        "vac": 1,  # Verticale nauwkeurigheid 10m
        "vel": 2}  # Snelheid 50 km/u
        

    try:
        response = requests.post(NAS_URL, json=payload)
        print(payload)
        if response.status_code == 200:
            print(f"Succes! Locatie {lat}, {lon} verstuurd.")
        else:
            print(f"Foutmelding van server: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Kon geen verbinding maken met de NAS: {e}")

if __name__ == "__main__":
    # Testpunt ergens in de buurt van Utrecht/Doorn
    stuur_test_locatie(52.0406, 5.3013)
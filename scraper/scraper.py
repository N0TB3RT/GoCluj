import requests
from datetime import datetime
import time

# Adresa backend-ului in interiorul retelei Docker
API_URL = "http://backend:8000/api/events"

def trimite_eveniment_test():
    # Acest dictionar respecta exact contractul din schemas.py (Pydantic)
    eveniment = {
        "title": "Concert Test Cluj",
        "description": "Acesta este un eveniment extras automat.",
        "event_date": datetime.now().isoformat(),
        "location_name": "BT Arena",
        "price_info": "50 RON",
        "is_free": False,
        "source_url": "https://exemplu.ro/concert-test-1", # Trebuie sa fie unic!
        "category_id": None
    }

    try:
        print(f"Trimit evenimentul către {API_URL}...")
        response = requests.post(API_URL, json=eveniment)
        
        if response.status_code == 200:
            print("Succes! Eveniment salvat:", response.json())
        else:
            print(f"Eroare {response.status_code}:", response.text)
            
    except requests.exceptions.RequestException as e:
        print("Eroare de conexiune la Backend:", e)

if __name__ == "__main__":
    # Punem o pauza la pornire ca sa ne asiguram ca backend-ul a pornit primul
    time.sleep(5)
    trimite_eveniment_test()
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd

# Stundu saraksta URL adreses katrai klasei no 1. līdz 12.
urls = [
    f"https://www.r40vsk.lv/lv/macdarbs/stsar{kl}kl/"
    for kl in range(1, 13)
]

# Teksta normalizācija kabinetu nosaukumiem
ROOM_NAMES = {
    "sporta zāle": "sporta_zale",
    "aktu zāle": "aktu_zale"
}

# Manuālas korekcijas konkrētu kabinetu tipam un ietilpībai
ROOM_FIXES = {
    "A-aktu-zale": {"type": "sport", "capacity": 90},
    "A-sporta-zale": {"type": "sport", "capacity": 30},
    "A-305": {"type": "computer"},
    "T-301": {"type": "computer"},
    "T-303": {"capacity": 20},
    "T-304": {"type": "computer"},
    "T-309": {"type": "chemistry"},
    "T-401": {"capacity": 20},
    "T-403": {"capacity": 20},
    "T-404": {"capacity": 20},
    "T-405": {"capacity": 20},
}

# Kabineta identifikatora ģenerēšana
def room_id(building, room):
    room = room.replace(".", "-")
    if room in ["sporta_zale", "aktu_zale"]:
        return f"{building}-" + room.replace("_", "-")
    return f"{building}-{room}"

# Mazo kabinetu ietilpības noteikšana
def letter_capacity(room_id):
    if re.search(r"-\d{3}-[ab]$", room_id):
        return 20
    return 30

records = []

# Datu izgūšana no katras klases stundu saraksta lapas
for kl, url in enumerate(urls, start=1):
    response = requests.get(url)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")

    text = soup.get_text().lower()

    rooms = set(re.findall(r'\b\d{3}(?:\.[a-z])?\b', text))

    for name, code in ROOM_NAMES.items():
        if name in text:
            rooms.add(code)

    # 1.-5. klases skolēni un 6.-12. klases skolēni mācās atsevišķās ēkās
    building = "Akas" if kl <= 5 else "Tērbatas"

    # Kabinetu ierakstu izveide
    for room in rooms:
        rid = room_id(building[0], room)
        record = {
            "room_id": rid,
            "room": room,
            "building": building,
            "type": "classroom",
            "capacity": letter_capacity(rid)
        }
        if rid in ROOM_FIXES:
            record.update(ROOM_FIXES[rid])
        records.append(record)

records.append({
    "room_id": "T-sporta-zale",
    "room": "sporta_zale",
    "building": "Tērbatas",
    "type": "sport",
    "capacity": 60
})

# Rezultātu saglabāšana CSV failā
df = pd.DataFrame(records)
df = df.drop_duplicates()
df = df.sort_values("room_id")
df.to_csv("data/rooms.csv", index=False, encoding="utf-8")

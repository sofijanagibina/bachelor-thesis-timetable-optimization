import re
import requests
from bs4 import BeautifulSoup
import pandas as pd

# Ielāde pedagoģisko darbinieku saraksta lapu
url = "https://www.r40vsk.lv/lv/parskolu/psaraksts/"
response = requests.get(url)
response.encoding = "utf-8"
soup = BeautifulSoup(response.text, "html.parser")

# Atslēgvārdi skolotāja amata noteikšanai
TEACHERS_LIST = ["pasniedzējs", "pasniedzēja", "skolotājs", "skolotāja"]

# Priekšmetu nosaukumu normalizācija
SUBJECTS_DICT = {
    "Latviešu valodas un literatūras": "Latviešu valoda un literatūra",
    "Latviešu valodas":                "Latviešu valoda",
    "Matemātikas":                     "Matemātika",
    "Sociālo zinību":                  "Sociālās zinības",
    "Bioloģijas":                      "Bioloģija",
    "Fizikas":                         "Fizika",
    "Angļu valodas":                   "Angļu valoda",
    "Teātra mākslas":                  "Teātra māksla",
    "Vācu valodas":                    "Vācu valoda",
    "Datorikas":                       "Datorika",
    "Dizaina un tehnoloģiju":          "Dizains un tehnoloģijas",
    "Inženierzinību":                  "Inženierzinības",
    "Mūzikas":                         "Mūzika",
    "Ķīmijas":                         "Ķīmija",
    "Ķīmij as":                        "Ķīmija", 
    "Dabaszinību":                     "Dabaszinības",
    "Sporta un veselības":             "Sports un veselība",
    "Vizuālās mākslas":                "Vizuālā māksla",
    "Uzņēmējdarbības pamatu":          "Uzņēmējdarbības pamati",
    "Ekonomikas":                      "Ekonomika",
    "Kultūras pamatu":                 "Kultūras pamati",
    "Krievu valodas un literatūras":   "Krievu valoda un literatūra",
    "Programmēšanas":                  "Programmēšana", 
    "Sociālo zinību un vēstures":      "Sociālās zinības un vēsture",
    "Vēstures":                        "Vēsture",
    "Ģeogrāfijas":                     "Ģeogrāfija",
    "Lietišķās angļu valodas":         "Lietišķā angļu valoda", 
    "Angļu literatūras":               "Angļu literatūra", 
    "Latviešu literatūras":            "Latviešu literatūra",
}

# Ieraksti, kas nav mācību priekšmeti
NOT_SUBJECTS = {
    "Pagarinātās dienas grupas",
    "Interešu izglītības",
    "Direktora vietniece",
    "Direktora vietnieks",
}

# Skolotāju tabulas atrašana lapā
all_tables = soup.find_all("table")
for t in all_tables:
    heading = t.find_previous("h1")
    if heading and "pedagoģisko darbinieku saraksts" in heading.get_text(strip=True).lower():
        teacher_table = t
        break

# Pārbauda, vai tekstā ir skolotāja amata nosaukums
def is_teaching_role(text):
    return any(tl in text.lower() for tl in TEACHERS_LIST)

# Klašu apzīmējumu iegūšana no teksta
def extract_classes(text):
    return sorted(set(re.findall(r"\d{1,2}\.[a-zA-Z]", text)))

# Skolotāja vārda un uzvārda iegūšana
def give_name(cell):
    first_name = ""
    last_name = ""
    for p in cell.find_all("p"):
        text = p.get_text(" ", strip=True)
        strong = p.find("strong")
        if strong:
            last_name = strong.get_text(strip=True)
            text = text.replace(last_name, "").strip()
        if text:
            first_name = text
    return first_name, last_name

# Priekšmeta nosaukuma sakārtošana
def normalize_subject(text):
    text = text.strip()
    text = SUBJECTS_DICT.get(text, text)
    if any(ns in text for ns in NOT_SUBJECTS):
        return None
    return text

# Priekšmetu un klašu iegūšana no tabulas šūnas
def parse_cell(cell):
    subjects = []
    classes = []

    paragraphs = cell.find_all("p") or [cell]
    for p in paragraphs:
        full_text = p.get_text(" ", strip=True)

        teacher_pos = None
        for tl in TEACHERS_LIST:
            pos = full_text.lower().find(tl)
            if pos != -1:
                teacher_pos = pos

        if teacher_pos is None:
            continue

        raw_subject = full_text[:teacher_pos].strip()

        subject = normalize_subject(raw_subject)
        if subject:
            subjects.append(subject)

        classes = extract_classes(cell.get_text(" ", strip=True))

    return subjects, classes

# Ierakstu veidošana skolotāju, skolotju-priekšmetu un skolotju-klašu tabulām
full_records, subject_records, class_records = [], [], []
rows = teacher_table.find_all("tr")

for i, row in enumerate(rows):
    if i == 0:
        continue
    cells = row.find_all(["td"])

    first_name, last_name = give_name(cells[1])
    subjects, classes = parse_cell(cells[2])
    if not subjects:
        continue
    tid = f"T{i:03d}"

    full_records.append({
        "teacher_id": tid,
        "first_name": first_name,
        "last_name": last_name,
        "subjects": "; ".join(subjects),
    })

    for subject in subjects:
        subject_records.append({"teacher_id": tid, "subject": subject})
        for cl in classes:
            class_records.append({
                "teacher_id": tid,
                "subject": subject,
                "class": cl
            })

df_full = pd.DataFrame(full_records)
df_subjects = pd.DataFrame(subject_records).drop_duplicates() if subject_records else pd.DataFrame(columns=["teacher_id","subject"])
df_classes = pd.DataFrame(class_records).drop_duplicates() if class_records else pd.DataFrame(columns=["teacher_id","subject","class"])

# Rezultātu saglabāšana CSV failos
df_full.to_csv("data/teachers_full.csv", index=False, encoding="utf-8")
df_subjects.to_csv("data/teachers_subjects.csv", index=False, encoding="utf-8")
df_classes.to_csv("data/teacher_classes.csv", index=False, encoding="utf-8")

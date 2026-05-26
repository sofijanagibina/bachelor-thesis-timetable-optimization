import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
import math

# Ielāde izglītības programmas lapu
url = "https://www.r40vsk.lv/lv/macdarbs/izglprog/"
response = requests.get(url)
response.encoding = "utf-8"
soup = BeautifulSoup(response.text, "html.parser")

# Priekšmeti, kas netiek iekļauti modelī, jo tiem ir specifiskas īpašības
EXCLUDE_SUBJECTS = [
    "Valsts aizsardzības mācība",
    "Projekta darbs",
]

# Stundu skaita nolasīšana no tabulas šūnas
def parse_cell(raw):
    raw = raw.strip()
    if not raw:
        return None, False

    raw = raw.replace(",", ".")

    if "/" in raw:
        _, right = raw.split("/", 1)
        value = int(right)
        return value, True  

    value = math.ceil(float(raw))
    return value, False

# Rindas izvēršana, ņemot vērā colspan
def expand_row(row):
    result = []
    col = 0
    for cell in row.find_all(["th", "td"]):
        text = cell.get_text(" ", strip=True)
        span = int(cell.get("colspan", 1))
        for _ in range(span):
            result.append((col, text, cell))
            col += 1
    return result

# Klases numura noteikšana no virsraksta teksta
def extract_grade(text):
    text = text.strip()
    kl = re.search(r"\b(\d{1,2})\s*\.?\s*kl", text, re.IGNORECASE)
    if kl:
        g = int(kl.group(1))
        if 1 <= g <= 12:
            return g
    return None

# Kopējā stundu skaita kolonnu izlaišana
def is_total_col(text):
    t = text.lower()
    return "kopēj" in t or ("stund" in t and "kl" not in t)

# Klases kolonnu atrašana tabulas galvenē
def get_grade_columns(header_row):
    expanded = expand_row(header_row)
    grade_cols = {}
    seen_cols = set()
    for col_pos, text, _ in expanded:
        if col_pos in seen_cols:
            continue
        seen_cols.add(col_pos)
        if col_pos == 0:
            continue
        if is_total_col(text):
            continue
        grade = extract_grade(text)
        if grade is not None:
            grade_cols[col_pos] = grade
    return grade_cols

# Tuvākā programmas virsraksta atrašana
def nearest_heading(tag):
    for sibling in tag.find_all_previous(["h2", "h3", "h4"]):
        text = sibling.get_text(strip=True)
        if text:
            return text
    return "unknown"

# Numerācijas rindu izlaišana
def is_numbering_row(text):
    return bool(re.fullmatch(r"\s*\d+\.?\s*", text))

# Sporta sadalīšana praktiskajā un teorijas daļā
def split_sport(grade, subject):
    return [
        {
            "grade": grade,
            "program": None,
            "subject": f"{subject} (praktiskā)",
            "lessons_per_week": 2,                
            "optional": False
            },
            {
            "grade": grade,
            "program": None,
            "subject": f"{subject} (teorija)",
            "lessons_per_week": 1,
            "optional": False
        }
    ]

all_records = []
tables = soup.find_all("table")

# Priekšmetu datu nolasīšana no visām tabulām
for table_idx, table in enumerate(tables):
    rows = table.find_all("tr")
    if len(rows) < 2:
        continue

    grade_cols = {}
    header_row_idx = None
    for candidate_idx in range(min(3, len(rows))):
        grade_cols = get_grade_columns(rows[candidate_idx])
        if grade_cols:
            header_row_idx = candidate_idx
            break

    if not grade_cols:
        continue

    grades_in_table = sorted(grade_cols.values())
    program_label = (
        "Pamatizglītība"
        if min(grades_in_table) <= 9
        else nearest_heading(table)
    )

    for row in rows[header_row_idx + 1:]:
        expanded = expand_row(row)
        if not expanded:
            continue

        subject = expanded[0][1]
        if not subject:
            continue

        if subject in EXCLUDE_SUBJECTS:
            continue

        if is_numbering_row(subject):
            continue

        if expanded[0][2].find(["strong", "b"]):
            continue

        row_values = {}
        seen = set()
        for col_pos, text, _ in expanded:
            if col_pos not in seen:
                row_values[col_pos] = text
                seen.add(col_pos)

        for col_pos, grade in grade_cols.items():
            raw = row_values.get(col_pos, "")
            lessons, optional = parse_cell(raw)
            if lessons is None:
                continue

            if subject == "Sports un veselība" and lessons == 3:
                split_rows = split_sport(grade, subject)

                for r in split_rows:
                    r["program"] = program_label
                    r["optional"] = optional
                    all_records.append(r)
            else:
                all_records.append({
                    "grade": grade,
                    "program": program_label,
                    "subject": subject,
                    "lessons_per_week": lessons,
                    "optional": optional,
                })

df = pd.DataFrame(all_records)

# Manuāli pievienota trūkstoša rinda
missing_row = pd.DataFrame([{
    "grade": 11,
    "program": "Uzņēmējdarbības pamati",
    "subject": "Ķīmija I",
    "lessons_per_week": 2,
    "optional": False
}])
df = pd.concat([df, missing_row], ignore_index=True)

# Rezultātu saglabāšana CSV failā
df = df.sort_values(["grade", "program", "subject"]).reset_index(drop=True)
df = df[["grade", "program", "subject", "lessons_per_week", "optional"]]
df.to_csv("data/subjects.csv", index=False, encoding="utf-8")

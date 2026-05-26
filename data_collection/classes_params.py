import pandas as pd

# Klašu saraksta ielāde no skolotāju-klašu datiem
classes = pd.read_csv("data/teacher_classes.csv")[["class"]].drop_duplicates()
classes["grade"] = classes["class"].str.extract(r"(\d+)").astype(int)
classes["letter"] = classes["class"].str.extract(r"\.(\w+)")
classes = classes.sort_values(["grade", "letter"])

rows = []

# Dienas parametru noteikšana katrai klasei
for c in classes["class"].unique():
    grade = int(''.join(filter(str.isdigit, c)))

    if grade <= 4:
        max_per_day = 6
    elif grade <= 9:
        max_per_day = 8
    else:
        max_per_day = 9

    min_start = 0

    rows.append({
        "class": c,
        "max_per_day": max_per_day,
        "min_start": min_start
    })

# Rezultāta saglabāšana CSV failā
df_classes = pd.DataFrame(rows)
df_classes.to_csv("data/class_params.csv", index=False, encoding="utf-8")

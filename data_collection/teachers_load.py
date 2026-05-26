import pandas as pd
import random

# Fiksēts seed reproducējamiem datiem
random.seed(43)

# Skolotāju saraksta ielāde
teachers = pd.read_csv("data/teachers_full.csv")

rows = []

# Nejauši ģenerēti dienas slodzes ierobežojumi
for tid in teachers["teacher_id"].unique():
    max_day = random.randint(6, 8)      
    min_day = random.randint(3, 5)

    rows.append({
        "teacher_id": tid,
        "max_day": max_day,
        "min_day": min_day
    })

# Rezultāta saglabāšana CSV failā
df = pd.DataFrame(rows)
df.to_csv("data/teacher_load.csv", index=False, encoding="utf-8")

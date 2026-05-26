import pandas as pd
import random

# Fiksēts seed reproducējamiem datiem
random.seed(42)

# Skolotāju saraksta ielāde
teachers = pd.read_csv("data/teachers_full.csv")
DAYS = list(range(5))
PERIODS = list(range(10))

# Nejauši ģenerēta skolotāju pieejamība ar 15% varbūtību
rows = []
for tid in teachers["teacher_id"]:
    for d in DAYS:
        for p in PERIODS:
            if random.random() < 0.15:
                available = 0
            else:
                available = 1
            rows.append({
                "teacher_id": tid,
                "day": d + 1,
                "period": p,
                "available": available
            })

# Rezultāta saglabāšana CSV failā
df = pd.DataFrame(rows)
df.to_csv("data/teacher_availability.csv", index=False, encoding="utf-8")

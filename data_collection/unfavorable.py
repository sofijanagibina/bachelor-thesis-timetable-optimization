import pandas as pd
import random

# Fiksēts seed reproducējamiem datiem
random.seed(44)

# Skolotāju pieejamības datu ielāde
avail = pd.read_csv("data/teacher_availability.csv")
rows = []

# Nejauši ģenerēti skolotājiem nevēlamie laiki ar 8% varbūtību
for _, row in avail.iterrows():
    if row["available"] == 0:
        unf = 0
    else:
        unf = 1 if random.random() < 0.08 else 0 
    rows.append({
        "teacher_id": row["teacher_id"],
        "day": row["day"],
        "period": row["period"],
        "unfavorable": unf
    })

# Rezultāta saglabāšana CSV failā
pd.DataFrame(rows).to_csv("data/teacher_unfavorable.csv", index=False, encoding="utf-8")

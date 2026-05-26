import requests
from bs4 import BeautifulSoup
import pandas as pd

# Ielāde zvanu saraksta lapu
url = "https://www.r40vsk.lv/lv/macdarbs/zvani"
response = requests.get(url)
response.encoding = "utf-8"
soup = BeautifulSoup(response.text, "html.parser")

# Tabula ar periodu informāciju
table = soup.find("table")
rows = table.find_all("tr")

periods = []

# Savākt periodu datus no tabulas
for row in rows:
    cells = row.find_all("td")
    if len(cells) == 2:
        label = cells[0].text.strip()   
        time  = cells[1].text.strip()   
    
        period_num = label.split(".")[0].strip()
        start, end = time.split("-")
        
        periods.append({
            "period": int(period_num),
            "label": label,
            "start": start.strip(),
            "end": end.strip()
        })

# Rezultātu saglabāšana CSV failā
df_periods = pd.DataFrame(periods)
df_periods.to_csv("data/periods.csv", index=False, encoding="utf-8")

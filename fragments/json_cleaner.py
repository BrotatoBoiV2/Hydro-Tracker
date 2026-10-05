import json
import pandas as pd
from pathlib import Path


def convert_data():
    df = pd.read_excel(Path('~/.hydro/current_bill.xlsx').expanduser(), header=2)
    date_col = df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col], unit='ms').dt.strftime('%Y-%m-%d')
    df = df.dropna(subset=[date_col])
    df.to_json(Path('~/.hydro/dirty_bill.json').expanduser(), orient='records', indent=4)


def clean_data():
    convert_data()

    with open(Path("~/.hydro/dirty_bill.json").expanduser(), "r", encoding="utf-8") as file:
        data = json.load(file)

    entries = {}
    cur_use = 0.0
    cur_cost = 0.0

    for usage in data:
        date = usage["Date"]
        entries[date] = {
            "Special_Usage": usage["ULO Weekend (kWh)"],
            "Medium_Usage": usage["ULO Mid-peak (kWh)"],
            "High_Usage": usage["ULO On-peak (kWh)"],
            "Night_Usage": usage["ULO Overnight (kWh)"],
            "Total_Usage": usage["Total (kWh)"],
            "Special_Cost": usage["ULO Weekend ($)"],
            "Medium_Cost": usage["ULO Mid-peak ($)"],
            "High_Cost": usage["ULO On-peak ($)"],
            "Night_Cost": usage["ULO Overnight ($)"],
            "Total_Cost": usage["Total ($)"],
            "Min_Temp": usage["Minimum Temperature \u00b0C"],
            "Max_Temp": usage["Maximum Temperature \u00b0C"]
        }
        cur_use += entries[date]["Total_Usage"]
        cur_cost += entries[date]["Total_Cost"]
        
    final = {
        "Records": entries,
        "Current_Usage": float(f"{cur_use:.2f}"),
        "Current_Cost": float(f"{cur_cost:.2f}")
    }

    with open(Path("~/.hydro/current_bill.json").expanduser(), "w") as file:
        json.dump(final, file, indent=4)
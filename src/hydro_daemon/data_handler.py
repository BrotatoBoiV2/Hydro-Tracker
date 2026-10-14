import time
import os
import json
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
import selenium.webdriver.firefox.webdriver 
from selenium.webdriver.common.by import By
import subprocess
from pathlib import Path
import shutil
import pandas as pd

BASE_DIR = Path("~/.hydro").expanduser()
BASE_DIR.mkdir(parents=True, exist_ok=True)
SYSTEMD_PATH = "/etc/systemd/system/"
SECURE_PASS_BIN = Path(__file__).parent / "lib/secure_pass"
    

def obtain_data():
    with open(BASE_DIR / "config.json", "r") as file:
        config = json.load(file)
        login_url = "https://account.hydroottawa.com/login"
        login_email = config["Login_Email"]
        enc_password = config.get("Login_Password", "")
        dec_pass_res = subprocess.run([SECURE_PASS_BIN, enc_password, "--decrypt"], capture_output=True)
        login_password = dec_pass_res.stdout.decode('utf-8').replace('\n', '')

    os.environ["MOZ_HEADLESS"] = "1"
    options = Options()
    options.add_argument("--headless")
    
    driver = webdriver.Firefox(options=options)

    try: # This shii ugly...
        driver.get(login_url)

        time.sleep(5)

        print("Logging in...")

        email_field = driver.find_element(By.ID, "EmailAddress")
        password_field = driver.find_element(By.ID, "LoginPassword")
        
        email_field.send_keys(str(login_email))
        password_field.send_keys(str(login_password))
        
        login_button = driver.find_element(By.ID, "LoginSubmitButton")
        login_button.click()

        print("Logged in!")

        time.sleep(10)

        usage_button = driver.find_element(By.ID, "usage")
        driver.execute_script("arguments[0].click();", usage_button)

        time.sleep(3)

        download_button = driver.find_element(By.ID, "download")
        driver.execute_script("arguments[0].click();", download_button)

        time.sleep(3)

        download_excel = driver.find_element(By.ID, "UsageDownloadExcel")
        driver.execute_script("arguments[0].click();", download_excel)

        time.sleep(3)

        downloaded_file = Path("~/Downloads/Current billing period.xlsx").expanduser()
        subprocess.run(["mv", downloaded_file, BASE_DIR / "current_bill.xlsx"])

        print("File saved!")

    except Exception as e:
        print(f"An error occured: {e}")

def convert_data():
    print("Converting")
    print(BASE_DIR / 'current_bill.xlsx')
    df = pd.read_excel(BASE_DIR / 'current_bill.xlsx', header=2)
    print(f"Processing {df}")
    date_col = df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col], unit='ms').dt.strftime('%Y-%m-%d')
    df = df.dropna(subset=[date_col])
    df.to_json(BASE_DIR / 'dirty_bill.json', orient='records', indent=4)


def clean_data():
    print("Cleaning/....")
    convert_data()

    with open(BASE_DIR / "dirty_bill.json", "r", encoding="utf-8") as file:
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


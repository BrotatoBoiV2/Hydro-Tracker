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
from selenium.webdriver.firefox.service import Service

from utils import log_to_file


BASE_DIR = Path("~/.hydro").expanduser()
BASE_DIR.mkdir(parents=True, exist_ok=True)
SYSTEMD_PATH = "/etc/systemd/system/"
SECURE_PASS_BIN = Path(__file__).parent / "lib/secure_pass"
    

def obtain_data(pass_client, cryptograph, hash):
    config_path = BASE_DIR / "config.json"
    if not config_path.exists():
        return False
        
    with open(BASE_DIR / "config.json", "r") as file:
        config = json.load(file)
        login_url = "https://account.hydroottawa.com/login"
        login_email = config["Login_Email"]
        enc_password = config.get("Login_Password", "")
        dec_pass = pass_client.send_request("decrypt", enc_password, hash)
        login_password = cryptograph.decrypt(dec_pass)

    options = Options()
    options.add_argument("-headless")
    options.binary_location = "/usr/bin/firefox" 
    service = Service(log_output="geckodriver.log")
    driver = webdriver.Firefox(service=service, options=options)

    try: # This shii ugly...
        driver.get(login_url)

        time.sleep(5)

        log_to_file("Logging in...")

        email_field = driver.find_element(By.ID, "EmailAddress")
        password_field = driver.find_element(By.ID, "LoginPassword")
        
        email_field.send_keys(str(login_email))
        password_field.send_keys(str(login_password))
        
        login_button = driver.find_element(By.ID, "LoginSubmitButton")
        login_button.click()

        log_to_file("Logged in!")

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

        log_to_file("File saved!")

    except Exception as e:
        log_to_file(f"An error occured: {e}")

    finally:
        driver.quit()

def convert_data():
    log_to_file("Converting")
    df = pd.read_excel(BASE_DIR / 'current_bill.xlsx', header=2)
    log_to_file(f"Processing {df}")
    date_col = df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col], unit='ms').dt.strftime('%Y-%m-%d')
    df = df.dropna(subset=[date_col])
    df.to_json(BASE_DIR / 'dirty_bill.json', orient='records', indent=4)


def clean_data():
    log_to_file("Cleaning....")
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


if __name__ == '__main__':
    from password_client import PasswordClient, LocalCryptograph, ClientHash

    # LOCAL_HASH  = ClientHash().client_hash
    # PASS_CLIENT = PasswordClient()
    # CRYPTOGRAPH = LocalCryptograph()
    obtain_data()


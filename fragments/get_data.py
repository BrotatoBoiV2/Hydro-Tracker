import time
import os
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
import selenium.webdriver.firefox.webdriver 
from selenium.webdriver.common.by import By
from dotenv import load_dotenv
import subprocess
from pathlib import Path
import shutil

load_dotenv()

URL = os.getenv("LOGIN_URL")
EMAIL = os.getenv("LOGIN_EMAIL")
PASS = os.getenv("LOGIN_PASS")
os.environ["MOZ_HEADLESS"] = "1"
OPTIONS = Options()
OPTIONS.add_argument("--headless")

def obtain_data():
    driver = webdriver.Firefox(options=OPTIONS)

    try: # This shii ugly...
        driver.get(URL)

        time.sleep(3)
        print("Logging in...")
        email_field = driver.find_element(By.ID, "EmailAddress")
        password_field = driver.find_element(By.ID, "LoginPassword")
        
        email_field.send_keys(str(EMAIL))
        password_field.send_keys(str(PASS))
        
        login_button = driver.find_element(By.ID, "LoginSubmitButton")
        login_button.click()
        print("Logged in!")
        time.sleep(5)

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
        subprocess.run(["mv", downloaded_file, Path("~/.hydro/current_bill.xlsx").expanduser()])
        print("File saved!")

    except Exception as e:
        print(f"An error occured: {e}")


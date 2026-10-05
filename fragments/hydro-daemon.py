from get_data import obtain_data
from json_cleaner import clean_data
from pathlib import Path

Path("~/.hydro").expanduser().mkdir(parents=True, exist_ok=True)
obtain_data()
clean_data()

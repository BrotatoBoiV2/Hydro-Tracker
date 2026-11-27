from pathlib import Path

LOG_FILE = Path("~/.hydro/program.log").expanduser()

def log_to_file(message):
    with open(LOG_FILE, "a") as file:
        file.write(message)


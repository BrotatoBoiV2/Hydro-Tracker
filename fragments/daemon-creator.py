"""nano /etc/systemd/system/my_scheduled_script.service

[Unit]
Description=Runs my python script on a schedule
After=network.target

[Service]
Type=oneshot
User=your_linux_username
WorkingDirectory=/path/to/your/script_directory
ExecStart=/usr/bin/python3 /path/to/your/script_directory/your_script.py


/etc/systemd/system/my_scheduled_script.timer

[Unit]
Description=Timer to trigger my python script

[Timer]
# Schedule configuration
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
"""
import getpass
from pathlib import Path


SYSTEMD_PATH = "./etc/systemd/system/" # Remove the `.` in prod.


def create_service(time):
    service_content = f"""
    [Unit]
    Description=Obtains hydro data and cleans it for processing.
    After=network.target

    [Service]
    Type=oneshot
    User={getpass.getuser()}
    ExecStart=/usr/bin/hydro-daemon
    """
    timer_content = f"""
    [Unit]
    Description=Timer for the Hydro Tracker Daemon caller.

    [Timer]
    # Schedule configuration
    OnCalendar=*-*-* {time}
    Persistent=true

    [Install]
    WantedBy=timers.target
    """

    Path(SYSTEMD_PATH).mkdir(parents=True, exist_ok=True)

    with open(f'{SYSTEMD_PATH}hydro-tracker.service', "w") as file:
        file.write(service_content)
    
    with open(f'{SYSTEMD_PATH}hydro-tracker.timer', 'w') as file:
        file.write(timer_content)
        

if __name__ == '__main__':
    create_service("03:00:00")
#!/usr/bin/env python
import json
import sys
import subprocess
from pathlib import Path
import getpass

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.widgets import ContentSwitcher, Footer, Header, Static, Input, Button, Label
from textual_timepiece.pickers import TimePicker
from whenever import Time
from datetime import datetime

# Import data handlers if available, otherwise define safe fallbacks/placeholders
try:
    from data_handler import obtain_data, clean_data, BASE_DIR
except ImportError as ie:
    print(f"Could not import the data handler: {ie}")
    BASE_DIR = Path("~/.hydro").expanduser()
    def obtain_data(): pass
    def clean_data(): pass


SYSTEMD_PATH = "/etc/systemd/system/"
SECURE_PASS_BIN = Path(__file__).parent / "lib/secure_pass"


def update_data():
    print("Obtaining data...")
    obtain_data()
    print("Data obtained, now cleaning it...")
    clean_data()
    print("Data is cleaned and ready to use!")


class HydroApp(App):
    CSS = """
    Screen {
        align: center middle;
    }
    
    /* Main Mode Switcher Container */
    #main-switcher {
        width: 74;
        height: 32;
        background: black;
    }

    /* Tracker UI Styling */
    #tracker-container {
        width: 70;
        height: 30;
        border: round red;
        padding: 1 2;
        background: black;
    }
    #record-content {
        height: 15;
        color: purple;
        content-align: left top;
        border-top: dashed lime;
    }
    #record-footer {
        height: 10;
        content-align: left middle;
        text-style: bold;
        color: magenta;
        border-top: dashed lime;
    }

    /* Daemon UI Styling */
    #daemon-container {
        width: 70;
        height: 30;
        border: round red;
        padding: 1 2;
        background: black;
    }
    .menu-header {
        height: 3;
        content-align: center middle;
        text-style: bold;
        color: yellow;
        border-bottom: dashed lime;
    }
    .menu-content {
        height: 30;
        color: purple;
        content-align: left top;
    }
    .menu-footer {
        height: 5;
        content-align: left middle;
        text-style: bold;
        color: magenta;
    }
    Horizontal Static {
        width: auto;
    }
    Input {
        margin-left: 10;
        width: 40;
    }
    TimePicker {
        margin-left: 10;
        width: 40;
    }
    Horizontal {
        height: 3;
        margin-bottom: 1;
    }
    .save-btn {
        width: 5;
    }
    """

    BINDINGS = [
        Binding("ctrl+m", "toggle_mode", "Toggle Mode (Tracker/Daemon)", priority=True),
        Binding("left", "prev_page", "Previous Page"),
        Binding("right", "next_page", "Next Page"),
        Binding("q", "quit", "Quit"),
        Binding("ctrl+s", "toggle_settings", "Settings", priority=True),
        Binding("ctrl+l", "toggle_logs", "Logs", priority=True),
        Binding("ctrl+d", "toggle_daemon", "Daemon", priority=True),
        Binding("ctrl+r", "update_info", "Refresh", priority=True),
        Binding("ctrl+u", "update_data_action", "Update Data", priority=True)
    ]

    def __init__(self):
        super().__init__()
        # Tracker state initialization
        self.records, self.cost, self.usage = self._get_records()
        self.record_list = list(self.records.items())
        self.total = len(self.record_list)
        self.index = self.total - 1 if self.total > 0 else 0
        
        # Daemon state initialization
        self.menu = "tracker"
        self.last_menu = "daemon"
        self.config_file = BASE_DIR / "config.json"
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        self.config = self.get_config()

        # Overall app mode: "tracker" or "daemon"
        self.mode = "tracker"

    def _get_records(self):
        try:
            with open(Path("~/.hydro/current_bill.json").expanduser(), "r") as file:
                data = json.load(file)
            return data["Records"], data["Current_Cost"], data["Current_Usage"]
        except Exception:
            return {}, "0.00", "0.00"

    def check_status(self) -> str:
        try:
            result = subprocess.run(
                ["systemctl", "status", 'hydro_tracker.service'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            if result.returncode == 0:
                return "RUNNING"
            elif result.returncode == 3:
                return "STOPPED"
            elif result.returncode == 4:
                return "DOES NOT EXIST"
            else:
                return "ERROR: CHECK LOGS OR CREATE DAEMON"
        except FileNotFoundError:
            return "SYSTEMCTL NOT FOUND"

    def get_config(self) -> dict:
        if self.config_file.is_file():
            try:
                with open(self.config_file, "r") as file:
                    return json.load(file)
            except json.JSONDecodeError:
                return {}
        return {}

    @on(Button.Pressed, "#save-btn")
    def save_config(self) -> None:
        login_email = self.query_one("#login-email", Input).value
        login_password = self.query_one("#login-password", Input).value
        refresh_time = f"{self.query_one('#refresh-time', TimePicker).value}"
        
        try:
            enc_pass_res = subprocess.run([SECURE_PASS_BIN, login_password, "--encrypt"], capture_output=True)
            enc_pass = enc_pass_res.stdout.decode('utf-8').replace('\n', '')
        except Exception:
            enc_pass = login_password

        data = {
            "Login_Email": login_email,
            "Login_Password": enc_pass,
            "Refresh_Time": refresh_time
        }

        with open(self.config_file, "w") as file:
            json.dump(data, file, indent=4)

        self.config = self.get_config()

    @on(Button.Pressed, "#start-daemon")
    def start_daemon(self) -> None:
        subprocess.run(["systemctl", "enable", "hydro_tracker.service"])
        subprocess.run(["systemctl", "start", "hydro_tracker.service"])
        self.action_update_info()

    @on(Button.Pressed, "#kill-daemon")
    def kill_daemon(self) -> None:
        subprocess.run(["systemctl", "disable", "hydro_tracker.service"])
        subprocess.run(["systemctl", "stop", "hydro_tracker.service"]) 
        self.action_update_info()

    @on(Button.Pressed, "#create-service")
    def create_service(self) -> None:
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
        OnCalendar=*-*-* {self.config.get("Refresh_Time", "00:00:00")}
        Persistent=true

        [Install]
        WantedBy=timers.target
        """

        Path(SYSTEMD_PATH).mkdir(parents=True, exist_ok=True)

        with open(f'{SYSTEMD_PATH}hydro_tracker.service', "w") as file:
            file.write(service_content)
        
        with open(f'{SYSTEMD_PATH}hydro_tracker.timer', 'w') as file:
            file.write(timer_content)

    def compose(self) -> ComposeResult:
        yield Header()

        with ContentSwitcher(initial="tracker", id="main-switcher"):
            # --- TRACKER VIEW ---
            with Container(id="tracker-container"):
                yield Static(id="record-header")
                yield Static(id="record-content")
                yield Static(id="record-footer")

            # --- DAEMON VIEW ---
            with Container(id="daemon-container"):
                with ContentSwitcher(initial=self.menu, id="menu-switcher"):
                    with Container(id="settings", classes="menu-content"):
                        email = self.config.get("Login_Email", "")
                        enc_password = self.config.get("Login_Password", "")
                        try:
                            dec_pass_res = subprocess.run([SECURE_PASS_BIN, enc_password, "--decrypt"], capture_output=True)
                            password = dec_pass_res.stdout.decode('utf-8').replace('\n', '')
                        except Exception:
                            password = enc_password
                        refresh_time = self.config.get("Refresh_Time", "00:00:00")

                        yield Static("Settings", classes="menu-header")
                        
                        with Horizontal():
                            yield Static("Email       : ")
                            yield Input(placeholder="Login Email", id="login-email", value=email)

                        with Horizontal():
                            yield Static("Password    : ")
                            yield Input(password=True, placeholder="Login Password", id="login-password", value=password)
                        
                        with Horizontal():
                            yield Static("Update Time : ")
                            yield TimePicker(Time(refresh_time), id="refresh-time")

                        yield Button("Save!", id="save-btn", variant="primary")

                    with Container(id="daemon", classes="menu-content"):
                        yield Static("Hydro Daemon", classes="menu-header")
                        yield Label(f"Daemon Status: {self.check_status()}", id="daemon-status")

                        with Horizontal():
                            yield Button("Start Daemon", id="start-daemon")
                            yield Button("Kill Daemon", id="kill-daemon")
                            yield Button("Create Service", id="create-service")
                            
                        yield Static(classes="menu-footer")

                    with Container(id="logs", classes="menu-content"):
                        yield Static("Daemon Logs", classes="menu-header")
                        yield Static(classes="menu-footer")

        yield Footer()

    def on_mount(self) -> None:
        self.update_page()
        self.action_update_info()

    def update_page(self) -> None:
        try:
            header_box = self.query_one("#record-header", Static)
            content_box = self.query_one("#record-content", Static)
            footer_box = self.query_one("#record-footer", Static)
        except Exception:
            return

        if self.total == 0:
            content_box.update("There are no data records for this billing period!")
            footer_box.update("Record 0 of 0")
            return

        record_date, record_value = self.record_list[self.index]
        day_name = datetime.strptime(record_date, "%Y-%m-%d").strftime("%A")

        header_box.update(f"\t\t\t[bold yellow]{day_name} | {record_date}[/bold yellow]\n\n")

        formatted_content = f"\n\t\t\tTypes of Usage/Cost:\n\nSpecial (Weekend/Holiday)\t\t\t{record_value['Special_Usage']}kWh/${record_value['Special_Cost']}\n"
        formatted_content += f"Medium:\t\t\t\t\t\t{record_value['Medium_Usage']}kWh/${record_value['Medium_Cost']}\nHigh:\t\t\t\t\t\t{record_value['High_Usage']}kWh/${record_value['High_Cost']}\n"
        formatted_content += f"Overnight: \t\t\t\t\t{record_value['Night_Usage']}kWh/${record_value['Night_Cost']}"
        formatted_content += f"\n\t\t\t\t\tTotal:\t{record_value['Total_Usage']}kWh/${record_value['Total_Cost']}"
        formatted_content += f"\n\n\n\t\t\tTemperature Ranges:\n\t\tMin\t\t\t\tMax\n\t\t{record_value['Min_Temp']}\t\t\t\t{record_value['Max_Temp']}\n"
        content_box.update(formatted_content)
        
        footer_box.update(
            f"\t\t\tRecord {self.index + 1} of {self.total}\n\n\n\t\t\tCurrent Data\nCost: ${self.cost}\t\t\t\t\tUsage: {self.usage}kWh"
        )

    def action_next_page(self) -> None:
        if self.mode == "tracker":
            if self.index < self.total - 1:
                self.index += 1
                self.update_page()

    def action_prev_page(self) -> None:
        if self.mode == "tracker":
            if self.index > 0:
                self.index -= 1
                self.update_page()

    def action_toggle_mode(self) -> None:
        switcher = self.query_one("#main-switcher", ContentSwitcher)
        if switcher.current == "tracker":
            switcher.current = "daemon"
            self.mode = "daemon"
            self.action_update_info()
        else:
            switcher.current = "tracker"
            self.mode = "tracker"
            self.update_page()

    def action_update_info(self) -> None:
        try:
            daemon_stats = self.query_one("#daemon-status", Label)
            daemon_stats.update(f"Daemon Status: {self.check_status()}")
        except Exception:
            pass

    def action_toggle_settings(self) -> None:
        if self.mode == "daemon":
            switcher = self.query_one("#menu-switcher", ContentSwitcher)
            last_menu = switcher.current
            switcher.current = "settings" if switcher.current != "settings" else self.last_menu
            self.last_menu = last_menu
            self.menu = switcher.current

    def action_toggle_logs(self) -> None:
        if self.mode == "daemon":
            switcher = self.query_one("#menu-switcher", ContentSwitcher)
            last_menu = switcher.current
            switcher.current = "logs" if switcher.current != "logs" else self.last_menu
            self.last_menu = last_menu
            self.menu = switcher.current

    def action_toggle_daemon(self) -> None:
        if self.mode == "daemon":
            self.action_update_info()
            switcher = self.query_one("#menu-switcher", ContentSwitcher)
            last_menu = switcher.current
            switcher.current = "daemon" if switcher.current != "daemon" else self.last_menu
            self.last_menu = last_menu
            self.menu = switcher.current

    def action_update_data_action(self) -> None:
        if self.mode == "daemon":
            update_data()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "--update":
        print("Updating...")
        update_data()
        sys.exit(0)

    HydroApp().run()

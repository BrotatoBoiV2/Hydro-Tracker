#!../../.hydro.venv/bin/python
import json
import subprocess
from pathlib import Path
import getpass
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.widgets import ContentSwitcher, Footer, Header, Static, Input, Button, Label
from textual_timepiece.pickers import TimePicker
from whenever import Time


SYSTEMD_PATH = "/etc/systemd/system/"
SECURE_PASS_BIN = Path(__file__).parent / "lib/secure_pass"


class HydroDaemonApp(App):
    CSS = """
    Screen {
        align: center middle;
    }
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
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+s", "toggle_settings", "Settings", priority=True),
        Binding("ctrl+l", "toggle_logs", "Logs", priority=True),
        Binding("ctrl+d", "toggle_daemon", "Daemon", priority=True),
        Binding("ctrl+r", "update_info", "Refresh", priority=True)
    ]

    def __init__(self):
        super().__init__()
        self.menu = "daemon"
        self.last_menu = "daemon"
        self.base_dir = Path("~/.hydro").expanduser()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.base_dir / "config.json"
        self.config = self.get_config()

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
            raise RuntimeError("systemctl command not found. Is this a systemd Linux environment?")

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
        login_email = self.query_one("#login-email").value
        login_password = self.query_one("#login-password").value
        refresh_time = f"{self.query_one("#refresh-time").value}"
        enc_pass_res = subprocess.run([SECURE_PASS_BIN, login_password, "--encrypt"], capture_output=True)
        enc_pass = enc_pass_res.stdout.decode('utf-8').replace('\n', '')

        data = {
            "Login_Email": login_email,
            "Login_Password": enc_pass,
            "Refresh_Time": refresh_time
        }

        with open(self.config_file, "w") as file:
            json.dump(data, file, indent=4)

    @on(Button.Pressed, "#start-daemon")
    def start_daemon(self) -> None:
        subprocess.run(["systemctl", "enable", "hydro_tracker.service"])
        subprocess.run(["systemctl", "start", "hydro_tracker.service"])

    @on(Button.Pressed, "#kill-daemon")
    def kill_daemon(self) -> None:
        subprocess.run(["systemctl", "disable", "hydro_tracker.service"])
        subprocess.run(["systemctl", "stop", "hydro_tracker.service"]) 

    @on(Button.Pressed, "#create-service")
    def create_service(self) -> None:
        with open("log.txt", "w") as file:
            file.write(str(self.config))
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
        OnCalendar=*-*-* {self.config["Refresh_Time"]}
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

        with Container(id="daemon-container"):
            with ContentSwitcher(initial=self.menu, id="menu-switcher"):
                with Container(id="settings", classes="menu-content"):
                    email = self.config.get("Login_Email", "")
                    enc_password = self.config.get("Login_Password", "")
                    dec_pass_res = subprocess.run([SECURE_PASS_BIN, enc_password, "--decrypt"], capture_output=True)
                    password = dec_pass_res.stdout.decode('utf-8').replace('\n', '')
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

    def action_update_info(self) -> None:
        daemon_stats = self.query_one("#daemon-status")
        daemon_stats.update(f"Daemon Status: {self.check_status()}")

    def action_toggle_settings(self) -> None:
        switcher = self.query_one("#menu-switcher", ContentSwitcher)
        last_menu = switcher.current
        switcher.current = "settings" if switcher.current != "settings" else self.last_menu
        self.last_menu = last_menu
        self.menu = switcher.current

    def action_toggle_logs(self) -> None:
        switcher = self.query_one("#menu-switcher", ContentSwitcher)
        last_menu = switcher.current
        switcher.current = "logs" if switcher.current != "logs" else self.last_menu
        self.last_menu = last_menu
        self.menu = switcher.current

    def action_toggle_daemon(self) -> None:
        self.action_update_info()
        switcher = self.query_one("#menu-switcher", ContentSwitcher)
        last_menu = switcher.current
        switcher.current = "daemon" if switcher.current != "daemon" else self.last_menu
        self.last_menu = last_menu
        self.menu = switcher.current


if __name__ == "__main__":
    HydroDaemonApp().run()
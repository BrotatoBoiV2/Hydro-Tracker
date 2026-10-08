import json
import subprocess
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.widgets import ContentSwitcher, Footer, Header, Static, Input, Button
from textual_timepiece.pickers import TimePicker


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
        margin-bottom: 40;
        content-align: left top;
    }
    .menu-footer {
        height: 5;
        content-align: left middle;
        text-style: bold;
        color: magenta;
        border-top: dashed lime;
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
        Binding("ctrl+s", "toggle_settings", "Settings"),
    ]

    def __init__(self):
        super().__init__()
        self.menu = "main"
        self.base_dir = Path("~/.hydro").expanduser()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.base_dir / "config.json"
        self.config = self.get_config()

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
        enc_pass_res = subprocess.run(["lib/secure_pass", login_password, "--encrypt"], capture_output=True)
        enc_pass = enc_pass_res.stdout.decode('utf-8').replace('\n', '')

        data = {
            "Login_Email": login_email,
            "Login_Password": enc_pass,
            "Refresh_Time": refresh_time
        }

        with open(self.config_file, "w") as file:
            json.dump(data, file, indent=4)

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="daemon-container"):
            with ContentSwitcher(initial=self.menu, id="menu-switcher"):
                # View 1: Settings
                with Container(id="settings", classes="menu-content"):
                    yield Static("Settings", classes="menu-header")
                    # yield Static(f"Loaded Config: {self.config}", classes="menu-content")
                    # email
                    # with Container(classes="menu-content"):
                    with Horizontal():
                        yield Static("Email       : ")
                        yield Input(placeholder="Login Email", id="login-email")

                    with Horizontal():
                        yield Static("Password    : ")
                        yield Input(password=True, placeholder="Login Password", id="login-password")
                    
                    with Horizontal():
                        yield Static("Update Time : ")
                        yield TimePicker(id="refresh-time")

                    yield Button("Save!", id="save-btn", variant="primary")

                    # yield Input(placeholder="Email to log in with")
                    # password
                    # Time to get data
                    yield Static("Press s to toggle settings | q to quit", classes="menu-footer")

                # View 2: Main Menu
                with Container(id="main", classes="menu-content"):
                    yield Static("Hydro Daemon", classes="menu-header")
                    # yield Static()
                    yield Static(classes="menu-footer")

        yield Footer()

    def action_toggle_settings(self) -> None:
        switcher = self.query_one("#menu-switcher", ContentSwitcher)
        switcher.current = "main" if switcher.current == "settings" else "settings"
        self.menu = switcher.current


if __name__ == "__main__":
    HydroDaemonApp().run()
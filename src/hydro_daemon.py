import json
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import ContentSwitcher, Footer, Header, Static, Input


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
    }
    .menu-content {
        height: 15;
        color: purple;
        content-align: left top;
        border-top: dashed lime;
    }
    .menu-footer {
        height: 8;
        content-align: left middle;
        text-style: bold;
        color: magenta;
        border-top: dashed lime;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("s", "toggle_settings", "Settings"),
    ]

    def __init__(self):
        super().__init__()
        self.menu = "main"
        self.config = self.get_config()

    def get_config(self) -> dict:
        config_dir = Path("~/.hydro").expanduser()
        config_file = config_dir / "config.json"

        config_dir.mkdir(parents=True, exist_ok=True)

        if config_file.is_file():
            try:
                with open(config_file, "r") as file:
                    return json.load(file)
            except json.JSONDecodeError:
                return {}
        return {}

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="daemon-container"):
            with ContentSwitcher(initial=self.menu, id="menu-switcher"):
                # View 1: Settings
                with Container(id="settings"):
                    yield Static("Settings", classes="menu-header")
                    # yield Static(f"Loaded Config: {self.config}", classes="menu-content")
                    # email
                    with Container(id="menu-content"):
                        yield Static("Email: ")
                        yield Input(placeholder="Email to log in with")
                    # password
                    # Time to get data
                    yield Static("Press t to toggle view | q to quit", classes="menu-footer")

                # View 2: Main Menu
                with Container(id="main"):
                    yield Static("Hydro Daemon", classes="menu-header")
                    yield Static(classes="menu-content")
                    yield Static(classes="menu-footer")

        yield Footer()

    def action_toggle_settings(self) -> None:
        switcher = self.query_one("#menu-switcher", ContentSwitcher)
        switcher.current = "main" if switcher.current == "settings" else "settings"
        self.menu = switcher.current


if __name__ == "__main__":
    HydroDaemonApp().run()
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Header, Footer, Static

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
    .menu-content {
        height: 15;
        color: purple;
        content-align: left top;
        border-top: dashed lime;
    }
    .menu-footer {
        height: 10;
        content-align: left middle;
        text-style: bold;
        color: magenta;
        border-top: dashed lime;
    }
    """
    BINDINGS = [
        Binding("q", "quit", "Quit")
    ]

    def __init__(self):
        super().__init__()

        self.config = self.get_config()

    def get_config(self):
        config_file = Path('~/.hydro/config.json').expanduser()

        if config_file.is_file():
            with open(config_file, 'r') as file:
                return json.load(file)

        else:
            self.menu = "settings"

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="daemon-container"):
            yield Static(id=f"{self.menu}-header", classes="menu-header")
            yield Static(id=f"{self.menu}-content", classes="menu-content")
            yield Static(id=f"{self.menu}-footer", classes="menu-footer")
        yield Footer()
    


if __name__ == '__main__':
    HydroDaemonApp().run()




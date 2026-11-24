import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.widgets import Button, ContentSwitcher, Footer, Header, Input, Static

from data_handler import clean_data, obtain_data, BASE_DIR
from password_client import LocalCryptograph, PasswordClient

# Define or import your binary path if not already globally defined
SECURE_PASS_BIN = "lib/secure_pass"


def get_records():
    with open(Path("~/.hydro/current_bill.json").expanduser(), "r") as file:
        data = json.load(file)
    return data["Records"], data["Current_Cost"], data["Current_Usage"]


def update_data():
    print("Obtaining data...")
    if not obtain_data():
        return False

    print("Data obtained, now cleaning it...")
    clean_data()
    print("Data is cleaned and ready to use!")
    return True


HYDRO_RECORDS, CURRENT_COST, CURRENT_USAGE = get_records()


class HydroUsageApp(App):
    """A Textual TUI application that switches between tracker and settings views."""

    CSS = """
    Screen {
        align: center middle;
    }
    #hydro-container {
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
    .menu-header {
        height: 3;
        content-align: center middle;
        text-style: bold;
        color: yellow;
        border-bottom: dashed lime;
    }
    .menu-content {
        height: 100%;
        color: purple;
        content-align: left top;
    }
    Horizontal {
        height: 3;
        margin-bottom: 1;
    }
    Horizontal Static {
        width: auto;
    }
    Input {
        margin-left: 4;
        width: 40;
    }
    #save-btn {
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("left", "prev_record", "Previous Record"),
        Binding("right", "next_record", "Next Record"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+u", "update", "Update Hydro Usage"),
        Binding("ctrl+s", "settings", "Settings Page"),
        Binding("ctrl+t", "tracker", "Hydro Tracker")
    ]

    def __init__(self, hydro_data, current_cost, current_usage, config=None):
        super().__init__()

        self.hydro_data = hydro_data
        self.current_cost = current_cost
        self.current_usage = current_usage
        self.config = config or {}
        self.config_file = BASE_DIR / "config.json"
        self.records_list = list(self.hydro_data.items())
        self.total_records = len(self.records_list)
        self.current_record_index = max(0, self.total_records - 1)
        self.current_page = "tracker"

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="hydro-container"):
            with ContentSwitcher(initial=self.current_page, id="page-switcher"):
                # Page 1: Tracker
                with Container(id="tracker"):
                    yield Static(id="record-header")
                    yield Static(id="record-content")
                    yield Static(id="record-footer")

                # Page 2: Settings
                with Container(id="settings"):
                    email = self.config.get("Login_Email", "")
                    enc_password = self.config.get("Login_Password", "")
                    password = ""
                    if enc_password:
                        dec_pass_res = subprocess.run(
                            [SECURE_PASS_BIN, enc_password, "--decrypt"],
                            capture_output=True,
                        )
                        password = dec_pass_res.stdout.decode("utf-8").replace("\n", "")
                    refresh_time = self.config.get("Refresh_Time", "00:00:00")

                    yield Static("Settings", classes="menu-header")

                    with Horizontal():
                        yield Static("Email       : ")
                        yield Input(placeholder="Login Email", id="login-email", value=email)

                    with Horizontal():
                        yield Static("Password    : ")
                        yield Input(
                            password=True,
                            placeholder="Login Password",
                            id="login-password",
                            value=password,
                        )

                    with Horizontal():
                        yield Static("Update Time : ")
                        yield Input(
                            placeholder="HH:MM:SS",
                            id="refresh-time",
                            value=refresh_time,
                        )

                    yield Button("Save!", id="save-btn", variant="primary")

        yield Footer()

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

        self.get_config()

    def on_mount(self) -> None:
        self.query_one("#settings").disabled = True
        self.set_focus(None)
        self.update_record_view()

    def update_record_view(self) -> None:
        header_box = self.query_one("#record-header", Static)
        content_box = self.query_one("#record-content", Static)
        footer_box = self.query_one("#record-footer", Static)

        if self.total_records == 0:
            content_box.update("There are no data records for this billing period!")
            footer_box.update("Record 0 of 0")
            return

        record_date, record_value = self.records_list[self.current_record_index]
        day_name = datetime.strptime(record_date, "%Y-%m-%d").strftime("%A")

        header_box.update(f"\t\t\t[bold yellow]{day_name} | {record_date}[/bold yellow]\n\n")

        formatted_content = (
            f"\n\t\t\tTypes of Usage/Cost:\n\n"
            f"Special (Weekend/Holiday)\t\t\t{record_value['Special_Usage']}kWh/${record_value['Special_Cost']}\n"
            f"Medium:\t\t\t\t\t\t{record_value['Medium_Usage']}kWh/${record_value['Medium_Cost']}\n"
            f"High:\t\t\t\t\t\t{record_value['High_Usage']}kWh/${record_value['High_Cost']}\n"
            f"Overnight: \t\t\t\t\t{record_value['Night_Usage']}kWh/${record_value['Night_Cost']}"
            f"\n\t\t\t\t\tTotal:\t{record_value['Total_Usage']}kWh/${record_value['Total_Cost']}"
            f"\n\n\n\t\t\tTemperature Ranges:\n\t\tMin\t\t\t\tMax\n\t\t{record_value['Min_Temp']}\t\t\t\t{record_value['Max_Temp']}\n"
        )
        content_box.update(formatted_content)

        footer_box.update(
            f"\t\t\tRecord {self.current_record_index + 1} of {self.total_records}\n\n\n"
            f"\t\t\tCurrent Data\nCost: ${self.current_cost}\t\t\t\t\tUsage: {self.current_usage}kWh"
        )

    def action_next_record(self) -> None:
        """Increments record index only when viewing the tracker page."""
        if self.current_page == "tracker" and self.current_record_index < self.total_records - 1:
            self.current_record_index += 1
            self.update_record_view()

    def action_prev_record(self) -> None:
        """Decrements record index only when viewing the tracker page."""
        if self.current_page == "tracker" and self.current_record_index > 0:
            self.current_record_index -= 1
            self.update_record_view()

    def action_update(self) -> None:
        if not update_data():
            self.action_settings()

    def action_settings(self) -> None:
        self.action_change_page("settings")

    def action_tracker(self) -> None:
        self.action_change_page("tracker")

    def action_change_page(self, pagename: str) -> None:
        self.current_page = pagename
        self.query_one("#page-switcher", ContentSwitcher).current = pagename

        if pagename == "tracker":
            self.query_one("#settings").disabled = True
            self.query_one("#tracker").disabled = False
            self.set_focus(None)

        elif pagename == "settings":
            self.query_one("#tracker").disabled = True
            self.query_one("#settings").disabled = False
            self.query_one("#login-email", Input).focus()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--update":
        print("Updating...")
        update_data()
        sys.exit(0)

    HydroUsageApp(HYDRO_RECORDS, CURRENT_COST, CURRENT_USAGE).run()

#!../.hydro.venv/bin/python

from datetime import datetime
import json
from pathlib import Path
import sys

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.widgets import ContentSwitcher, Footer, Header, Static, Input, Button, Label
from textual_timepiece.pickers import TimePicker
from whenever import Time

from data_handler import BASE_DIR, obtain_data, clean_data
from password_client import PasswordClient, LocalCryptograph, ClientHash

LOCAL_HASH  = ClientHash().client_hash
PASS_CLIENT = PasswordClient()
CRYPTOGRAPH = LocalCryptograph()


class TrackerApp(App):
    CSS = """
    Screen {
        align: center middle;
    }

    #tracker-menu {
        color: magenta;
        width: 70;
        height: 30;
        border: round red;
        padding: 1 2;
        background: black;
    }

    #tracker-footer {
        height: 10;
        content-align: left middle;
        text-style: bold;
        color: magenta;
        border-top: dashed lime;
    }

    #menu-switcher {
        width: 70;
        height: 30;
        border: round red;
        padding: 1 2;
        background: black;
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
        Binding("left", "prev_record", "Previous Record"),
        Binding("right", "next_record", "Next Record"),
        Binding("ctrl+s", "toggle_settings", "Toggle Settings"),
        Binding("ctrl+u", "update_data", "Update Hydro Data"),
    ]
    AUTO_FOCUS = None

    def __init__(self, exec_file):
        super().__init__()

        self.bill_file = Path("~/.hydro/current_bill.json").expanduser()
        self.get_information()
        self.record_list = list(self.records.items())
        self.record_count = len(self.record_list)
        self.current_record_index = max(0, self.record_count - 1)
        self.config_file = BASE_DIR / "config.json"
        self.config = self._get_config()
        self.menu = "tracker"
        self.execution_file = exec_file

    def _get_config(self) -> dict:
        if self.config_file.is_file():
            try:
                with open(self.config_file, "r") as file:
                    return json.load(file)
            except json.JSONDecodeError:
                return {}

        return {}

    def _reload_records(self) -> None:
        self.get_information()
        self.record_list = list(self.records.items())
        self.record_count = len(self.record_list)

        if self.record_count == 0:
            self.current_record_index = 0
        elif self.current_record_index >= self.record_count:
            self.current_record_index = self.record_count - 1

        self.update_record_view()

    @on(Button.Pressed, "#save-btn")
    def save_config(self) -> None:
        login_email = self.query_one("#login-email").value
        login_password = self.query_one("#login-password").value
        refresh_time = f"{self.query_one("#refresh-time").value}"
        safe_pass = CRYPTOGRAPH.encrypt(login_password)
        enc_pass = PASS_CLIENT.send_request("encrypt", safe_pass, LOCAL_HASH)
        data = {
            "Login_Email": login_email,
            "Login_Password": enc_pass,
            "Refresh_Time": refresh_time
        }

        with open(self.config_file, "w") as file:
            json.dump(data, file, indent=4)

        self._get_config()
        
    def compose(self) -> ComposeResult:
        yield Header()

        with ContentSwitcher(initial=self.menu, id="menu-switcher"):
            with Container(id="tracker"):
                yield Static(id="tracker-header")
                yield Static(id="tracker-content")
                yield Static(id="tracker-footer")

            with Container(id="settings"):
                email = self.config.get("Login_Email", "")
                enc_password = self.config.get("Login_Password", "")
                password = enc_password
                if enc_password:
                    dec_pass = PASS_CLIENT.send_request("decrypt", enc_password, LOCAL_HASH)
                    password = CRYPTOGRAPH.decrypt(dec_pass)

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

        yield Footer()

    def get_information(self):
        with open(self.bill_file, "r") as file:
            data = json.load(file)

        self.records = data["Records"]
        self.cost = data["Current_Cost"]
        self.usage = data["Current_Usage"]

    def on_mount(self) -> None:
        self.update_record_view()

    def update_record_view(self) -> None:
        header = self.query_one("#tracker-header", Static)
        content = self.query_one("#tracker-content", Static)
        footer = self.query_one("#tracker-footer", Static)

        if self.record_count == 0:
            content.update("There are no records found for this billing period!")
            footer.update("Empty 0/0")
            return

        record_date, record_value = self.record_list[self.current_record_index]
        day_name = datetime.strptime(record_date, "%Y-%m-%d").strftime("%A")
        header.update(f"\t\t\t[bold yellow]{day_name} | {record_date}[/bold yellow]\n\n")
        
        formatted_content = (
            f"\n\t\t\tTypes of Usage/Cost:\n\n"
            f"Special (Weekend/Holiday)\t\t\t{record_value['Special_Usage']}kWh/${record_value['Special_Cost']}\n"
            f"Medium:\t\t\t\t\t\t{record_value['Medium_Usage']}kWh/${record_value['Medium_Cost']}\n"
            f"High:\t\t\t\t\t\t{record_value['High_Usage']}kWh/${record_value['High_Cost']}\n"
            f"Overnight: \t\t\t\t\t{record_value['Night_Usage']}kWh/${record_value['Night_Cost']}"
            f"\n\t\t\t\t\tTotal:\t{record_value['Total_Usage']}kWh/${record_value['Total_Cost']}"
            f"\n\n\n\t\t\tTemperature Ranges:\n\t\tMin\t\t\t\tMax\n\t\t{record_value['Min_Temp']}\t\t\t\t{record_value['Max_Temp']}\n"
        )
        content.update(formatted_content)

        footer.update(
            f"\t\t\tRecord {self.current_record_index + 1} of {self.record_count}\n\n\n"
            f"\t\t\tCurrent Data\nCost: ${self.cost}\t\t\t\t\tUsage: {self.usage}kWh"
        )

    def action_next_record(self) -> None:
        if self.current_record_index < self.record_count - 1:
            self.current_record_index += 1
            self.update_record_view()

    def action_prev_record(self) -> None:
         if self.current_record_index > 0:
            self.current_record_index -= 1
            self.update_record_view()

    def action_toggle_settings(self) -> None:
        switcher = self.query_one("#menu-switcher")
        last_menu = switcher.current
        switcher.current = "settings" if switcher.current != "settings" else "tracker"
        self.menu = switcher.current

        if self.menu == "tracker":
            self.set_focus(None)
        else:
            self.query_one("#login-email", Input).focus()

    def action_update_data(self) -> None:
        import subprocess

        # Run the script
        result = subprocess.run([self.execution_file, "--update"])
        if result.returncode == 0:
            self._reload_records()
        # obtain_data(self.pass_client, self.cryptograph, self.hash)
        # clean_data()



if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "--update":
        print("Updating...")
        obtain_data(PASS_CLIENT, CRYPTOGRAPH, LOCAL_HASH)
        clean_data()
        sys.exit(0)

    exec_file = sys.argv[0]
    TrackerApp(exec_file).run()

import json
from pathlib import Path
from datetime import datetime
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Header, Footer, Static


def get_records():
    with open(Path("~/.hydro/current_bill.json").expanduser(), "r") as file:
        data = json.load(file)
    return data["Records"], data["Current_Cost"], data["Current_Usage"]
   


HYDRO_RECORDS, CURRENT_COST, CURRENT_USAGE = get_records()


class HydroUsageApp(App):
    """A Textual TUI application that reads pages directly from a nested dictionary structure."""

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
    """

    BINDINGS = [
        Binding("left", "prev_record", "Previous Page"),
        Binding("right", "next_record", "Next Page"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, hydro_data, current_cost, current_usage):
        super().__init__()
        self.hydro_data = hydro_data
        self.current_cost = current_cost
        self.current_usage = current_usage
        self.records_list = list(self.hydro_data.items())
        self.total_records = len(self.records_list)
        self.current_record_index = self.total_records - 1

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="hydro-container"):
            yield Static(id="record-header")
            yield Static(id="record-content")
            yield Static(id="record-footer")
        yield Footer()

    def on_mount(self) -> None:
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

        formatted_content = f"\n\t\t\tTypes of Usage/Cost:\n\nSpecial (Weekend/Holiday)\t\t\t{record_value['Special_Usage']}kWh/${record_value['Special_Cost']}\n"
        formatted_content += f"Medium:\t\t\t\t\t\t{record_value['Medium_Usage']}kWh/${record_value['Medium_Cost']}\nHigh:\t\t\t\t\t\t{record_value['High_Usage']}kWh/${record_value['High_Cost']}\n"
        formatted_content += f"Overnight: \t\t\t\t\t{record_value['Night_Usage']}kWh/${record_value['Night_Cost']}"
        formatted_content += f"\n\t\t\t\t\tTotal:\t{record_value['Total_Usage']}kWh/${record_value['Total_Cost']}"
        formatted_content += f"\n\n\n\t\t\tTemperature Ranges:\n\t\tMin\t\t\t\tMax\n\t\t{record_value['Min_Temp']}\t\t\t\t{record_value['Max_Temp']}\n"
        content_box.update(formatted_content)
        
        footer_box.update(
            f"\t\t\tRecord {self.current_record_index + 1} of {self.total_records}\n\n\n\t\t\tCurrent Data\nCost: ${self.current_cost}\t\t\t\t\tUsage: {self.current_usage}kWh"
        )

    def action_next_record(self) -> None:
        """Increments page state safely up to the array boundary limit."""
        if self.current_record_index < self.total_records - 1:
            self.current_record_index += 1
            self.update_record_view()

    def action_prev_record(self) -> None:
        """Decrements page state safely down to zero index."""
        if self.current_record_index > 0:
            self.current_record_index -= 1
            self.update_record_view()


if __name__ == "__main__":
    HydroUsageApp(HYDRO_RECORDS, CURRENT_COST, CURRENT_USAGE).run()

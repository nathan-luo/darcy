from framework.core.observer import Observer
from typing import Any
from interfaces.cli import ToolCLI
from rich.prompt import Confirm

class CLIObserver(Observer):
    def __init__(self, cli_interface: ToolCLI):
        self.cli_interface = cli_interface
        self.loading = None

    def update(self, event: Any):
        if event["type"] == "response":
            self.cli_interface.print_message(event["content"], event["type"], "green")
        if event["type"] == "function_call":
            self.cli_interface.print_message(event["parameters"], event["name"], "yellow")
        if event["type"] == "function_result":
            self.cli_interface.print_message(event["content"]["content"], event["name"], "yellow")
        if event["type"] == "status_update":
            if not self.loading:
                self.loading = self.cli_interface.show_loading(event["message"])
                self.loading.__enter__()
            elif event["message"] == "done":
                if self.loading:
                    self.loading.__exit__(None, None, None)
                    self.loading = None
                else:
                    raise Exception("Loading spinner not initialized.")
            else:
                self.loading.update_status(event["message"])

    def get_input(self, event: Any):
        if event["type"] == "confirm":
            while True:
                self.loading.live_context.stop()
                response = self.cli_interface.get_confirmation(event["message"]).lower().strip()
                self.loading.live_context.start()
                if response in ['yes', 'y']:
                    return True
                elif response in ['no', 'n']:
                    return False
                print("Please enter 'yes' or 'no'")
        return self.cli_interface.get_input(event["message"])

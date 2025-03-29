"""
CLI Analysis Database Browser.

A Textual-based UI for browsing the CLI tools stored in the database.
"""

import logging
import os
import traceback
from datetime import datetime
from typing import Dict, List, Optional

# Keep necessary imports for the App
from sqlmodel import Session, select # Keep for SQLDebugButton logic if moved back/handled here
from sqlmodel import Session, select # Keep for SQLDebugButton logic if moved back/handled here
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
# Import Input along with other base widgets
from textual.widgets import Footer, Header, Label, Static, Input

# Import custom widgets from their new locations
from .widgets.tools_table import ToolsTable, ToolSelected
from .widgets.command_tree import CommandTree, CommandSelected
from .widgets.detail_panel import DetailPanel
from .widgets.search_input import SearchInput
from .widgets.sql_debug_button import SQLDebugButton, SQLDebugRequested # Import message too

# Keep repository import
from testronaut.ui.repository import DBBrowserRepository
# Keep model imports if needed by App logic (e.g., SQLDebugButton logic if moved)
# from testronaut.models.base import engine # Engine is used in SQLDebugButton now
# from testronaut.models.cli_tool import CLITool # Keep CLITool for SQLDebugButton logic

# Disable other logs that might interfere with the TUI
logging.getLogger("httpx").setLevel(logging.WARNING)

# Custom logger for the UI that won't output to console
ui_logger = logging.getLogger("testronaut.ui")
ui_logger.setLevel(logging.DEBUG)  # Change to DEBUG level
# Remove any existing handlers to prevent console output
for handler in ui_logger.handlers[:]: # Iterate over a copy
    ui_logger.removeHandler(handler)
# Add a file handler to log to a file in the current directory
log_file = os.path.join(os.getcwd(), "browser_debug.log")
try:
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    ui_logger.addHandler(file_handler)
    ui_logger.info(f"Browser UI starting, logging to {log_file}") # Use info level for startup message
except Exception as e:
    print(f"Error setting up UI file logger: {e}") # Print error if logger setup fails


# Also add a method to dump objects for debugging
# Consider moving this to a shared utility module if used elsewhere
def debug_dump(obj, prefix="DEBUG DUMP"):
    """Dump object details to the log for debugging."""
    if not ui_logger.isEnabledFor(logging.DEBUG):
        return

    try:
        import pprint

        dump = pprint.pformat(obj, indent=2, depth=3)
        ui_logger.debug(f"{prefix}: {dump}")
    except Exception as e:
        ui_logger.debug(f"Error dumping object {prefix}: {str(e)}")


# --- Widget Classes Removed - Now Imported ---


class DBBrowserApp(App):
    """Database Browser Application."""

    TITLE = "Testronaut DB Browser"
    SUB_TITLE = "Browse CLI Analysis Results"
    CSS_PATH = "styles/browser.tcss" # Assuming CSS file exists

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("f", "focus_search", "Search"),
        ("escape", "clear_search", "Clear Search"),
    ]

    def __init__(self, tool_id: Optional[str] = None):
        """
        Initialize the app.

        Args:
            tool_id: Optional ID of tool to load on startup
        """
        super().__init__()
        self.selected_tool_id = tool_id
        self.repository = DBBrowserRepository()
        self.search_results: List[Dict] = []
        self.search_active = False
        # self.debug_button = SQLDebugButton() # Button is now composed directly

    def compose(self) -> ComposeResult:
        """Compose the app layout."""
        yield Header()

        with Container(id="app-grid"):
            # Left panel with tools list and search
            with Vertical(id="left-panel"):
                yield Label("CLI Tools", id="tools-header")
                with Horizontal(id="search-container"):
                    yield SearchInput() # Use imported widget
                yield ToolsTable() # Use imported widget
                yield SQLDebugButton() # Use imported widget

            # Middle panel with command tree
            with Vertical(id="middle-panel"):
                yield CommandTree() # Use imported widget

            # Right panel with details
            with Vertical(id="right-panel"):
                yield DetailPanel() # Use imported widget

        yield Footer()

    def on_mount(self) -> None:
        """Handle the app mount event."""
        # If a tool ID was provided at startup, select it
        if self.selected_tool_id:
            self.select_tool(self.selected_tool_id)
        else:
             # Disable debug button initially if no tool selected
             self.query_one(SQLDebugButton).disabled = True


    @on(Input.Changed)
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        # Check the type of the input widget that triggered the event
        if isinstance(event.input, SearchInput):
            if len(event.value) >= 2:
                self.search_commands(event.value)
            elif not event.value:
                self.clear_search()

    def search_commands(self, query: str) -> None:
        """Search for commands matching the query."""
        self.search_results = self.repository.search_commands(query)

        # Update the tree to show search results
        command_tree = self.query_one(CommandTree)
        command_tree.clear()
        command_tree.root.set_label(f"Search Results: {query}") # Use set_label

        if not self.search_results:
            command_tree.root.add("No results found")
            return

        # Group by tool
        results_by_tool: Dict[str, Dict] = {}
        for cmd in self.search_results:
            # Validate command data
            if not isinstance(cmd, dict) or "tool_id" not in cmd or "tool_name" not in cmd:
                ui_logger.debug(f"Invalid command data in search results: {cmd}")
                continue

            tool_id = cmd["tool_id"]
            tool_name = cmd["tool_name"]

            if tool_id not in results_by_tool:
                results_by_tool[tool_id] = {"name": tool_name, "commands": []}

            results_by_tool[tool_id]["commands"].append(cmd)

        # Add to tree
        for tool_id, tool_data in results_by_tool.items():
            if not tool_id:  # Skip if tool_id is None or empty
                continue

            tool_node = command_tree.root.add(f"🔧 {tool_data['name']}")

            for cmd in tool_data["commands"]:
                # Validate command has required fields
                if not isinstance(cmd, dict) or "name" not in cmd:
                    ui_logger.debug(f"Skipping invalid command: {cmd}")
                    continue

                # Create node label with icon based on command type
                icon = "🔸" if cmd.get("is_subcommand") else "🔹"
                cmd_label = f"{icon} {cmd['name']}"
                if cmd.get("description"):
                    # Keep label concise
                    desc_short = cmd['description'][:40] + ('...' if len(cmd['description']) > 40 else '')
                    cmd_label += f": {desc_short}"

                # Make sure we store the command dictionary as data
                tool_node.add(cmd_label, data=cmd)

        self.search_active = True
        command_tree.root.expand() # Expand results

    def select_tool(self, tool_id: str) -> None:
        """Select a tool and display its commands."""
        if not tool_id:
            ui_logger.warning("Attempted to select tool with empty ID")
            return

        ui_logger.info(f"Selecting tool with ID: {tool_id}")
        self.selected_tool_id = tool_id
        # Update the debug button state
        self.query_one(SQLDebugButton).set_tool_id(tool_id)

        # Get the tool detail first to verify it exists
        # repository = DBBrowserRepository() # Use self.repository
        tool_detail = self.repository.get_tool_detail(tool_id)

        if not tool_detail:
            ui_logger.warning(f"Could not load tool with ID: {tool_id}")
            detail_panel = self.query_one(DetailPanel)
            detail_panel.update("# Error\n\nSelected tool could not be loaded from the database.")
            # Clear command tree as well
            command_tree = self.query_one(CommandTree)
            command_tree.clear()
            command_tree.root.set_label("Commands")
            return

        ui_logger.info(f"Successfully loaded tool: {tool_detail['name']}")

        # Update the command tree
        command_tree = self.query_one(CommandTree)
        command_tree.load_tool(tool_id)

        # Update the detail panel with tool information
        detail_panel = self.query_one(DetailPanel)
        # Use the panel's method to show tool details
        detail_panel.show_tool_detail(tool_detail)

        # Log command loading for debugging
        cmd_count = len(tool_detail.get("commands", []))
        ui_logger.info(f"Loaded tool {tool_detail.get('name')} with {cmd_count} commands")

    # Removed _format_tool_detail as logic moved to DetailPanel

    def action_refresh(self) -> None:
        """Refresh the current view."""
        ui_logger.info("Refreshing view...")
        if self.search_active:
            search_input = self.query_one(SearchInput)
            self.search_commands(search_input.value)
        else:
            tools_table = self.query_one(ToolsTable)
            tools_table.refresh_tools()

            if self.selected_tool_id:
                self.select_tool(self.selected_tool_id)
            else:
                 # If no tool selected, clear details and tree
                 self.query_one(DetailPanel).clear_panel()
                 command_tree = self.query_one(CommandTree)
                 command_tree.clear()
                 command_tree.root.set_label("Commands")


    def action_focus_search(self) -> None:
        """Focus the search input."""
        self.query_one(SearchInput).focus()

    def action_clear_search(self) -> None:
        """Clear the search results."""
        self.clear_search()

    def clear_search(self) -> None:
        """Clear search results and restore previous view."""
        ui_logger.info("Clearing search...")
        search_input = self.query_one(SearchInput)
        search_input.value = ""

        self.search_active = False
        self.search_results = []

        # Restore view based on whether a tool was previously selected
        if self.selected_tool_id:
            self.select_tool(self.selected_tool_id) # Reload the selected tool's tree
        else:
            # No tool selected, clear the tree and detail panel
            command_tree = self.query_one(CommandTree)
            command_tree.clear()
            command_tree.root.set_label("Commands")
            self.query_one(DetailPanel).clear_panel()
            self.query_one(SQLDebugButton).set_tool_id(None) # Disable debug button


    @on(ToolSelected)
    def handle_tool_selected(self, message: ToolSelected) -> None:
        """Handle tool selection event."""
        self.search_active = False # Clear search when a tool is selected from the table
        self.query_one(SearchInput).value = "" # Clear search input visually
        ui_logger.debug(f"======= TOOL SELECTION TRIGGERED FOR ID: {message.tool_id} =======")
        self.select_tool(message.tool_id)

    @on(CommandSelected)
    def handle_command_selected(self, message: CommandSelected) -> None:
        """Handle command selection event."""
        detail_panel = self.query_one(DetailPanel)
        detail_panel.show_command(message.command)

    # Add handler for the new message from SQLDebugButton
    @on(SQLDebugRequested)
    def on_sql_debug_requested(self, event: SQLDebugRequested) -> None:
        """Handle SQL debug request."""
        # This handler is primarily for logging or app-level coordination if needed.
        # The button itself handles fetching and displaying the debug info.
        ui_logger.info(
            f"======= SQL DEBUG REQUESTED FOR TOOL ID: {self.selected_tool_id} ======="
        )
        # Add any app-level logic needed when the button is pressed


def run_browser(tool_id: Optional[str] = None) -> None:
    """
    Run the database browser app.

    Args:
        tool_id: Optional ID of tool to load on startup
    """
    ui_logger.info(f"Starting browser with tool_id: {tool_id}") # Use info
    try:
        app = DBBrowserApp(tool_id)
        app.run()
    except Exception as e:
        ui_logger.error(f"Error running browser app: {str(e)}")
        ui_logger.debug(traceback.format_exc())
        print(f"Error running browser app: {e}") # Also print to console

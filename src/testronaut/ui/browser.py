"""
CLI Analysis Database Browser.

A Textual-based UI for browsing the CLI tools stored in the database.
"""

import logging
import os
import traceback
from datetime import datetime
from typing import Dict, List, Optional

from sqlmodel import Session, select
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Static, Tree
from textual.widgets.tree import TreeNode

from testronaut.models.base import engine
from testronaut.models.cli_tool import Argument, CLITool, Command, Example, Option
from testronaut.ui.repository import DBBrowserRepository

# Disable other logs that might interfere with the TUI
logging.getLogger("httpx").setLevel(logging.WARNING)

# Custom logger for the UI that won't output to console
ui_logger = logging.getLogger("testronaut.ui")
ui_logger.setLevel(logging.DEBUG)  # Change to DEBUG level
# Remove any existing handlers to prevent console output
for handler in ui_logger.handlers:
    ui_logger.removeHandler(handler)
# Add a file handler to log to a file in the current directory
log_file = os.path.join(os.getcwd(), "browser_debug.log")
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
ui_logger.addHandler(file_handler)
ui_logger.warning(f"Browser UI starting, logging to {log_file}")


# Also add a method to dump objects for debugging
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


class ToolsTable(DataTable):
    """Table widget for displaying CLI tools."""

    BINDINGS = [
        ("enter", "select_tool", "Select Tool"),
    ]

    def __init__(self) -> None:
        """Initialize the tools table."""
        super().__init__()
        self.cursor_type = "row"
        self.zebra_stripes = True

    def on_mount(self) -> None:
        """Setup the table when mounted."""
        self.add_columns("Tool Name", "Version", "Commands", "Options", "Arguments", "Analyzed At")
        self.refresh_tools()

    def refresh_tools(self) -> None:
        """Refresh the list of tools."""
        self.clear()
        repository = DBBrowserRepository()
        tools = repository.get_all_tools()

        for tool in tools:
            command_count = tool.get("command_count", 0)
            option_count = tool.get("option_count", 0)
            argument_count = tool.get("argument_count", 0)
            created_at = tool.get("created_at")

            if created_at:
                if isinstance(created_at, datetime):
                    created_at_str = created_at.strftime("%Y-%m-%d %H:%M")
                else:
                    created_at_str = str(created_at)
            else:
                created_at_str = "Unknown"

            self.add_row(
                tool["name"],
                tool.get("version", "Unknown"),
                str(command_count),
                str(option_count),
                str(argument_count),
                created_at_str,
                key=tool["id"],
            )

    def action_select_tool(self) -> None:
        """Handle tool selection."""
        selected_row_index = self.cursor_row
        if 0 <= selected_row_index < self.row_count:
            row = self.get_row_at(selected_row_index)
            # Use getattr to safely access the key property
            tool_id = str(getattr(row, "key", ""))
            if tool_id:
                self.post_message(ToolSelected(tool_id))


class CommandTree(Tree):
    """Tree widget for displaying command hierarchy."""

    BINDINGS = [
        ("enter", "select_command", "Select Command"),
    ]

    def __init__(self) -> None:
        """Initialize the command tree."""
        super().__init__("Commands", "📋")
        self.selected_tool_id: Optional[str] = None
        self.command_nodes: Dict[str, TreeNode] = {}

    def load_tool(self, tool_id: str) -> None:
        """Load command tree for a specific tool."""
        ui_logger.debug(f"===== LOAD_TOOL START: {tool_id} =====")
        self.selected_tool_id = tool_id
        self.clear()
        repository = DBBrowserRepository()

        try:
            ui_logger.debug(f"Loading tool with ID: {tool_id}")
            tool_detail = repository.get_tool_detail(tool_id)

            if not tool_detail:
                ui_logger.error(f"No tool found with ID: {tool_id}")
                self.root.label = "No tool selected"
                self.root.add("Tool not found in database")
                return

            ui_logger.debug(
                f"Retrieved tool: {tool_detail['name']} with keys: {list(tool_detail.keys())}"
            )
            self.root.label = f"Commands: {tool_detail['name']} {tool_detail.get('version', '')}"
            self.command_nodes = {}

            # Get commands from tool detail
            commands = tool_detail.get("commands", [])
            ui_logger.debug(f"Tool has {len(commands)} commands")

            # Deeper debug for commands
            if commands:
                for i, cmd in enumerate(commands[:3]):  # Log first 3 commands as samples
                    cmd_keys = list(cmd.keys()) if isinstance(cmd, dict) else "NOT A DICT"
                    ui_logger.debug(f"Command {i} keys: {cmd_keys}")
                    if isinstance(cmd, dict) and "name" in cmd:
                        ui_logger.debug(f"Command {i} name: {cmd['name']}")
                debug_dump(commands[:3], "Sample commands")
            else:
                ui_logger.debug("Commands list is empty!")

            if not commands:
                ui_logger.warning(f"No commands found for tool: {tool_detail['name']}")
                self.root.add("No commands found for this tool")
                return

            # Add top-level commands
            for cmd in commands:
                try:
                    ui_logger.debug(f"Adding command: {cmd.get('name', 'Unnamed')}")
                    self._add_command_to_tree(cmd, self.root)
                except Exception as e:
                    ui_logger.error(f"Error adding command {cmd.get('name', 'Unknown')}: {str(e)}")
                    ui_logger.debug(traceback.format_exc())

            ui_logger.debug(
                f"Finished loading {len(commands)} commands for tool {tool_detail['name']}"
            )
        except Exception as e:
            ui_logger.error(f"Error in load_tool: {str(e)}")
            ui_logger.debug(traceback.format_exc())
            self.root.label = "Error Loading Tool"
            self.root.add(f"Error: {str(e)}")
        finally:
            ui_logger.debug(f"===== LOAD_TOOL END: {tool_id} =====")

    def _add_command_to_tree(self, command: Dict, parent: TreeNode) -> None:
        """Recursively add commands to the tree."""
        # Create node label with icon based on command type
        icon = "🔸" if command.get("is_subcommand") else "🔹"
        cmd_label = f"{icon} {command['name']}"
        if command.get("description"):
            cmd_label += f": {command['description']}"

        # Add node to tree
        node = parent.add(cmd_label, data=command)
        self.command_nodes[command["id"]] = node

        # Add subcommands recursively
        for subcmd in command.get("subcommands", []):
            self._add_command_to_tree(subcmd, node)

    def action_select_command(self) -> None:
        """Handle command selection."""
        node = self.cursor_node
        if node and hasattr(node, "data") and node.data:
            # Make sure we're sending a dictionary, not a string
            if isinstance(node.data, dict):
                self.post_message(CommandSelected(node.data))
            else:
                ui_logger.debug(f"Invalid command data: {node.data}")


class DetailPanel(Static):
    """Panel for displaying detailed information."""

    def __init__(self) -> None:
        """Initialize the detail panel."""
        super().__init__("Select a tool or command to view details")
        self.current_command: Optional[Dict] = None

    def show_command(self, command: Dict) -> None:
        """Show command details."""
        self.current_command = command

        # Validate command data
        if not isinstance(command, dict):
            self.update(f"# Error\n\nInvalid command data: {command}")
            return

        if "name" not in command:
            self.update("# Error\n\nCommand data is missing name field")
            return

        # Build markdown content for the command
        content = f"# Command: {command['name']}\n\n"

        if command.get("description"):
            content += f"**Description:** {command['description']}\n\n"

        if command.get("syntax"):
            content += f"**Syntax:** `{command['syntax']}`\n\n"

        # Add options section
        options = command.get("options", [])
        if options:
            content += "## Options\n\n"
            for opt in options:
                opt_name = opt["name"]
                if opt.get("short_form"):
                    opt_name = f"{opt['short_form']}, {opt_name}"
                elif opt.get("long_form"):
                    opt_name = f"{opt_name}, {opt['long_form']}"

                content += f"* **{opt_name}**"
                if opt.get("description"):
                    content += f": {opt['description']}"
                if opt.get("required"):
                    content += " *(required)*"
                if opt.get("default_value"):
                    content += f" *[default: {opt['default_value']}]*"
                content += "\n"
            content += "\n"

        # Add arguments section
        arguments = command.get("arguments", [])
        if arguments:
            content += "## Arguments\n\n"
            # Sort arguments by position
            sorted_args = sorted(arguments, key=lambda a: a.get("position", 0))
            for arg in sorted_args:
                content += f"* **{arg['name']}**"
                if arg.get("description"):
                    content += f": {arg['description']}"
                if arg.get("required"):
                    content += " *(required)*"
                if arg.get("default_value"):
                    content += f" *[default: {arg['default_value']}]*"
                content += "\n"
            content += "\n"

        # Add examples section
        examples = command.get("examples", [])
        if examples:
            content += "## Examples\n\n"
            for ex in examples:
                if ex.get("description"):
                    content += f"**{ex['description']}**\n\n"
                content += f"```\n{ex['command_line']}\n```\n\n"
                if ex.get("expected_output"):
                    content += "Expected output:\n\n"
                    content += f"```\n{ex['expected_output']}\n```\n\n"

        # Add help text if available
        if command.get("help_text"):
            content += "## Help Text\n\n"
            content += f"```\n{command['help_text']}\n```\n"

        self.update(content)


class ToolSelected(Message):
    """Message sent when a tool is selected."""

    def __init__(self, tool_id: str):
        """Initialize with the selected tool ID."""
        self.tool_id = tool_id
        super().__init__()


class CommandSelected(Message):
    """Message sent when a command is selected."""

    def __init__(self, command: Dict):
        """Initialize with the selected command data."""
        self.command = command
        super().__init__()


class SearchInput(Input):
    """Search input widget."""

    def __init__(self) -> None:
        """Initialize search input."""
        super().__init__(placeholder="Search commands...")


class SQLDebugButton(Button):
    """Button to run direct SQL diagnostics."""

    def __init__(self) -> None:
        """Initialize the debug button."""
        super().__init__("Run SQL Debug", variant="primary")
        self.tool_id = None

    def set_tool_id(self, tool_id: str) -> None:
        """Set the tool ID to debug."""
        self.tool_id = tool_id

    def on_button_pressed(self) -> None:
        """Run SQL debug when button is pressed."""
        # Call the app's handler first
        if hasattr(self.app, "on_sql_debug_button_pressed"):
            self.app.on_sql_debug_button_pressed()

        if not self.tool_id:
            self.app.query_one(DetailPanel).update(
                "# SQL Debug\n\nNo tool selected. Select a tool first."
            )
            return

        try:
            debug_result = self._run_direct_sql_debug(self.tool_id)
            self.app.query_one(DetailPanel).update(debug_result)
        except Exception as e:
            error_msg = f"# SQL Debug Error\n\n```\n{str(e)}\n\n{traceback.format_exc()}\n```"
            self.app.query_one(DetailPanel).update(error_msg)

    def _run_direct_sql_debug(self, tool_id: str) -> str:
        """Run direct SQL queries to debug the database."""
        result = "# SQL Debug Results\n\n"

        with Session(engine) as session:
            # Query the tool
            result += "## Tool Information\n\n"
            tool = session.get(CLITool, tool_id)
            if not tool:
                return f"Tool with ID {tool_id} not found in database."

            result += f"- **ID:** {tool.id}\n"
            result += f"- **Name:** {tool.name}\n"
            result += f"- **Version:** {tool.version or 'N/A'}\n"
            result += f"- **Created:** {tool.created_at}\n\n"

            # Direct SQL for commands
            result += "## Commands (Direct SQL)\n\n"
            commands = session.exec(select(Command).where(Command.cli_tool_id == tool_id)).all()

            result += f"Found {len(commands)} commands in total.\n\n"

            # List all commands
            for i, cmd in enumerate(commands):
                result += f"### {i + 1}. {cmd.name}\n"
                result += f"- **ID:** {cmd.id}\n"
                result += f"- **Description:** {cmd.description or 'N/A'}\n"
                result += f"- **Is Subcommand:** {cmd.is_subcommand}\n"
                result += f"- **Parent ID:** {cmd.parent_command_id or 'N/A'}\n\n"

                # Check for relationships
                options = session.exec(select(Option).where(Option.command_id == cmd.id)).all()
                arguments = session.exec(
                    select(Argument).where(Argument.command_id == cmd.id)
                ).all()
                examples = session.exec(select(Example).where(Example.command_id == cmd.id)).all()
                subcommands = session.exec(
                    select(Command).where(Command.parent_command_id == cmd.id)
                ).all()

                result += f"- **Options:** {len(options)}\n"
                result += f"- **Arguments:** {len(arguments)}\n"
                result += f"- **Examples:** {len(examples)}\n"
                result += f"- **Subcommands:** {len(subcommands)}\n\n"

        return result


class DBBrowserApp(App):
    """Database Browser Application."""

    TITLE = "Testronaut DB Browser"
    SUB_TITLE = "Browse CLI Analysis Results"
    CSS_PATH = "styles/browser.tcss"

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
        self.debug_button = SQLDebugButton()

    def compose(self) -> ComposeResult:
        """Compose the app layout."""
        yield Header()

        with Container(id="app-grid"):
            # Left panel with tools list and search
            with Vertical(id="left-panel"):
                yield Label("CLI Tools", id="tools-header")
                with Horizontal(id="search-container"):
                    yield SearchInput()
                yield ToolsTable()
                yield self.debug_button

            # Middle panel with command tree
            with Vertical(id="middle-panel"):
                yield CommandTree()

            # Right panel with details
            with Vertical(id="right-panel"):
                yield DetailPanel()

        yield Footer()

    def on_mount(self) -> None:
        """Handle the app mount event."""
        # If a tool ID was provided at startup, select it
        if self.selected_tool_id:
            self.select_tool(self.selected_tool_id)

    @on(Input.Changed)
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if isinstance(event.input, SearchInput) and len(event.value) >= 2:
            self.search_commands(event.value)
        elif isinstance(event.input, SearchInput) and not event.value:
            self.clear_search()

    def search_commands(self, query: str) -> None:
        """Search for commands matching the query."""
        self.search_results = self.repository.search_commands(query)

        # Update the tree to show search results
        command_tree = self.query_one(CommandTree)
        command_tree.clear()
        command_tree.root.label = f"Search Results: {query}"

        if not self.search_results:
            command_tree.root.add("No results found")
            return

        # Group by tool
        results_by_tool = {}
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
                    cmd_label += f": {cmd['description']}"

                # Make sure we store the command dictionary as data
                tool_node.add(cmd_label, data=cmd)

        self.search_active = True

    def select_tool(self, tool_id: str) -> None:
        """Select a tool and display its commands."""
        if not tool_id:
            ui_logger.warning("Attempted to select tool with empty ID")
            return

        ui_logger.warning(f"Selecting tool with ID: {tool_id}")
        self.selected_tool_id = tool_id
        self.debug_button.set_tool_id(tool_id)

        # Get the tool detail first to verify it exists
        repository = DBBrowserRepository()
        tool_detail = repository.get_tool_detail(tool_id)

        if not tool_detail:
            ui_logger.warning(f"Could not load tool with ID: {tool_id}")
            detail_panel = self.query_one(DetailPanel)
            detail_panel.update("# Error\n\nSelected tool could not be loaded from the database.")
            return

        ui_logger.warning(f"Successfully loaded tool: {tool_detail['name']}")

        # Update the command tree
        command_tree = self.query_one(CommandTree)
        command_tree.load_tool(tool_id)

        # Update the detail panel with tool information
        detail_panel = self.query_one(DetailPanel)
        detail_panel.update(self._format_tool_detail(tool_detail))

        # Log command loading for debugging
        cmd_count = len(tool_detail.get("commands", []))
        ui_logger.warning(f"Loaded tool {tool_detail.get('name')} with {cmd_count} commands")

    def _format_tool_detail(self, tool: Dict) -> str:
        """Format tool details for display."""
        content = f"# Tool: {tool['name']}\n\n"

        if tool.get("version"):
            content += f"**Version:** {tool['version']}\n\n"

        if tool.get("description"):
            content += f"**Description:** {tool['description']}\n\n"

        if tool.get("install_command"):
            content += f"**Install Command:** `{tool['install_command']}`\n\n"

        if tool.get("help_text"):
            content += "## Help Text\n\n"
            content += f"```\n{tool['help_text']}\n```\n\n"

        cmd_count = len(tool.get("commands", []))
        content += f"**Commands:** {cmd_count}\n\n"

        content += "Select a command from the tree to see its details."
        return content

    def action_refresh(self) -> None:
        """Refresh the current view."""
        if self.search_active:
            search_input = self.query_one(SearchInput)
            self.search_commands(search_input.value)
        else:
            tools_table = self.query_one(ToolsTable)
            tools_table.refresh_tools()

            if self.selected_tool_id:
                self.select_tool(self.selected_tool_id)

    def action_focus_search(self) -> None:
        """Focus the search input."""
        self.query_one(SearchInput).focus()

    def action_clear_search(self) -> None:
        """Clear the search results."""
        self.clear_search()

    def clear_search(self) -> None:
        """Clear search results and restore previous view."""
        search_input = self.query_one(SearchInput)
        search_input.value = ""

        self.search_active = False
        self.search_results = []

        if self.selected_tool_id:
            self.select_tool(self.selected_tool_id)
        else:
            command_tree = self.query_one(CommandTree)
            command_tree.clear()
            command_tree.root.label = "Commands"

    @on(ToolSelected)
    def handle_tool_selected(self, message: ToolSelected) -> None:
        """Handle tool selection event."""
        self.search_active = False
        ui_logger.debug(f"======= TOOL SELECTION TRIGGERED FOR ID: {message.tool_id} =======")
        self.select_tool(message.tool_id)

    @on(CommandSelected)
    def handle_command_selected(self, message: CommandSelected) -> None:
        """Handle command selection event."""
        detail_panel = self.query_one(DetailPanel)
        detail_panel.show_command(message.command)

    def on_sql_debug_button_pressed(self) -> None:
        """Handle SQL debug button press."""
        ui_logger.debug(
            f"======= SQL DEBUG BUTTON PRESSED FOR TOOL ID: {self.selected_tool_id} ======="
        )
        # The default handler in SQLDebugButton will take care of the rest


def run_browser(tool_id: Optional[str] = None) -> None:
    """
    Run the database browser app.

    Args:
        tool_id: Optional ID of tool to load on startup
    """
    ui_logger.debug(f"Starting browser with tool_id: {tool_id}")
    try:
        app = DBBrowserApp(tool_id)
        app.run()
    except Exception as e:
        ui_logger.error(f"Error running browser app: {str(e)}")
        ui_logger.debug(traceback.format_exc())

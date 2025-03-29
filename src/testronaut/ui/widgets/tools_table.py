"""
ToolsTable Widget for the Testronaut DB Browser.
"""
from datetime import datetime
from typing import Optional

from textual.widgets import DataTable
from textual.message import Message

# Assuming repository and messages are accessible or imported appropriately
# Adjust imports based on actual project structure if needed
from testronaut.ui.repository import DBBrowserRepository
# Define or import ToolSelected message if not globally available
# from testronaut.ui.messages import ToolSelected

# Placeholder for ToolSelected if not defined elsewhere yet
class ToolSelected(Message):
    """Message sent when a tool is selected."""
    def __init__(self, tool_id: str):
        self.tool_id = tool_id
        super().__init__()


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
        # Initialize repository here or pass it in if needed
        self.repository = DBBrowserRepository()

    def on_mount(self) -> None:
        """Setup the table when mounted."""
        self.add_columns("Tool Name", "Version", "Commands", "Options", "Arguments", "Analyzed At")
        self.refresh_tools()

    def refresh_tools(self) -> None:
        """Refresh the list of tools."""
        self.clear()
        tools = self.repository.get_all_tools()

        for tool in tools:
            command_count = tool.get("command_count", 0)
            option_count = tool.get("option_count", 0)
            argument_count = tool.get("argument_count", 0)
            created_at = tool.get("created_at")

            if created_at:
                if isinstance(created_at, datetime):
                    created_at_str = created_at.strftime("%Y-%m-%d %H:%M")
                else:
                    # Attempt to parse if string, otherwise use as is
                    try:
                        dt_obj = datetime.fromisoformat(str(created_at))
                        created_at_str = dt_obj.strftime("%Y-%m-%d %H:%M")
                    except (ValueError, TypeError):
                         created_at_str = str(created_at) # Fallback
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
        if self.row_count == 0:
            return # No rows to select

        selected_row_index = self.cursor_row
        # Ensure cursor is within bounds
        if 0 <= selected_row_index < self.row_count:
            try:
                # Use coordinate_to_row_key to get the key associated with the cursor row
                # Ignore potential Pylance false positive if type hints are inaccurate
                row_key = self.coordinate_to_row_key(self.cursor_coordinate) # type: ignore
                if row_key is not None: # Check if a key was found
                    self.post_message(ToolSelected(str(row_key)))
                else:
                    # Log if no key found for the coordinate (shouldn't happen if added correctly)
                    # logger.warning(f"No row key found for coordinate {self.cursor_coordinate}")
                    pass
            except Exception as e:
                 # Log error if getting row key fails
                 # Consider adding logging here if needed
                 pass # Or log the error: logger.error(f"Error selecting tool: {e}")

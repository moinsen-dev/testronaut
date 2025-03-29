"""
SQLDebugButton Widget for the Testronaut DB Browser.
"""
import traceback
from typing import Optional

from sqlmodel import Session, select
from textual.widgets import Button
from textual.message import Message # Import Message

# Assuming models and engine are accessible or imported appropriately
# Adjust imports based on actual project structure if needed
from testronaut.models.base import engine
from testronaut.models.cli_tool import Argument, CLITool, Command, Example, Option

# Assuming logger is accessible or imported appropriately
# import logging
# ui_logger = logging.getLogger("testronaut.ui.widget.sql_debug_button")

# Define a message for the button press
class SQLDebugRequested(Message):
    """Message posted when the SQL Debug button is pressed."""
    pass


class SQLDebugButton(Button):
    """Button to run direct SQL diagnostics."""

    def __init__(self) -> None:
        """Initialize the debug button."""
        super().__init__("Run SQL Debug", variant="primary", id="sql-debug-button")
        self.tool_id: Optional[str] = None

    def set_tool_id(self, tool_id: Optional[str]) -> None:
        """Set the tool ID to debug."""
        self.tool_id = tool_id
        self.disabled = not bool(tool_id) # Disable if no tool ID

    def on_button_pressed(self) -> None:
        """Post a message and run SQL debug when button is pressed."""
        # Post a message instead of calling the app directly
        self.post_message(SQLDebugRequested())

        # Still need to find the DetailPanel to display results
        # Using query_one requires knowing the app structure, which might be fragile.
        # A better approach might be for the app to handle the result display
        # in response to the SQLDebugRequested message.
        # For now, keep the existing logic but acknowledge its potential fragility.
        detail_panel = getattr(self.app, "query_one", lambda _: None)(
            "DetailPanel", expect_type=Static # type: ignore
        )
        if not detail_panel:
             # Cannot display results if panel not found
             # logger.error("DetailPanel not found in app for SQL debug results.")
             return

        if not self.tool_id:
            detail_panel.update(
                "# SQL Debug\n\nNo tool selected. Select a tool first."
            )
            return

        try:
            debug_result = self._run_direct_sql_debug(self.tool_id)
            detail_panel.update(debug_result)
        except Exception as e:
            error_msg = f"# SQL Debug Error\n\n```\n{str(e)}\n\n{traceback.format_exc()}\n```"
            detail_panel.update(error_msg)

    def _run_direct_sql_debug(self, tool_id: str) -> str:
        """Run direct SQL queries to debug the database."""
        result = f"# SQL Debug Results (Tool ID: {tool_id})\n\n"

        try:
            with Session(engine) as session:
                # Query the tool
                result += "## Tool Information\n\n"
                tool = session.get(CLITool, tool_id)
                if not tool:
                    return result + f"Tool with ID {tool_id} not found in database."

                result += f"- **ID:** {tool.id}\n"
                result += f"- **Name:** {tool.name}\n"
                result += f"- **Version:** {tool.version or 'N/A'}\n"
                result += f"- **Created:** {tool.created_at}\n\n"

                # Direct SQL for commands
                result += "## Commands (Direct SQL)\n\n"
                commands = session.exec(select(Command).where(Command.cli_tool_id == tool_id)).all()

                result += f"Found {len(commands)} commands linked to this tool.\n\n"

                # List all commands
                for i, cmd in enumerate(commands):
                    result += f"### {i + 1}. {cmd.name}\n"
                    result += f"- **ID:** {cmd.id}\n"
                    result += f"- **Description:** {cmd.description or 'N/A'}\n"
                    result += f"- **Is Subcommand:** {cmd.is_subcommand}\n"
                    result += f"- **Parent ID:** {cmd.parent_command_id or 'N/A'}\n"

                    # Check for relationships
                    options = session.exec(select(Option).where(Option.command_id == cmd.id)).all()
                    arguments = session.exec(
                        select(Argument).where(Argument.command_id == cmd.id)
                    ).all()
                    examples = session.exec(select(Example).where(Example.command_id == cmd.id)).all()
                    # Query subcommands based on parent_id relationship
                    subcommands = session.exec(
                        select(Command).where(Command.parent_command_id == cmd.id)
                    ).all()

                    result += f"- **Options:** {len(options)}\n"
                    result += f"- **Arguments:** {len(arguments)}\n"
                    result += f"- **Examples:** {len(examples)}\n"
                    result += f"- **Subcommands (Direct Children):** {len(subcommands)}\n\n"

        except Exception as e:
             result += f"\n**Error during SQL query:**\n```\n{str(e)}\n{traceback.format_exc()}\n```"

        return result

# Need to import Static for the type hint in on_button_pressed
from textual.widgets import Static

"""
CommandTree Widget for the Testronaut DB Browser.
"""
import traceback
from typing import Dict, Optional, List # Import List

from textual.message import Message
from textual.widgets import Tree
from textual.widgets.tree import TreeNode

# Assuming repository and logger are accessible or imported appropriately
# Adjust imports based on actual project structure if needed
from testronaut.ui.repository import DBBrowserRepository
# Import the logger and debug_dump from the browser module or a shared utility module
# For now, let's assume they might be defined in browser or need moving to a shared util
# If ui_logger and debug_dump are defined in browser.py, this will need adjustment later
# or we move the logger setup to a shared location.
# Placeholder import:
# from testronaut.ui.browser import ui_logger, debug_dump
# Using standard logging for now if ui_logger isn't easily accessible
import logging
ui_logger = logging.getLogger("testronaut.ui.widget.command_tree") # Use a specific logger

# Placeholder for debug_dump if not easily accessible
def debug_dump(obj, prefix="DEBUG DUMP"):
     pass # Replace with actual implementation or import


class CommandSelected(Message):
    """Message sent when a command is selected."""
    def __init__(self, command: Dict):
        self.command = command
        super().__init__()


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
        # Initialize repository here or pass it in if needed
        self.repository = DBBrowserRepository()

    def load_tool(self, tool_id: str) -> None:
        """Load command tree for a specific tool."""
        ui_logger.debug(f"===== LOAD_TOOL START: {tool_id} =====")
        self.selected_tool_id = tool_id
        self.clear() # Clear existing nodes
        self.root.remove_children() # Ensure root is empty before adding

        try:
            ui_logger.debug(f"Loading tool with ID: {tool_id}")
            tool_detail = self.repository.get_tool_detail(tool_id)

            if not tool_detail:
                ui_logger.error(f"No tool found with ID: {tool_id}")
                self.root.set_label("Tool not found") # Update root label
                # self.root.add("Tool not found in database") # Don't add child if root indicates error
                return

            ui_logger.debug(
                f"Retrieved tool: {tool_detail['name']} with keys: {list(tool_detail.keys())}"
            )
            self.root.set_label(f"Commands: {tool_detail['name']} {tool_detail.get('version', '')}")
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
                self.root.add("No commands found for this tool") # Add message as child
                return

            # Add top-level commands (those without a parent_command_id or where it's None)
            commands_added = 0
            for cmd in commands:
                if not cmd.get("parent_command_id"):
                    try:
                        ui_logger.debug(f"Adding top-level command: {cmd.get('name', 'Unnamed')}")
                        self._add_command_to_tree(cmd, self.root, commands)
                        commands_added += 1
                    except Exception as e:
                        ui_logger.error(f"Error adding command {cmd.get('name', 'Unknown')}: {str(e)}")
                        ui_logger.debug(traceback.format_exc())

            ui_logger.debug(
                f"Finished loading {commands_added} top-level commands for tool {tool_detail['name']}"
            )
        except Exception as e:
            ui_logger.error(f"Error in load_tool: {str(e)}")
            ui_logger.debug(traceback.format_exc())
            self.root.set_label("Error Loading Tool") # Update root label on error
            # self.root.add(f"Error: {str(e)}") # Don't add child if root indicates error
        finally:
            self.refresh(layout=True) # Refresh tree layout
            ui_logger.debug(f"===== LOAD_TOOL END: {tool_id} =====")

    def _add_command_to_tree(self, command_data: Dict, parent_node: TreeNode, all_commands: List[Dict]) -> None:
        """Recursively add commands to the tree, finding children from the flat list."""
        command_id = command_data.get("id")
        if not command_id:
            ui_logger.warning(f"Command data missing 'id': {command_data.get('name', 'Unknown')}")
            return

        # Avoid adding the same command ID multiple times under different parents if structure is odd
        if command_id in self.command_nodes:
             # If it already exists, maybe just ensure it's under the correct parent?
             # For simplicity now, we just skip re-adding.
             # ui_logger.debug(f"Command node {command_id} already exists.")
             return

        # Create node label with icon based on command type
        icon = "🔸" if command_data.get("is_subcommand") else "🔹"
        cmd_label = f"{icon} {command_data.get('name', 'Unnamed')}"
        # Keep label concise for the tree view
        # if command_data.get("description"):
        #     cmd_label += f": {command_data['description'][:30]}..." # Truncate description

        # Add node to tree
        try:
            node = parent_node.add(cmd_label, data=command_data)
            self.command_nodes[command_id] = node
            ui_logger.debug(f"Added node for {command_id} ('{command_data.get('name')}') under parent {parent_node.data.get('id') if parent_node.data else 'root'}")

            # Find and add subcommands recursively by checking parent_command_id
            for sub_cmd_data in all_commands:
                if sub_cmd_data.get("parent_command_id") == command_id:
                    self._add_command_to_tree(sub_cmd_data, node, all_commands)
        except Exception as e:
             ui_logger.error(f"Error adding node {command_data.get('name', 'Unknown')} to tree: {e}")
             ui_logger.debug(traceback.format_exc())


    def action_select_command(self) -> None:
        """Handle command selection."""
        node = self.cursor_node
        if node and node.data:
            # Make sure we're sending a dictionary, not a string or None
            if isinstance(node.data, dict):
                self.post_message(CommandSelected(node.data))
            else:
                ui_logger.warning(f"Invalid command data type on node selection: {type(node.data)}")
        else:
             ui_logger.debug("Command selection action triggered on invalid node.")

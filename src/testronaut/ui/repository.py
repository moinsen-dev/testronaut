"""
Repository for the UI database browser.

This module provides database access functions specifically tailored
for the UI database browser, with methods for retrieving and formatting
data for display.
"""

import logging
import traceback
from typing import Dict, List, Optional

from sqlmodel import Session, select

from testronaut.models.base import engine
from testronaut.models.cli_tool import CLITool, Command
from testronaut.repositories.cli_tool import CLIToolRepository

# Use the UI logger from browser.py
ui_logger = logging.getLogger("testronaut.ui")


class DBBrowserRepository:
    """Repository for database browser UI."""

    def __init__(self):
        """Initialize the repository."""
        self.cli_tool_repo = CLIToolRepository()
        ui_logger.debug("DBBrowserRepository initialized")

    def get_all_tools(self, with_summary: bool = True) -> List[Dict]:
        """
        Get all CLI tools with optional summary data.

        Args:
            with_summary: Whether to include command count summary

        Returns:
            List of CLI tools as dictionaries with display-friendly data
        """
        ui_logger.debug(f"Getting all tools (with_summary={with_summary})")
        result = []

        try:
            with Session(engine) as session:
                # Get all tools within the session
                statement = session.query(CLITool)
                tools = statement.all()

                ui_logger.debug(f"Found {len(tools)} CLI tools in database")

                for tool in tools:
                    # Basic tool data
                    tool_data = {
                        "id": tool.id,
                        "name": tool.name,
                        "version": tool.version or "Unknown",
                        "created_at": tool.created_at,
                    }

                    if with_summary:
                        # Retrieve command counts while in session
                        commands = (
                            session.query(Command).filter(Command.cli_tool_id == tool.id).all()
                        )
                        tool_data["command_count"] = len(commands)
                        tool_data["top_level_commands"] = sum(
                            1 for cmd in commands if not cmd.is_subcommand
                        )

                        # Count options, arguments, and examples
                        option_count = 0
                        argument_count = 0
                        example_count = 0

                        # For each command, count its related items
                        for cmd in commands:
                            # Relationships are accessed within the session
                            option_count += len(
                                session.query(Command).filter(Command.id == cmd.id).one().options
                            )
                            argument_count += len(
                                session.query(Command).filter(Command.id == cmd.id).one().arguments
                            )
                            example_count += len(
                                session.query(Command).filter(Command.id == cmd.id).one().examples
                            )

                        tool_data["option_count"] = option_count
                        tool_data["argument_count"] = argument_count
                        tool_data["example_count"] = example_count

                        ui_logger.debug(
                            f"Tool {tool.name}: {len(commands)} commands, {option_count} options, {argument_count} arguments"
                        )

                    result.append(tool_data)
        except Exception as e:
            ui_logger.error(f"Error getting all tools: {str(e)}")
            ui_logger.debug(traceback.format_exc())

        return result

    def get_tool_detail(self, tool_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific CLI tool.

        Args:
            tool_id: ID of the CLI tool

        Returns:
            Dictionary with tool data or None if not found
        """
        ui_logger.debug(f"===== GET_TOOL_DETAIL START: {tool_id} =====")

        try:
            # Simplified approach: Direct SQL to get the tool first
            with Session(engine) as session:
                # Get the basic tool info
                tool = session.get(CLITool, tool_id)
                if not tool:
                    ui_logger.warning(f"Tool with ID {tool_id} not found")
                    return None

                # Create result dictionary with basic tool info
                result = {
                    "id": tool.id,
                    "name": tool.name,
                    "version": tool.version,
                    "created_at": tool.created_at,
                    "description": tool.description,
                    "help_text": tool.help_text,
                    "install_command": tool.install_command,
                    "commands": [],
                }

                ui_logger.debug(f"Basic tool info retrieved for {tool.name}")

                # Direct SQL approach: Get all commands for this tool in one query
                all_commands = session.exec(
                    select(Command).where(Command.cli_tool_id == tool.id)
                ).all()

                ui_logger.debug(f"Found {len(all_commands)} total commands for tool {tool.name}")

                # If no commands, return early
                if not all_commands:
                    ui_logger.warning(f"No commands found for tool {tool.name}")
                    return result

                # Create command dictionary by ID for easier lookup
                command_dict = {cmd.id: self._format_command_basic(cmd) for cmd in all_commands}

                # Identify top-level commands (not subcommands)
                top_level_commands = [cmd for cmd in all_commands if not cmd.is_subcommand]

                ui_logger.debug(f"Found {len(top_level_commands)} top-level commands")

                # Process top-level commands, format them and add to result
                for cmd in top_level_commands:
                    cmd_data = command_dict[cmd.id]

                    # Find subcommands
                    subcommands = [
                        subcmd for subcmd in all_commands if subcmd.parent_command_id == cmd.id
                    ]
                    ui_logger.debug(f"Command {cmd.name} has {len(subcommands)} direct subcommands")

                    # Add subcommands
                    if subcommands:
                        cmd_data["subcommands"] = []
                        for subcmd in subcommands:
                            subcmd_data = command_dict[subcmd.id]
                            # Find nested subcommands (if any)
                            nested_subcommands = [
                                nc for nc in all_commands if nc.parent_command_id == subcmd.id
                            ]
                            if nested_subcommands:
                                subcmd_data["subcommands"] = []
                                for nested in nested_subcommands:
                                    nested_data = command_dict[nested.id]
                                    subcmd_data["subcommands"].append(nested_data)
                            cmd_data["subcommands"].append(subcmd_data)

                    # Add the complete command data to result
                    result["commands"].append(cmd_data)
                    ui_logger.debug(f"Added command {cmd.name} to result")

                ui_logger.debug(f"Returning tool with {len(result['commands'])} commands")
                return result

        except Exception as e:
            ui_logger.error(f"Error getting tool detail: {str(e)}")
            ui_logger.debug(traceback.format_exc())
            return None
        finally:
            ui_logger.debug(f"===== GET_TOOL_DETAIL END: {tool_id} =====")

    def _format_command_basic(self, cmd: Command) -> Dict:
        """
        Format a command for display with basic information.

        Args:
            cmd: Command object

        Returns:
            Dictionary with formatted command data
        """
        return {
            "id": cmd.id,
            "name": cmd.name,
            "description": cmd.description,
            "syntax": cmd.syntax,
            "help_text": cmd.help_text,
            "is_subcommand": cmd.is_subcommand,
            "options": [],
            "arguments": [],
            "examples": [],
        }

    def get_command_detail(self, command_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific command.

        Args:
            command_id: ID of the command

        Returns:
            Dictionary with command data or None if not found
        """
        ui_logger.debug(f"Getting command detail for ID: {command_id}")
        try:
            with Session(engine) as session:
                command = session.get(Command, command_id)
                if not command:
                    ui_logger.warning(f"Command with ID {command_id} not found")
                    return None

                return self._format_command(command)
        except Exception as e:
            ui_logger.error(f"Error getting command detail: {str(e)}")
            ui_logger.debug(traceback.format_exc())
            return None

    def _format_command(self, command: Command, session=None) -> Dict:
        """
        Format a command for display.

        Args:
            command: Command object
            session: Optional active SQLAlchemy session

        Returns:
            Dictionary with formatted command data
        """
        # Create a session if not provided
        close_session = False
        if session is None:
            session = Session(engine)
            close_session = True

        try:
            # Log information about the command being formatted
            ui_logger.debug(f"Formatting command: {command.name} (ID: {command.id})")

            # Re-query the command within this session to ensure relationships are loaded
            cmd = session.get(Command, command.id)
            if not cmd:
                ui_logger.warning(f"Could not retrieve command {command.id}")
                return {
                    "id": command.id,
                    "name": command.name,
                    "description": "Error: Command could not be loaded",
                }

            cmd_data = {
                "id": cmd.id,
                "name": cmd.name,
                "description": cmd.description,
                "syntax": cmd.syntax,
                "help_text": cmd.help_text,
                "is_subcommand": cmd.is_subcommand,
                "options": [],
                "arguments": [],
                "examples": [],
                "subcommands": [],
            }

            # Use direct queries to get related entities
            from testronaut.models.cli_tool import Argument, Example, Option

            # Get options
            options = session.exec(select(Option).where(Option.command_id == cmd.id)).all()

            for opt in options:
                opt_data = {
                    "id": opt.id,
                    "name": opt.name,
                    "short_form": opt.short_form,
                    "long_form": opt.long_form,
                    "description": opt.description,
                    "required": opt.required,
                    "default_value": opt.default_value,
                    "value_type": opt.value_type,
                }
                cmd_data["options"].append(opt_data)

            ui_logger.debug(f"Added {len(options)} options for command {cmd.name}")

            # Get arguments
            arguments = session.exec(select(Argument).where(Argument.command_id == cmd.id)).all()

            for arg in arguments:
                arg_data = {
                    "id": arg.id,
                    "name": arg.name,
                    "description": arg.description,
                    "required": arg.required,
                    "default_value": arg.default_value,
                    "value_type": arg.value_type,
                    "position": arg.position,
                }
                cmd_data["arguments"].append(arg_data)

            ui_logger.debug(f"Added {len(arguments)} arguments for command {cmd.name}")

            # Get examples
            examples = session.exec(select(Example).where(Example.command_id == cmd.id)).all()

            for ex in examples:
                ex_data = {
                    "id": ex.id,
                    "description": ex.description,
                    "command_line": ex.command_line,
                    "expected_output": ex.expected_output,
                }
                cmd_data["examples"].append(ex_data)

            ui_logger.debug(f"Added {len(examples)} examples for command {cmd.name}")

            # Get subcommands
            subcommands = session.exec(
                select(Command).where(Command.parent_command_id == cmd.id)
            ).all()

            ui_logger.debug(f"Found {len(subcommands)} subcommands for command {cmd.name}")

            # Add subcommands recursively
            for subcmd in subcommands:
                subcmd_data = self._format_command(subcmd, session)
                cmd_data["subcommands"].append(subcmd_data)

            return cmd_data
        except Exception as e:
            ui_logger.error(f"Error formatting command {command.name}: {str(e)}")
            ui_logger.debug(traceback.format_exc())
            return {
                "id": command.id,
                "name": command.name,
                "description": f"Error formatting command: {str(e)}",
            }
        finally:
            if close_session:
                session.close()

    def search_commands(self, query: str) -> List[Dict]:
        """
        Search for commands matching the query.

        Args:
            query: Search query string

        Returns:
            List of matching commands
        """
        ui_logger.debug(f"Searching for commands with query: '{query}'")
        results = []
        query_lower = query.lower()

        try:
            with Session(engine) as session:
                # Get all commands
                statement = select(Command)
                commands = session.exec(statement).all()

                ui_logger.debug(f"Searching through {len(commands)} commands")

                # Filter commands manually
                for cmd in commands:
                    cmd_name = cmd.name.lower() if cmd.name else ""
                    cmd_desc = cmd.description.lower() if cmd.description else ""

                    if query_lower in cmd_name or query_lower in cmd_desc:
                        # Get the parent tool
                        tool = session.get(CLITool, cmd.cli_tool_id)

                        cmd_data = {
                            "id": cmd.id,
                            "name": cmd.name,
                            "description": cmd.description,
                            "tool_name": tool.name if tool else "Unknown",
                            "tool_id": tool.id if tool else None,
                            "is_subcommand": cmd.is_subcommand,
                        }
                        results.append(cmd_data)

                ui_logger.debug(f"Search found {len(results)} matching commands")
        except Exception as e:
            ui_logger.error(f"Error searching commands: {str(e)}")
            ui_logger.debug(traceback.format_exc())

        return results

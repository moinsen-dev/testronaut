"""
CLI tool repository for database operations.

This module provides repository implementations for CLI Tool related models,
including tools, commands, options, arguments, and examples.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlmodel import Session, select

from testronaut.models.base import Repository, engine
from testronaut.models.cli_tool import (
    CLITool,
    Command,
    add_relationship_analysis,
    add_semantic_analysis,
)
from testronaut.utils.version import requires_reanalysis


class CLIToolRepository(Repository[CLITool]):
    """Repository for CLITool model."""

    def __init__(self):
        """Initialize the repository with the CLITool model class."""
        super().__init__(CLITool)

    def get_tool_by_id(self, tool_id: int) -> Optional[CLITool]:
        """
        Get a CLI tool by its ID with all relationships eagerly loaded.

        Args:
            tool_id: The ID of the CLI tool

        Returns:
            The CLI tool or None if not found
        """
        with Session(engine) as session:
            # First get the basic tool to check if it exists
            statement = select(CLITool).where(CLITool.id == tool_id)
            tool = session.exec(statement).first()

            if not tool:
                return None

            # Get the tool with all relationships within the session context
            tool_with_relations = session.get(CLITool, tool.id)

            if tool_with_relations:
                # Trigger loading of relationships
                commands = (
                    list(tool_with_relations.commands)
                    if hasattr(tool_with_relations, "commands")
                    else []
                )

                # Trigger loading of nested relationships
                for cmd in commands:
                    _ = list(cmd.options) if hasattr(cmd, "options") else []
                    _ = list(cmd.arguments) if hasattr(cmd, "arguments") else []
                    _ = list(cmd.examples) if hasattr(cmd, "examples") else []
                    _ = list(cmd.subcommands) if hasattr(cmd, "subcommands") else []

            return tool_with_relations

    def get_by_name(self, name: str) -> Optional[CLITool]:
        """
        Get a CLI tool by its name with all relationships eagerly loaded.

        Args:
            name: The name of the CLI tool

        Returns:
            The CLI tool or None if not found
        """
        with Session(engine) as session:
            # First get the basic tool to check if it exists
            statement = select(CLITool).where(CLITool.name == name)
            tool = session.exec(statement).first()

            if not tool:
                return None

            # Get the tool with all relationships within the session context
            tool_with_relations = session.get(CLITool, tool.id)

            if tool_with_relations:
                # Trigger loading of relationships
                commands = list(tool_with_relations.commands)

                # Trigger loading of nested relationships
                for cmd in commands:
                    _ = list(cmd.options)
                    _ = list(cmd.arguments)
                    _ = list(cmd.examples)
                    _ = list(cmd.subcommands)

            return tool_with_relations

    def check_analysis_needed(
        self, name: str, version: Optional[str] = None
    ) -> Tuple[bool, Optional[CLITool]]:
        """
        Check if a CLI tool needs to be analyzed based on version.

        This method compares the current version with the stored version
        to determine if reanalysis is needed based on semantic versioning rules.

        Args:
            name: The name of the CLI tool
            version: The current version of the tool (optional)

        Returns:
            A tuple of (needs_analysis, existing_tool)
            - needs_analysis: True if analysis is needed, False otherwise
            - existing_tool: The existing tool if found, None otherwise
        """
        # Get existing tool if any
        existing_tool = self.get_by_name(name)

        # If tool doesn't exist, analysis is needed
        if not existing_tool:
            return True, None

        # If version is not provided, reanalyze
        if not version:
            return True, existing_tool

        # If existing tool doesn't have a version, reanalyze
        if not existing_tool.version:
            return True, existing_tool

        # Compare versions to determine if reanalysis is needed
        return requires_reanalysis(existing_tool.version, version), existing_tool

    def save_analysis_results(
        self,
        cli_tool: CLITool,
        semantic_analysis: Optional[Dict[str, Any]] = None,
        force_update: bool = False,
    ) -> CLITool:
        """
        Save a complete CLI tool analysis including all related entities.

        This method handles saving or updating a CLI tool and all its
        commands, options, arguments, and examples.

        Args:
            cli_tool: The CLI tool with its complete object graph
            semantic_analysis: Optional semantic analysis data
            force_update: Force update even if reanalysis is not needed

        Returns:
            The saved CLI tool with IDs
        """
        # Check if the CLI tool already exists and if reanalysis is needed
        needs_analysis, existing_tool = self.check_analysis_needed(cli_tool.name, cli_tool.version)

        # If no reanalysis is needed and we're not forcing it, return the existing tool
        if not needs_analysis and not force_update and existing_tool:
            return existing_tool

        with Session(engine) as session:
            if existing_tool:
                # Update existing tool
                cli_tool.id = existing_tool.id
                cli_tool.created_at = existing_tool.created_at

                # Delete all existing related entities (cascading delete)
                session.delete(existing_tool)
                session.commit()

            # Add semantic analysis if provided
            if semantic_analysis:
                add_relationship_analysis(cli_tool, semantic_analysis)

            # Convert MetaData object to dict before saving
            if cli_tool.meta_data:
                # Use model_dump for SQLModel/Pydantic objects
                cli_tool.meta_data = cli_tool.meta_data.model_dump(mode='json')

            # Save the tool and all related entities
            session.add(cli_tool)
            session.commit()
            session.refresh(cli_tool)

            # Eagerly load the commands relationship within the session
            # before returning the detached object.
            _ = cli_tool.commands

            return cli_tool

    def list(self, skip: int = 0, limit: int = 100) -> List[CLITool]:
        """
        List all CLI tools with their commands eagerly loaded.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of CLI tools with commands populated
        """
        tools = []
        with Session(engine) as session:
            statement = select(CLITool).offset(skip).limit(limit)
            db_tools = session.exec(statement).all()

            # For each tool, eagerly load its commands and related entities
            for tool in db_tools:
                # Execute a query to get the tool with commands, options, etc.
                stmt = select(CLITool).where(CLITool.id == tool.id)
                loaded_tool = session.exec(stmt).first()

                # Trigger loading of relationships
                if loaded_tool is not None:
                    _ = [cmd.name for cmd in loaded_tool.commands]
                    tools.append(loaded_tool)

        return tools

    def get_commands_for_tool(self, tool_id: int) -> List[Command]:
        """
        Get all commands for a specific CLI tool.

        Args:
            tool_id: The ID of the CLI tool

        Returns:
            List of commands for the tool
        """
        with Session(engine) as session:
            statement = select(Command).where(Command.cli_tool_id == tool_id)
            commands = session.exec(statement).all()
            return list(commands)


class CommandRepository(Repository[Command]):
    """Repository for Command model."""

    def __init__(self):
        """Initialize the repository with the Command model class."""
        super().__init__(Command)

    def get_by_name_and_tool(self, tool_id: str, name: str) -> Optional[Command]:
        """
        Get a command by its name and CLI tool ID.

        Args:
            tool_id: The CLI tool ID
            name: The command name

        Returns:
            The command or None if not found
        """
        with Session(engine) as session:
            statement = select(Command).where(Command.cli_tool_id == tool_id, Command.name == name)
            return session.exec(statement).first()

    def add_semantic_analysis(self, command_id: str, analysis: Dict[str, Any]) -> Optional[Command]:
        """
        Add semantic analysis to a command.

        Args:
            command_id: The command ID
            analysis: The semantic analysis data

        Returns:
            The updated command or None if not found
        """
        with Session(engine) as session:
            command = session.get(Command, command_id)
            if not command:
                return None

            add_semantic_analysis(command, analysis)
            session.add(command)
            session.commit()
            session.refresh(command)
            return command

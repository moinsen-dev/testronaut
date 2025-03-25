"""
CLI tool repository for database operations.

This module provides repository implementations for CLI Tool related models,
including tools, commands, options, arguments, and examples.
"""

from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from testronaut.models.base import Repository, engine
from testronaut.models.cli_tool import (
    CLITool,
    Command,
    add_relationship_analysis,
    add_semantic_analysis,
)


class CLIToolRepository(Repository[CLITool]):
    """Repository for CLITool model."""

    def __init__(self):
        """Initialize the repository with the CLITool model class."""
        super().__init__(CLITool)

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

    def save_analysis_results(
        self, cli_tool: CLITool, semantic_analysis: Optional[Dict[str, Any]] = None
    ) -> CLITool:
        """
        Save a complete CLI tool analysis including all related entities.

        This method handles saving or updating a CLI tool and all its
        commands, options, arguments, and examples.

        Args:
            cli_tool: The CLI tool with its complete object graph
            semantic_analysis: Optional semantic analysis data

        Returns:
            The saved CLI tool with IDs
        """
        # Check if the CLI tool already exists
        existing_tool = self.get_by_name(cli_tool.name)

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

            # Save the tool and all related entities
            session.add(cli_tool)
            session.commit()
            session.refresh(cli_tool)

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

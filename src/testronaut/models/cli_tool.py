"""
CLI tool and command models.

This module defines the data models for CLI tools, commands, options, and arguments.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any, ForwardRef

from sqlmodel import Field, SQLModel, Relationship

from testronaut.models.base import BaseModel


# Forward references for type hints
CommandRef = ForwardRef("Command")
OptionRef = ForwardRef("Option")
ArgumentRef = ForwardRef("Argument")
ExampleRef = ForwardRef("Example")


class CLITool(BaseModel, table=True):
    """Model representing a CLI tool."""

    name: str = Field(index=True)
    version: Optional[str] = Field(default=None)
    install_command: Optional[str] = Field(default=None)
    help_text: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)

    # Relationships
    commands: List[CommandRef] = Relationship(
        back_populates="cli_tool",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class Command(BaseModel, table=True):
    """Model representing a command within a CLI tool."""

    cli_tool_id: str = Field(foreign_key="clitool.id", index=True)
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    syntax: Optional[str] = Field(default=None)
    help_text: Optional[str] = Field(default=None)
    is_subcommand: bool = Field(default=False)
    parent_command_id: Optional[str] = Field(default=None, foreign_key="command.id", index=True)

    # Relationships
    cli_tool: CLITool = Relationship(back_populates="commands")
    parent_command: Optional[CommandRef] = Relationship(
        sa_relationship_kwargs={"remote_side": "Command.id"}
    )
    subcommands: List[CommandRef] = Relationship(
        back_populates="parent_command",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    options: List[OptionRef] = Relationship(
        back_populates="command",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    arguments: List[ArgumentRef] = Relationship(
        back_populates="command",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    examples: List[ExampleRef] = Relationship(
        back_populates="command",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class Option(BaseModel, table=True):
    """Model representing a command-line option."""

    command_id: str = Field(foreign_key="command.id", index=True)
    name: str
    short_form: Optional[str] = Field(default=None)
    long_form: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    required: bool = Field(default=False)
    default_value: Optional[str] = Field(default=None)
    value_type: Optional[str] = Field(default=None)

    # Relationships
    command: Command = Relationship(back_populates="options")


class Argument(BaseModel, table=True):
    """Model representing a positional command-line argument."""

    command_id: str = Field(foreign_key="command.id", index=True)
    name: str
    description: Optional[str] = Field(default=None)
    required: bool = Field(default=False)
    default_value: Optional[str] = Field(default=None)
    value_type: Optional[str] = Field(default=None)
    position: int = Field(default=0)

    # Relationships
    command: Command = Relationship(back_populates="arguments")


class Example(BaseModel, table=True):
    """Model representing an example usage of a command."""

    command_id: str = Field(foreign_key="command.id", index=True)
    description: Optional[str] = Field(default=None)
    command_line: str
    expected_output: Optional[str] = Field(default=None)

    # Relationships
    command: Command = Relationship(back_populates="examples")


# Resolve forward references
Command.update_forward_refs()
CLITool.update_forward_refs()
Option.update_forward_refs()
Argument.update_forward_refs()
Example.update_forward_refs()
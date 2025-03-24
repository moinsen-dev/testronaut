"""
CLI tool and command models.

This module defines the data models for CLI tools, commands, options, and arguments.
"""

from typing import Any, Dict, ForwardRef, List, Optional

from sqlmodel import Field, Relationship, SQLModel

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
        back_populates="cli_tool", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
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
        back_populates="parent_command", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    options: List[OptionRef] = Relationship(
        back_populates="command", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    arguments: List[ArgumentRef] = Relationship(
        back_populates="command", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    examples: List[ExampleRef] = Relationship(
        back_populates="command", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
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


# Semantic analysis extension classes - these are not stored in the database but used for API responses


class SemanticAnalysis(SQLModel):
    """Model representing semantic analysis of a command."""

    primary_function: Optional[str] = None
    common_use_cases: List[str] = []
    key_options: List[Dict[str, str]] = []
    risk_level: str = "unknown"
    alternatives: List[str] = []
    common_patterns: List[str] = []


class CommandRelationship(SQLModel):
    """Model representing a relationship between commands."""

    parent: str
    child: str


class CommandWorkflow(SQLModel):
    """Model representing a workflow involving multiple commands."""

    name: str
    steps: List[str]


class CommandDependency(SQLModel):
    """Model representing a dependency between commands."""

    command: str
    depends_on: str


class RelationshipAnalysis(SQLModel):
    """Model representing relationship analysis between commands."""

    parent_child: List[CommandRelationship] = []
    workflows: List[CommandWorkflow] = []
    dependencies: List[CommandDependency] = []


# Custom serialization/deserialization functions for command metadata
def add_semantic_analysis(command: Command, analysis: Dict[str, Any]) -> None:
    """
    Add semantic analysis to a command as JSON metadata.

    Args:
        command: The command to add metadata to.
        analysis: The semantic analysis dict.
    """
    command._semantic_analysis = SemanticAnalysis(**analysis)


def get_semantic_analysis(command: Command) -> Optional[SemanticAnalysis]:
    """
    Get semantic analysis from a command.

    Args:
        command: The command to get metadata from.

    Returns:
        The semantic analysis object or None.
    """
    return getattr(command, "_semantic_analysis", None)


def add_relationship_analysis(cli_tool: CLITool, analysis: Dict[str, Any]) -> None:
    """
    Add relationship analysis to a CLI tool as JSON metadata.

    Args:
        cli_tool: The CLI tool to add metadata to.
        analysis: The relationship analysis dict.
    """
    relationships = RelationshipAnalysis()

    # Process parent-child relationships
    if "parent_child" in analysis and isinstance(analysis["parent_child"], list):
        relationships.parent_child = [
            CommandRelationship(**rel) for rel in analysis["parent_child"] if isinstance(rel, dict)
        ]

    # Process workflows
    if "workflows" in analysis and isinstance(analysis["workflows"], list):
        relationships.workflows = [
            CommandWorkflow(**wf) for wf in analysis["workflows"] if isinstance(wf, dict)
        ]

    # Process dependencies
    if "dependencies" in analysis and isinstance(analysis["dependencies"], list):
        relationships.dependencies = [
            CommandDependency(**dep) for dep in analysis["dependencies"] if isinstance(dep, dict)
        ]

    cli_tool._relationship_analysis = relationships


def get_relationship_analysis(cli_tool: CLITool) -> Optional[RelationshipAnalysis]:
    """
    Get relationship analysis from a CLI tool.

    Args:
        cli_tool: The CLI tool to get metadata from.

    Returns:
        The relationship analysis object or None.
    """
    return getattr(cli_tool, "_relationship_analysis", None)


# Resolve forward references
Command.update_forward_refs()
CLITool.update_forward_refs()
Option.update_forward_refs()
Argument.update_forward_refs()
Example.update_forward_refs()

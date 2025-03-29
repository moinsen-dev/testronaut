"""
CLI tool and command models.

This module defines the data models for CLI tools, commands, options, and arguments.
"""

from typing import Any, Dict, ForwardRef, List, Optional

from sqlalchemy import JSON
from sqlmodel import Column, Field, Relationship, SQLModel

from testronaut.models.base import BaseModel

# Forward references for type hints
CommandRef = ForwardRef("Command")
OptionRef = ForwardRef("Option")
ArgumentRef = ForwardRef("Argument")
ExampleRef = ForwardRef("Example")


class TokenUsage(SQLModel):
    """Model for tracking LLM token usage during analysis."""

    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    api_calls: int = 0
    estimated_cost: float = 0.0
    models_used: Dict[str, int] = {}

    def add_usage(
        self,
        total_tokens: int = 0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model: Optional[str] = None,
        cost: Optional[float] = None,
    ) -> None:
        """
        Add token usage from an API call.

        Args:
            total_tokens: Total tokens used
            prompt_tokens: Tokens used in the prompt
            completion_tokens: Tokens used in the completion
            model: The model used for this API call
            cost: The estimated cost of this API call
        """
        self.total_tokens += total_tokens
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.api_calls += 1

        # Track usage by model
        if model:
            if model not in self.models_used:
                self.models_used[model] = 0
            self.models_used[model] += total_tokens

        # Add cost if provided, or estimate it
        if cost is not None:
            self.estimated_cost += cost
        elif total_tokens > 0:
            # Estimate cost based on model if provided
            if model and "gpt-4" in model.lower():
                # Approximate GPT-4 pricing
                self.estimated_cost += total_tokens * 0.00001  # $0.01 per 1K tokens
            else:
                # Approximate GPT-3.5 pricing
                self.estimated_cost += total_tokens * 0.000002  # $0.002 per 1K tokens


class MetaData(SQLModel):
    """Model for storing metadata about a CLI tool analysis."""

    llm_usage: Optional[TokenUsage] = None
    semantic_analysis: Optional[Dict[str, Any]] = None
    relationship_analysis: Optional[Dict[str, Any]] = None
    user_preferences: Optional[Dict[str, Any]] = None
    analysis_timestamp: Optional[str] = None


class CLITool(BaseModel, table=True):
    """Model representing a CLI tool."""

    name: str = Field(index=True)
    version: Optional[str] = Field(default=None)
    install_command: Optional[str] = Field(default=None)
    help_text: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    purpose: Optional[str] = Field(default=None, description="Detailed purpose of the tool")
    background: Optional[str] = Field(
        default=None, description="Background information for testing"
    )
    use_cases: Optional[List[str]] = Field(
        default=None, sa_column=Column(JSON), description="Common use cases (stored as JSON)"
    )
    testing_considerations: Optional[List[str]] = Field(
        default=None, sa_column=Column(JSON), description="Testing considerations (stored as JSON)"
    )

    # Metadata for analysis information
    meta_data: MetaData = Field(default_factory=MetaData, sa_column=Column(JSON))

    # Relationships
    commands: List[CommandRef] = Relationship(
        back_populates="cli_tool", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    def track_token_usage(
        self,
        total_tokens: int = 0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model: Optional[str] = None,
        cost: Optional[float] = None,
    ) -> None:
        """
        Track token usage during analysis.

        Args:
            total_tokens: Total tokens used
            prompt_tokens: Tokens used in the prompt
            completion_tokens: Tokens used in the completion
            model: The model used for this API call
            cost: The estimated cost of this API call
        """
        # Initialize token usage if needed
        if not self.meta_data:
            self.meta_data = MetaData()

        if not self.meta_data.llm_usage:
            self.meta_data.llm_usage = TokenUsage()

        # Add the usage
        self.meta_data.llm_usage.add_usage(
            total_tokens=total_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model,
            cost=cost,
        )

    def get_token_usage(self) -> Optional[TokenUsage]:
        """
        Get token usage information.

        Returns:
            TokenUsage object or None if not available
        """
        if not self.meta_data:
            return None

        return self.meta_data.llm_usage


class Command(BaseModel, table=True):
    """Model representing a command within a CLI tool."""

    cli_tool_id: str = Field(foreign_key="clitool.id", index=True)
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    purpose: Optional[str] = Field(default=None, description="Specific purpose of this command")
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

    def model_dump(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """
        Override model_dump to ensure name and description are properly serialized.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            A dictionary representation of the model.
        """
        data = super().model_dump(*args, **kwargs)
        # Ensure name and description are always included
        data["name"] = self.name
        data["description"] = self.description or None
        return data


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

    # Store in the metadata
    if not hasattr(cli_tool, "meta_data") or cli_tool.meta_data is None:
        cli_tool.meta_data = MetaData()

    cli_tool.meta_data.relationship_analysis = relationships.dict()

    # Also keep backward compatibility
    cli_tool._relationship_analysis = relationships


def get_relationship_analysis(cli_tool: CLITool) -> Optional[RelationshipAnalysis]:
    """
    Get relationship analysis from a CLI tool.

    Args:
        cli_tool: The CLI tool to get metadata from.

    Returns:
        The relationship analysis object or None.
    """
    # Try to get from new metadata structure first
    if (
        hasattr(cli_tool, "meta_data")
        and cli_tool.meta_data
        and cli_tool.meta_data.relationship_analysis
    ):
        return RelationshipAnalysis(**cli_tool.meta_data.relationship_analysis)

    # Fall back to legacy attribute
    return getattr(cli_tool, "_relationship_analysis", None)


# Resolve forward references
Command.update_forward_refs()
CLITool.update_forward_refs()
Option.update_forward_refs()
Argument.update_forward_refs()
Example.update_forward_refs()

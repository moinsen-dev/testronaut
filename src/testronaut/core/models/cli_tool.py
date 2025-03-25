"""
Data models for CLI tool information.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CommandParameter(BaseModel):
    """
    Represents a parameter for a CLI command.
    """
    name: str = Field(..., description="Parameter name")
    description: Optional[str] = Field(None, description="Parameter description")
    required: bool = Field(False, description="Whether the parameter is required")
    default: Optional[str] = Field(None, description="Default value for the parameter")
    type: str = Field("string", description="Parameter type (string, number, boolean, etc.)")
    is_flag: bool = Field(False, description="Whether this is a flag parameter")
    short_option: Optional[str] = Field(None, description="Short option form (e.g. -v)")
    long_option: Optional[str] = Field(None, description="Long option form (e.g. --verbose)")


class Command(BaseModel):
    """
    Represents a CLI command.
    """
    name: str = Field(..., description="Command name")
    description: Optional[str] = Field(None, description="Command description")
    usage: Optional[str] = Field(None, description="Command usage example")
    parameters: List[CommandParameter] = Field(default_factory=list, description="Command parameters")
    subcommands: Dict[str, "Command"] = Field(default_factory=dict, description="Command subcommands")


class CliTool(BaseModel):
    """
    Represents a CLI tool.
    """
    name: str = Field(..., description="Tool name")
    description: Optional[str] = Field(None, description="Tool description")
    version: Optional[str] = Field(None, description="Tool version")
    commands: Dict[str, Command] = Field(default_factory=dict, description="Commands provided by the tool")
    global_parameters: List[CommandParameter] = Field(default_factory=list, description="Global parameters")
    help_text: Optional[str] = Field(None, description="Help text for the tool")
    bin_path: Optional[str] = Field(None, description="Path to the tool binary")
    install_command: Optional[str] = Field(None, description="Command to install the tool")
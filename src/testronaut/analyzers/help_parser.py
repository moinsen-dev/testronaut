"""
Help Text Parser Utility.

This module provides a class responsible for parsing CLI help text to extract
commands, options, arguments, and examples using regular expressions.
"""

import re
from typing import Any, Dict, List, Optional

# Import necessary models if methods need them (adjust as needed)
# from testronaut.models import Command, Example, Option, Argument
from testronaut.utils.logging import get_logger

logger = get_logger(__name__)

class HelpTextParser:
    """Parses CLI help text to extract structural elements."""

    def extract_commands(self, tool_name: str, help_text: str) -> List[Dict[str, Any]]:
        """
        Extract commands from the help text of a CLI tool.

        Args:
            tool_name: The name of the CLI tool (used for logging).
            help_text: The help text of the tool.

        Returns:
            A list of dictionaries with command information.
        """
        logger.debug(f"Extracting commands for tool: {tool_name}")
        commands = []
        existing_cmd_names = set()  # Track command names to avoid duplicates

        # Look for the "Commands" section in the help text
        # This pattern works for rich-formatted CLI help (like Typer with rich formatting)
        commands_section_match = re.search(
            r"Commands[^\n]*\n(.*?)(?:\n\n|\Z)", help_text, re.DOTALL
        )

        if commands_section_match:
            commands_section = commands_section_match.group(1)
            # Process each line in the commands section
            for line in commands_section.split("\n"):
                # Skip separator lines and empty lines
                if not line.strip() or re.match(
                    r"^[\s\u2500\u256d\u256e\u2570\u256f\u2502]+$", line
                ):
                    continue

                # Extract command name and description
                # This works for "command    description" format
                parts = re.split(r"\s{2,}", line.strip(), maxsplit=1)
                if len(parts) >= 1:
                    # Clean up command name (remove UI characters)
                    cmd_name = parts[0].strip()
                    cmd_name = re.sub(
                        r"[\u2500\u256d\u256e\u2570\u256f\u2502]", "", cmd_name
                    ).strip()

                    # Clean up description
                    cmd_desc = parts[1].strip() if len(parts) > 1 else None
                    if cmd_desc:
                        cmd_desc = re.sub(
                            r"[\u2500\u256d\u256e\u2570\u256f\u2502]", "", cmd_desc
                        ).strip()

                    # Check for duplicates (case-insensitive)
                    if cmd_name and cmd_name.lower() not in existing_cmd_names:
                        commands.append({"name": cmd_name, "description": cmd_desc})
                        existing_cmd_names.add(cmd_name.lower())

        # If no commands were found with the above pattern, try simpler patterns
        if not commands:
            # Common patterns for commands in help text
            command_patterns = [
                # Pattern for "Commands:" section with indented commands
                r"(?:Commands|Available commands):\s*\n((?:\s+\w+\s+.*\n)+)",
                # Pattern for "Subcommands:" section
                r"(?:Subcommands):\s*\n((?:\s+\w+.*\n)+)",
                # Pattern for command lists with descriptions
                r"^\s+(\w+)\s+(.*?)$",
            ]

            for pattern in command_patterns:
                matches = re.findall(pattern, help_text, re.MULTILINE)
                if matches:
                    if isinstance(matches[0], tuple):
                        # If matches are tuples, we have command and description
                        for match in matches:
                            cmd_name = match[0].strip()
                            cmd_desc = match[1].strip() if len(match) > 1 else None

                            # Check for duplicates (case-insensitive)
                            if cmd_name and cmd_name.lower() not in existing_cmd_names:
                                commands.append({"name": cmd_name, "description": cmd_desc})
                                existing_cmd_names.add(cmd_name.lower())
                    else:
                        # Otherwise, we have a block of text with commands
                        for block in matches:
                            for line in block.split("\n"):
                                if line.strip():
                                    parts = line.strip().split(maxsplit=1)
                                    cmd_name = parts[0].strip()
                                    cmd_desc = parts[1].strip() if len(parts) > 1 else None

                                    # Check for duplicates (case-insensitive)
                                    if cmd_name and cmd_name.lower() not in existing_cmd_names:
                                        commands.append({"name": cmd_name, "description": cmd_desc})
                                        existing_cmd_names.add(cmd_name.lower())

        logger.debug(f"Extracted {len(commands)} commands from help text")
        return commands

    def extract_options(self, help_text: str) -> List[Dict[str, Any]]:
        """
        Extract options from the help text.

        Args:
            help_text: The help text to parse.

        Returns:
            A list of dictionaries with option information.
        """
        logger.debug("Extracting options from help text")
        options = []
        processed_options = set() # Track options to avoid duplicates

        # Common patterns for options in help text
        option_patterns = [
            # Pattern for "-o, --option DESCRIPTION" format (optional value placeholder)
            r"^\s+(-\w),?\s+(--[\w-]+)(?:\s+[<\[][\w\s.-]+[>\]])?\s+(.*?)(?:\s+\[(.*)\])?$",
            # Pattern for "--option DESCRIPTION" format (optional value placeholder)
            r"^\s+(--[\w-]+)(?:\s+[<\[][\w\s.-]+[>\]])?\s+(.*?)(?:\s+\[(.*)\])?$",
            # Pattern for "-o DESCRIPTION" format (optional value placeholder)
            r"^\s+(-\w)(?:\s+[<\[][\w\s.-]+[>\]])?\s+(.*?)(?:\s+\[(.*)\])?$",
        ]

        for pattern in option_patterns:
            matches = re.findall(pattern, help_text, re.MULTILINE)
            for match in matches:
                option_info = {}
                if len(match) == 4 and match[0].startswith("-") and match[1].startswith("--"): # -o, --option DESC [env]
                    option_info = {"short_form": match[0], "long_form": match[1], "description": match[2].strip(), "env_var": match[3]}
                elif len(match) == 3:
                    if match[0].startswith("--"): # --option DESC [env]
                        option_info = {"short_form": None, "long_form": match[0], "description": match[1].strip(), "env_var": match[2]}
                    elif match[0].startswith("-"): # -o DESC [env]
                        option_info = {"short_form": match[0], "long_form": None, "description": match[1].strip(), "env_var": match[2]}

                if option_info:
                    # Use long_form primarily for name and uniqueness check
                    name = (option_info.get("long_form") or option_info.get("short_form", "")).lstrip("-")
                    if name and name not in processed_options:
                        option_info["name"] = name
                        # Basic check for required (often indicated in description)
                        option_info["required"] = "[required]" in option_info.get("description", "").lower()
                        options.append(option_info)
                        processed_options.add(name)

        logger.debug(f"Extracted {len(options)} options from help text")
        return options

    def extract_arguments(self, help_text: str) -> List[Dict[str, Any]]:
        """
        Extract arguments from the help text.

        Args:
            help_text: The help text to parse.

        Returns:
            A list of dictionaries with argument information.
        """
        logger.debug("Extracting arguments from help text")
        arguments = []
        processed_args = set() # Track arguments to avoid duplicates

        # Look for "Arguments:" section first
        args_section_match = re.search(
            r"Arguments:[^\n]*\n(.*?)(?:\n\n|\Z)", help_text, re.DOTALL
        )
        section_text = help_text # Default to full text if section not found
        if args_section_match:
            section_text = args_section_match.group(1)
            logger.debug("Found 'Arguments:' section.")

        # Pattern for "ARG_NAME    Description [possible attributes]"
        # ARG_NAME can be uppercase, <enclosed>, or [optional]
        arg_pattern = r"^\s+([\w_<>\[\]-]+)\s+(.*?)(?:\s+\[(.*)\])?$"

        position = 0
        for line in section_text.split('\n'):
            match = re.match(arg_pattern, line)
            if match:
                name_raw = match.group(1).strip()
                description = match.group(2).strip()
                attributes = match.group(3)

                # Skip if it looks like an option
                if name_raw.startswith("-"):
                    continue

                # Determine if required based on brackets
                required = not (name_raw.startswith("[") and name_raw.endswith("]"))

                # Clean up the name
                name = name_raw.strip("<>[]").upper() # Often uppercase by convention

                if name and name not in processed_args:
                    arg_info = {
                        "name": name,
                        "description": description,
                        "required": required,
                        "position": position,
                        "attributes": attributes # Store raw attributes for potential later parsing
                    }
                    # Check attributes for 'required' keyword
                    if attributes and "required" in attributes.lower():
                        arg_info["required"] = True

                    arguments.append(arg_info)
                    processed_args.add(name)
                    position += 1

        logger.debug(f"Extracted {len(arguments)} arguments from help text")
        return arguments

    def extract_examples(self, tool_name: str, help_text: str) -> List[Dict[str, Any]]:
        """
        Extract usage examples from help text.

        Args:
            tool_name: The name of the CLI tool (used to identify example lines).
            help_text: The help text to parse.

        Returns:
            A list of dictionaries containing example information.
        """
        logger.debug(f"Extracting examples for tool: {tool_name}")
        examples = []
        example_lines = []

        # Look for "Examples:" section
        examples_section_match = re.search(
            r"(?:Examples|EXAMPLES):[^\n]*\n((?:.|\n)*?)(?:\n\n[A-Z][a-z]+:|\Z)", help_text, re.IGNORECASE
        )

        if examples_section_match:
            logger.debug("Found 'Examples:' section.")
            section_text = examples_section_match.group(1)
            # Split into potential examples (often separated by blank lines or indentation changes)
            potential_examples = re.split(r'\n\s*\n', section_text.strip())
            for block in potential_examples:
                lines = block.strip().split('\n')
                command_line = ""
                description_parts = []
                for line in lines:
                    stripped_line = line.strip()
                    # Check if the line looks like a command execution
                    if stripped_line.startswith(f"{tool_name} ") or stripped_line.startswith("$ ") or stripped_line.startswith("# "):
                        # If we already have a command line, this might be a new example
                        if command_line and description_parts:
                             if command_line.startswith(tool_name): # Only add valid examples
                                 examples.append({
                                     "command_line": command_line,
                                     "description": " ".join(description_parts).strip() or None
                                 })
                             command_line = ""
                             description_parts = []

                        # Clean up the command line
                        command_line = re.sub(r"^\s*[$#]\s*", "", stripped_line)

                    elif command_line: # If we have a command line, assume this is part of the description
                        description_parts.append(stripped_line)
                    # else: ignore lines before the first command line in a block

                # Add the last example found in the block
                if command_line and command_line.startswith(tool_name):
                    examples.append({
                        "command_line": command_line,
                        "description": " ".join(description_parts).strip() or None
                    })

        # Fallback: Look for lines starting with the tool name outside an examples section
        if not examples:
            logger.debug("No 'Examples:' section found or parsed, trying fallback pattern.")
            # Simple pattern: find lines starting with the tool name, possibly indented
            fallback_pattern = rf"^\s+{re.escape(tool_name)}\s+.*$"
            matches = re.findall(fallback_pattern, help_text, re.MULTILINE)
            for line in matches:
                 examples.append({"command_line": line.strip(), "description": None})


        logger.debug(f"Extracted {len(examples)} examples from help text")
        return examples

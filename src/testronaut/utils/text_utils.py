"""
Utility functions for text processing in Testronaut.

This module provides functions for cleaning, formatting, and processing
text data, particularly focused on CLI help text.
"""

import re
from typing import Optional


def clean_help_text(help_text: Optional[str]) -> Optional[str]:
    """
    Clean CLI help text by removing excess whitespace and decorative elements.

    Args:
        help_text: The original help text from a CLI tool

    Returns:
        Cleaned and formatted help text suitable for machine processing
    """
    if not help_text:
        return help_text

    # Replace box drawing characters with markdown equivalents
    box_chars_map = {
        # Box drawing characters
        "┌": "",
        "┐": "",
        "└": "",
        "┘": "",
        "─": "",
        "│": "",
        "╔": "",
        "╗": "",
        "╚": "",
        "╝": "",
        "═": "",
        "║": "",
        "├": "",
        "┤": "",
        "┬": "",
        "┴": "",
        "┼": "",
        "╠": "",
        "╣": "",
        "╦": "",
        "╩": "",
        "╬": "",
        # Box drawing light variants
        "╭": "",
        "╮": "",
        "╯": "",
        "╰": "",
        # Other special characters
        "•": "*",
        "·": "*",
        "↵": "",
        "⏎": "",
        "…": "...",
        "✓": "[x]",
        "✔": "[x]",
        "✗": "[ ]",
        "✘": "[ ]",
        "✕": "[ ]",
        "→": "->",
        "←": "<-",
        "↑": "^",
        "↓": "v",
    }

    # Create a regex pattern for all box characters
    pattern = "|".join(re.escape(char) for char in box_chars_map.keys())

    # Replace box characters
    for char, replacement in box_chars_map.items():
        help_text = help_text.replace(char, replacement)

    # Process the text line by line
    lines = help_text.split("\n")
    cleaned_lines = []
    in_command_section = False
    in_option_section = False

    for line in lines:
        # Strip trailing whitespace
        line = line.rstrip()

        # Skip empty lines or lines with only decorative characters
        if not line or line.strip() in ["", "-", "=", "*"] or re.match(r"^[-=*]+$", line.strip()):
            continue

        # Detect sections
        if re.search(r"commands", line.lower()):
            in_command_section = True
            cleaned_lines.append("\n**Commands:**")
            continue

        if re.search(r"options", line.lower()):
            in_option_section = True
            cleaned_lines.append("\n**Options:**")
            continue

        # Remove lines that are just decorative separators
        if re.match(r"^[─═╌┄═━\s-]+$", line):
            continue

        # Clean up excessive whitespace
        line = re.sub(r"\s{2,}", " ", line)
        line = line.strip()

        # Skip if line became empty after cleaning
        if not line:
            continue

        # Format command and option lines
        if in_command_section and line and not line.startswith("**"):
            # Extract command name and description if they exist
            cmd_match = re.match(r"([a-zA-Z0-9_-]+)\s+(.*)", line)
            if cmd_match:
                cmd, desc = cmd_match.groups()
                line = f"* `{cmd}` - {desc}"
            else:
                line = f"* `{line}`"

        if in_option_section and line and not line.startswith("**"):
            # Extract option name and description if they exist
            opt_match = re.match(r"(--?[a-zA-Z0-9_-]+)\s+(.*)", line)
            if opt_match:
                opt, desc = opt_match.groups()
                line = f"* `{opt}` - {desc}"
            else:
                # If we just have an option without description
                if line.startswith("--") or line.startswith("-"):
                    line = f"* `{line}`"

        cleaned_lines.append(line)

    # Combine lines
    cleaned_text = "\n".join(cleaned_lines)

    # Replace multiple newlines with double newline
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)

    # Fix "Usage:" sections to use code blocks
    cleaned_text = re.sub(
        r"(Usage|USAGE):(.*?)(\n\n|\n\*\*|$)",
        r"**Usage:**\n```\n\1\2\n```\n",
        cleaned_text,
        flags=re.DOTALL,
    )

    return cleaned_text

"""
LLM Result Processor.

This module provides utilities for processing and validating LLM analysis results.
"""

import json
import re
from typing import Any, Dict, List, Optional

from testronaut.utils.errors import ValidationError
from testronaut.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


class LLMResultProcessor:
    """Processor for handling and validating LLM responses for CLI analysis."""

    @staticmethod
    def extract_json_from_text(text: str) -> Dict[str, Any]:
        """
        Extract JSON from text that might contain markdown or other formatting.

        Args:
            text: The text containing JSON.

        Returns:
            The extracted JSON as a dictionary.

        Raises:
            ValidationError: If no valid JSON can be found.
        """
        # Try to find JSON in code blocks first
        json_block_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        matches = re.findall(json_block_pattern, text)

        if matches:
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue

        # No valid JSON in code blocks, try to find JSON anywhere in the text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find anything that looks like a JSON object
            json_pattern = r"(\{[\s\S]*\})"
            matches = re.findall(json_pattern, text)

            if matches:
                for match in matches:
                    try:
                        return json.loads(match)
                    except json.JSONDecodeError:
                        continue

            raise ValidationError(
                "Could not extract valid JSON from LLM response",
                details={"response_text": text[:500] + "..." if len(text) > 500 else text},
            )

    @staticmethod
    def validate_command_analysis(
        analysis: Dict[str, Any], expected_keys: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate command analysis results.

        Args:
            analysis: The analysis results to validate.
            expected_keys: Optional list of keys that should be present.

        Returns:
            The validated analysis.

        Raises:
            ValidationError: If the analysis is invalid.
        """
        if not expected_keys:
            expected_keys = ["primary_function", "common_use_cases", "key_options", "risk_level"]

        # Check for required keys
        missing_keys = [key for key in expected_keys if key not in analysis]
        if missing_keys:
            raise ValidationError(
                "Command analysis missing required keys", details={"missing_keys": missing_keys}
            )

        return analysis

    @staticmethod
    def process_command_purpose(text: str) -> str:
        """
        Process command purpose description from LLM response.

        Args:
            text: The LLM response text.

        Returns:
            The processed command purpose description.
        """
        # Clean up response by removing common explanatory prefixes
        prefixes_to_remove = [
            "Command purpose:",
            "Description:",
            "The command",
            "This command",
            "Here's a description:",
        ]

        result = text.strip()
        for prefix in prefixes_to_remove:
            if result.startswith(prefix):
                result = result[len(prefix) :].strip()

        # Limit to 500 characters
        if len(result) > 500:
            result = result[:497] + "..."

        return result

    @staticmethod
    def process_examples(text: str) -> List[Dict[str, str]]:
        """
        Process command examples from LLM response.

        Args:
            text: The LLM response text.

        Returns:
            List of example dictionaries.

        Raises:
            ValidationError: If examples can't be processed.
        """
        examples = []

        # Try to extract structured examples first
        try:
            json_data = LLMResultProcessor.extract_json_from_text(text)
            if isinstance(json_data, list):
                return json_data
            elif "examples" in json_data and isinstance(json_data["examples"], list):
                return json_data["examples"]
        except ValidationError:
            pass

        # Fall back to regex-based extraction
        example_pattern = (
            r"(?:Example|Example \d+):?\s+(.*?\s+.*?)(?:\n|$)(?:Description:?\s+(.*?))?(?:\n\n|\Z)"
        )
        matches = re.findall(example_pattern, text, re.MULTILINE | re.DOTALL)

        if matches:
            for command_line, description in matches:
                examples.append(
                    {
                        "command_line": command_line.strip(),
                        "description": description.strip() if description else None,
                    }
                )

            return examples

        # Try another pattern for numbered examples
        numbered_pattern = r"(\d+\.)\s+(.*?\s+.*?)(?:\n|$)(?:\s+-\s+(.*?))?(?:\n\n|\Z)"
        matches = re.findall(numbered_pattern, text, re.MULTILINE | re.DOTALL)

        if matches:
            for _, command_line, description in matches:
                examples.append(
                    {
                        "command_line": command_line.strip(),
                        "description": description.strip() if description else None,
                    }
                )

            return examples

        # If all else fails and there are legitimate command lines, try to extract them
        command_lines = re.findall(r"`([^`]+)`", text)
        if command_lines:
            for cmd in command_lines:
                examples.append({"command_line": cmd.strip(), "description": None})

            return examples

        raise ValidationError(
            "Could not extract examples from LLM response",
            details={"response_text": text[:500] + "..." if len(text) > 500 else text},
        )

    @staticmethod
    def process_relationships(text: str) -> Dict[str, Any]:
        """
        Process command relationships from LLM response.

        Args:
            text: The LLM response text.

        Returns:
            Dictionary with relationship information.
        """
        result = {"parent_child": [], "workflows": [], "dependencies": []}

        # Try to extract JSON first
        try:
            json_data = LLMResultProcessor.extract_json_from_text(text)
            # If the extraction worked and has the right structure, use it
            if (
                "parent_child" in json_data
                or "workflows" in json_data
                or "dependencies" in json_data
            ):
                for key in result:
                    if key in json_data and isinstance(json_data[key], list):
                        result[key] = json_data[key]
                return result
        except ValidationError:
            pass

        # Extract parent-child relationships
        parent_child_section = re.search(
            r"(?:Parent-child|Subcommand).*?:(.*?)(?:2\.|Workflows|Common workflows|$)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if parent_child_section:
            # Extract relationships like "command -> subcommand" or "parent: child1, child2"
            relationships = re.findall(
                r"([a-z0-9_-]+)(?:\s*->|:\s*)([a-z0-9_, -]+)",
                parent_child_section.group(1),
                re.IGNORECASE,
            )
            for parent, children in relationships:
                for child in re.split(r",\s*", children):
                    if child.strip():
                        result["parent_child"].append(
                            {"parent": parent.strip(), "child": child.strip()}
                        )

        # Extract workflows
        workflows_section = re.search(
            r"(?:2\.|Workflows|Common workflows).*?:(.*?)(?:3\.|Dependencies|$)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if workflows_section:
            # Extract workflows like "workflow: command1 -> command2 -> command3"
            workflows = re.findall(
                r"(?:- |• )?(?:\d+\.\s+)?([^:]+)(?::|workflow:)(.*?)(?:\n\n|\n(?:- |• |\d+\.)|\Z)",
                workflows_section.group(1),
                re.MULTILINE,
            )
            for name, steps in workflows:
                if steps.strip():
                    result["workflows"].append(
                        {
                            "name": name.strip(),
                            "steps": [s.strip() for s in re.split(r"->|,|;", steps) if s.strip()],
                        }
                    )

        # Extract dependencies
        dependencies_section = re.search(
            r"(?:3\.|Dependencies).*?:(.*?)(?:\Z)", text, re.DOTALL | re.IGNORECASE
        )
        if dependencies_section:
            # Extract dependencies like "command1 depends on command2"
            dependencies = re.findall(
                r"(?:- |• )?(?:\d+\.\s+)?([a-z0-9_-]+).*?(?:depends on|requires|prerequisite).*?([a-z0-9_-]+)",
                dependencies_section.group(1),
                re.IGNORECASE,
            )
            for command, dependency in dependencies:
                result["dependencies"].append(
                    {"command": command.strip(), "depends_on": dependency.strip()}
                )

        return result

    @staticmethod
    def process_semantic_analysis(text: str) -> Dict[str, Any]:
        """
        Process semantic analysis from LLM response.

        Args:
            text: The LLM response text.

        Returns:
            Dictionary with semantic analysis information.
        """
        result = {
            "primary_function": "",
            "common_use_cases": [],
            "key_options": [],
            "risk_level": "unknown",
            "alternatives": [],
            "common_patterns": [],
        }

        # Try to extract JSON first
        try:
            json_data = LLMResultProcessor.extract_json_from_text(text)
            # If the extraction worked and has the right structure, use it
            for key in result:
                if key in json_data:
                    result[key] = json_data[key]
            return result
        except ValidationError:
            pass

        # Extract sections using regex
        sections = {
            "primary_function": r"(?:1\.|Primary Function|Main Purpose).*?:(.+?)(?=(?:\n\n|\n\d\.|\Z))",
            "common_use_cases": r"(?:2\.|Common Use Cases|Usage Scenarios).*?:(.+?)(?=(?:\n\n|\n\d\.|\Z))",
            "key_options": r"(?:3\.|Key Options|Important Options).*?:(.+?)(?=(?:\n\n|\n\d\.|\Z))",
            "risk_level": r"(?:4\.|Risk Level|Safety).*?:(.+?)(?=(?:\n\n|\n\d\.|\Z))",
            "alternatives": r"(?:5\.|Alternatives).*?:(.+?)(?=(?:\n\n|\n\d\.|\Z))",
            "common_patterns": r"(?:6\.|Common Patterns|Usage Patterns|Workflows).*?:(.+?)(?=(?:\n\n|\n\d\.|\Z))",
        }

        for key, pattern in sections.items():
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()

                # Process the content according to the expected type
                if key in ["common_use_cases", "key_options", "alternatives", "common_patterns"]:
                    # Extract list items
                    items = re.findall(
                        r"(?:- |• |\* |[\d]+\. )(.*?)(?:\n(?:- |• |\* |[\d]+\. )|\Z)",
                        content,
                        re.DOTALL,
                    )
                    result[key] = [item.strip() for item in items if item.strip()]

                    # If no list items found, split by newlines and clean up
                    if not result[key]:
                        result[key] = [item.strip() for item in content.split("\n") if item.strip()]
                else:
                    result[key] = content

        # Special processing for risk level
        if isinstance(result["risk_level"], str):
            risk_text = result["risk_level"].lower()
            if "low" in risk_text or "safe" in risk_text:
                result["risk_level"] = "low"
            elif "medium" in risk_text or "moderate" in risk_text:
                result["risk_level"] = "medium"
            elif "high" in risk_text or "dangerous" in risk_text or "destructive" in risk_text:
                result["risk_level"] = "high"

        return result

    @staticmethod
    def process_tool_purpose_analysis(text: str) -> Dict[str, Any]:
        """
        Process tool purpose analysis from LLM response.

        Args:
            text: The LLM response text.

        Returns:
            Dictionary with tool purpose analysis information.
        """
        # Try to extract structured data first
        try:
            return LLMResultProcessor.extract_json_from_text(text)
        except ValidationError:
            pass

        # Fall back to regex-based extraction
        result = {"purpose": "", "background": "", "use_cases": [], "testing_considerations": []}

        # Extract purpose
        purpose_match = re.search(
            r"(?:Purpose|1\.)[^\n]*?\n\s*(.*?)(?:\n\s*\n|\n\s*[2-9]\.)", text, re.DOTALL
        )
        if purpose_match:
            result["purpose"] = purpose_match.group(1).strip()

        # Extract background
        background_match = re.search(
            r"(?:Background|2\.)[^\n]*?\n\s*(.*?)(?:\n\s*\n|\n\s*[3-9]\.)", text, re.DOTALL
        )
        if background_match:
            result["background"] = background_match.group(1).strip()

        # Extract use cases
        use_cases_text = ""
        use_cases_match = re.search(
            r"(?:Use Cases|3\.)[^\n]*?\n\s*(.*?)(?:\n\s*\n|\n\s*[4-9]\.)", text, re.DOTALL
        )
        if use_cases_match:
            use_cases_text = use_cases_match.group(1).strip()
            # Extract individual use cases
            use_cases = re.findall(r"[-*]\s*(.*?)(?:\n|$)", use_cases_text)
            if use_cases:
                result["use_cases"] = [uc.strip() for uc in use_cases]
            else:
                # If no bullet points, treat as single paragraph
                result["use_cases"] = [use_cases_text]

        # Extract testing considerations
        testing_text = ""
        testing_match = re.search(
            r"(?:Testing Considerations|4\.)[^\n]*?\n\s*(.*?)(?:\n\s*\n|\Z)", text, re.DOTALL
        )
        if testing_match:
            testing_text = testing_match.group(1).strip()
            # Extract individual considerations
            considerations = re.findall(r"[-*]\s*(.*?)(?:\n|$)", testing_text)
            if considerations:
                result["testing_considerations"] = [c.strip() for c in considerations]
            else:
                # If no bullet points, treat as single paragraph
                result["testing_considerations"] = [testing_text]

        return result

    @staticmethod
    def extract_purpose(text: str) -> str:
        """
        Extract command purpose from LLM response text.

        Args:
            text: The LLM response text.

        Returns:
            The extracted purpose as a string.
        """
        # Try to extract structured data first
        try:
            json_data = LLMResultProcessor.extract_json_from_text(text)
            if "purpose" in json_data:
                return json_data["purpose"]
        except ValidationError:
            pass

        # Extract purpose section
        purpose_match = re.search(
            r"(?:Purpose|1\.)[^\n]*?\n\s*(.*?)(?:\n\s*\n|\n\s*[2-9]\.)", text, re.DOTALL
        )
        if purpose_match:
            return purpose_match.group(1).strip()

        # If no clear purpose section, use the first paragraph
        paragraphs = text.split("\n\n")
        if paragraphs:
            first_para = paragraphs[0].strip()
            # Remove common prefixes
            prefixes = ["Purpose:", "The purpose is", "This command's purpose is"]
            for prefix in prefixes:
                if first_para.startswith(prefix):
                    first_para = first_para[len(prefix) :].strip()
            return first_para

        return ""

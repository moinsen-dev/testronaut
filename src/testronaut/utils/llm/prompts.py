"""
CLI Analysis Prompts.

This module contains prompt templates for analyzing CLI tools and commands using LLMs.
"""

from typing import Dict, List, Optional


class CLIAnalysisPrompts:
    """Collection of prompts for CLI tool and command analysis."""

    @staticmethod
    def command_purpose_analysis(
        command_name: str,
        help_text: str,
        description: Optional[str] = None,
    ) -> str:
        """
        Generate a prompt for analyzing the purpose of a command.

        Args:
            command_name: The name of the command.
            help_text: The help text of the command.
            description: Optional existing description of the command.

        Returns:
            A prompt string for the LLM.
        """
        context = f"Existing description: {description}" if description else ""
        return f"""
        Based on the following help text for the command '{command_name}', provide a clear,
        concise description of what this command does. Focus on the main purpose and key
        functionality. Keep the description under 100 words and write in a direct, technical style.

        {context}

        Help text:
        ```
        {help_text[:3000]}  # Limiting to 3000 chars to avoid token limits
        ```
        """

    @staticmethod
    def command_examples_extraction(
        tool_name: str,
        command_name: str,
        help_text: str,
        num_examples: int = 3,
    ) -> str:
        """
        Generate a prompt for extracting or generating command usage examples.

        Args:
            tool_name: The name of the CLI tool.
            command_name: The name of the command.
            help_text: The help text of the command.
            num_examples: The desired number of examples.

        Returns:
            A prompt string for the LLM.
        """
        return f"""
        Based on the following help text for the command '{tool_name} {command_name}',
        extract or generate {num_examples} useful example command usages. If there are explicit
        examples in the help text, extract those. If not, generate realistic examples based on
        the available options and arguments.

        Each example should:
        1. Start with the full command including '{tool_name} {command_name}'
        2. Demonstrate a realistic use case
        3. Include a brief description of what the example does

        Help text:
        ```
        {help_text[:3000]}  # Limiting to 3000 chars to avoid token limits
        ```
        """

    @staticmethod
    def command_relationships_analysis(
        tool_name: str,
        commands: List[Dict[str, str]],
    ) -> str:
        """
        Generate a prompt for analyzing relationships between commands.

        Args:
            tool_name: The name of the CLI tool.
            commands: List of dictionaries containing command names and descriptions.

        Returns:
            A prompt string for the LLM.
        """
        commands_str = "\n".join(
            [f"- {cmd['name']}: {cmd.get('description', 'No description')}" for cmd in commands]
        )

        return f"""
        Analyze the following list of commands for the CLI tool '{tool_name}' and identify:

        1. Parent-child relationships between commands (which commands might be subcommands of others)
        2. Common workflows or sequences of commands that are typically used together
        3. Any command dependencies (commands that require other commands to be run first)

        Commands:
        {commands_str}

        For each identified relationship, explain why you think these commands are related and
        how they might be used together in a workflow.
        """

    @staticmethod
    def command_semantic_analysis(
        tool_name: str,
        command_name: str,
        help_text: str,
    ) -> str:
        """
        Generate a prompt for semantic analysis of a command.

        Args:
            tool_name: The name of the CLI tool.
            command_name: The name of the command.
            help_text: The help text of the command.

        Returns:
            A prompt string for the LLM.
        """
        return f"""
        Perform a detailed semantic analysis of the command '{tool_name} {command_name}'
        based on its help text. Your analysis should include:

        1. Primary function: What is the main purpose of this command?
        2. Common use cases: In what scenarios would this command typically be used?
        3. Key options: Which options are most important and why?
        4. Risk level: Is this command potentially destructive or safe to use without caution?
        5. Alternatives: Are there alternative commands that could achieve similar results?
        6. Common patterns: How is this command typically used in workflows?

        Help text:
        ```
        {help_text[:3000]}  # Limiting to 3000 chars to avoid token limits
        ```

        Provide your analysis in a structured format with sections for each of the above aspects.
        """

    @staticmethod
    def option_purpose_analysis(
        command_name: str,
        option_name: str,
        help_text: str,
    ) -> str:
        """
        Generate a prompt for analyzing the purpose of a command option.

        Args:
            command_name: The name of the command.
            option_name: The name of the option.
            help_text: The help text containing information about the option.

        Returns:
            A prompt string for the LLM.
        """
        return f"""
        Based on the following help text for the command '{command_name}', provide a clear,
        concise description of what the option '{option_name}' does. Explain its purpose,
        what values it accepts, and any default values or behaviors. Keep your response
        focused only on this specific option.

        Help text:
        ```
        {help_text[:3000]}  # Limiting to 3000 chars to avoid token limits
        ```
        """

    @staticmethod
    def error_cases_analysis(
        tool_name: str,
        command_name: str,
        help_text: str,
    ) -> str:
        """
        Generate a prompt for analyzing potential error cases for a command.

        Args:
            tool_name: The name of the CLI tool.
            command_name: The name of the command.
            help_text: The help text of the command.

        Returns:
            A prompt string for the LLM.
        """
        return f"""
        Based on the help text for the command '{tool_name} {command_name}', identify potential
        error cases or failure modes that could occur when using this command. For each error case,
        explain:

        1. What scenario would trigger this error
        2. What the error message might look like
        3. How to fix or avoid the error

        Focus on the most common or important error cases rather than trying to be exhaustive.

        Help text:
        ```
        {help_text[:3000]}  # Limiting to 3000 chars to avoid token limits
        ```
        """

    @staticmethod
    def command_structure_inference(
        tool_name: str,
        command_name: str,
        tool_help_text: str,
        error_context: Optional[str] = None,
    ) -> str:
        """
        Generate a prompt for inferring command structure when conventional parsing fails.

        Args:
            tool_name: The name of the CLI tool.
            command_name: The name of the command.
            tool_help_text: The help text of the overall tool.
            error_context: Optional error message from conventional parsing.

        Returns:
            A prompt string for the LLM.
        """
        error_info = (
            f"\nThe conventional help command failed with this error: {error_context}"
            if error_context
            else ""
        )

        return f"""
        I need to understand the structure and usage of the '{tool_name} {command_name}' command.{error_info}

        Based on your knowledge of CLI tools and the following information about the '{tool_name}' tool,
        please analyze and provide a structured description of the '{command_name}' command.

        Your response should include:

        1. COMMAND PURPOSE: A concise description of what this command does
        2. SYNTAX: The proper syntax for using this command
        3. OPTIONS: List of options/flags this command likely supports
        4. ARGUMENTS: List of arguments this command likely accepts
        5. EXAMPLES: 2-3 realistic examples of how to use this command
        6. SUBCOMMANDS: If applicable, likely subcommands of this command

        Context about the tool:
        ```
        {tool_help_text[:2000]}  # Limiting to 2000 chars to avoid token limits
        ```

        Format your response in a structured way that clearly identifies each section.
        If you're uncertain about any details, provide reasonable guesses based on common patterns
        in similar CLI tools, but indicate these as inferred rather than definitive.
        """

"""
DetailPanel Widget for the Testronaut DB Browser.
"""
from typing import Dict, Optional

from textual.widgets import Static

# Assuming logger is accessible or imported appropriately
# import logging
# ui_logger = logging.getLogger("testronaut.ui.widget.detail_panel")

class DetailPanel(Static):
    """Panel for displaying detailed information."""

    def __init__(self) -> None:
        """Initialize the detail panel."""
        super().__init__("Select a tool or command to view details")
        self.current_command: Optional[Dict] = None

    def show_command(self, command: Dict) -> None:
        """Show command details."""
        self.current_command = command

        # Validate command data
        if not isinstance(command, dict):
            self.update(f"# Error\n\nInvalid command data: {command}")
            return

        if "name" not in command:
            self.update("# Error\n\nCommand data is missing name field")
            return

        # Build markdown content for the command
        content = f"# Command: {command['name']}\n\n"

        if command.get("description"):
            content += f"**Description:** {command['description']}\n\n"

        if command.get("syntax"):
            content += f"**Syntax:** `{command['syntax']}`\n\n"

        # Add options section
        options = command.get("options", [])
        if options:
            content += "## Options\n\n"
            for opt in options:
                # Ensure opt is a dictionary before accessing keys
                if isinstance(opt, dict):
                    opt_name = opt.get("name", "Unknown Option")
                    short_form = opt.get("short_form")
                    long_form = opt.get("long_form")

                    display_name = opt_name # Default display
                    if short_form and long_form:
                         display_name = f"{short_form}, {long_form}"
                    elif long_form:
                         display_name = long_form
                    elif short_form:
                         display_name = short_form

                    content += f"* **{display_name}**"
                    if opt.get("description"):
                        content += f": {opt['description']}"
                    if opt.get("required"):
                        content += " *(required)*"
                    # Default value display removed as it wasn't in the Option model originally
                    # if opt.get("default_value"):
                    #     content += f" *[default: {opt['default_value']}]*"
                    content += "\n"
                else:
                     # Log or display an error for invalid option format
                     content += f"* **Error:** Invalid option data format: {opt}\n"
            content += "\n"

        # Add arguments section
        arguments = command.get("arguments", [])
        if arguments:
            content += "## Arguments\n\n"
            # Sort arguments by position if available, otherwise just list them
            try:
                 sorted_args = sorted(arguments, key=lambda a: a.get("position", 0) if isinstance(a, dict) else 0)
            except TypeError:
                 sorted_args = arguments # Fallback if sorting fails

            for arg in sorted_args:
                 if isinstance(arg, dict):
                     content += f"* **{arg.get('name', 'Unknown Argument')}**"
                     if arg.get("description"):
                         content += f": {arg['description']}"
                     if arg.get("required"):
                         content += " *(required)*"
                     # Default value display removed as it wasn't in the Argument model originally
                     # if arg.get("default_value"):
                     #     content += f" *[default: {arg['default_value']}]*"
                     content += "\n"
                 else:
                      content += f"* **Error:** Invalid argument data format: {arg}\n"
            content += "\n"

        # Add examples section
        examples = command.get("examples", [])
        if examples:
            content += "## Examples\n\n"
            for ex in examples:
                 if isinstance(ex, dict):
                     if ex.get("description"):
                         content += f"**{ex['description']}**\n\n"
                     if ex.get("command_line"):
                         content += f"```bash\n{ex['command_line']}\n```\n\n"
                     # Expected output display removed as it wasn't in the Example model originally
                     # if ex.get("expected_output"):
                     #     content += "Expected output:\n\n"
                     #     content += f"```\n{ex['expected_output']}\n```\n\n"
                 else:
                      content += f"**Error:** Invalid example data format: {ex}\n\n"

        # Add help text if available
        if command.get("help_text"):
            content += "## Help Text\n\n"
            content += f"```\n{command['help_text']}\n```\n"

        self.update(content)

    def show_tool_detail(self, tool: Dict) -> None:
        """Formats and displays tool details."""
        content = f"# Tool: {tool.get('name', 'Unknown Tool')}\n\n"

        if tool.get("version"):
            content += f"**Version:** {tool['version']}\n\n"

        if tool.get("description"):
            content += f"**Description:** {tool['description']}\n\n"

        if tool.get("install_command"):
            content += f"**Install Command:** `{tool['install_command']}`\n\n"

        # Display purpose, background, use cases etc. if available in metadata
        meta = tool.get('meta_data', {})
        if isinstance(meta, dict):
             if meta.get("purpose"):
                  content += f"**Purpose:** {meta['purpose']}\n\n"
             if meta.get("background"):
                  content += f"**Background:** {meta['background']}\n\n"
             if meta.get("use_cases"):
                  content += "**Use Cases:**\n"
                  for case in meta['use_cases']:
                       content += f"- {case}\n"
                  content += "\n"
             if meta.get("testing_considerations"):
                  content += "**Testing Considerations:**\n"
                  for consid in meta['testing_considerations']:
                       content += f"- {consid}\n"
                  content += "\n"

        # Display LLM Usage if available
        llm_usage_data = meta.get('llm_usage')
        if isinstance(llm_usage_data, dict):
             content += "## LLM Usage (Analysis)\n\n"
             content += f"- **API Calls:** {llm_usage_data.get('api_calls', 0)}\n"
             content += f"- **Total Tokens:** {llm_usage_data.get('total_tokens', 0)}\n"
             content += f"- **Prompt Tokens:** {llm_usage_data.get('prompt_tokens', 0)}\n"
             content += f"- **Completion Tokens:** {llm_usage_data.get('completion_tokens', 0)}\n"
             content += f"- **Estimated Cost:** ${llm_usage_data.get('estimated_cost', 0.0):.4f}\n"
             models_used = llm_usage_data.get('models_used', {})
             if models_used:
                  content += "- **Models Used:**\n"
                  for model, count in models_used.items():
                       content += f"  - {model}: {count} tokens\n"
             content += "\n"


        # Display Relationship Analysis if available
        rel_analysis_data = meta.get('relationship_analysis')
        if isinstance(rel_analysis_data, dict):
             content += "## Relationship Analysis\n\n"
             if rel_analysis_data.get('parent_child'):
                  content += "**Parent/Child:**\n"
                  for rel in rel_analysis_data['parent_child']:
                       content += f"- {rel.get('parent')} -> {rel.get('child')}\n"
                  content += "\n"
             if rel_analysis_data.get('workflows'):
                  content += "**Workflows:**\n"
                  for wf in rel_analysis_data['workflows']:
                       steps = " -> ".join(wf.get('steps', []))
                       content += f"- {wf.get('name', 'Unnamed')}: {steps}\n"
                  content += "\n"
             if rel_analysis_data.get('dependencies'):
                  content += "**Dependencies:**\n"
                  for dep in rel_analysis_data['dependencies']:
                       content += f"- {dep.get('command')} depends on {dep.get('depends_on')}\n"
                  content += "\n"


        cmd_count = len(tool.get("commands", []))
        content += f"**Commands Found:** {cmd_count}\n\n"

        content += "Select a command from the tree to see its details."
        self.update(content)

    def clear_panel(self, message: str = "Select a tool or command to view details") -> None:
         """Clears the panel and shows a default message."""
         self.update(message)

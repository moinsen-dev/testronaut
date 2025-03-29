"""
Configuration management commands for Testronaut.
"""

import os # Keep os if needed by remaining code
# Removed shutil as it wasn't used by remaining code
from pathlib import Path
from typing import Optional # Keep Optional if needed by remaining code
# Removed List, Dict, Any as they were only used by LLM code
# Removed yaml as it wasn't used by remaining code
# Removed questionary as it wasn't used by remaining code
# Removed Confirm as it wasn't used by remaining code
# Removed huggingface_hub imports as they were only used by LLM code

import typer
from rich import box
from rich.table import Table

from testronaut.cli.common import console, logger
from testronaut.config import (
    Settings,
    RegisteredModel,
    get_config_path,
    initialize_config,
    load_config_file,
    save_config_file,
    RegisteredModel, # Keep if needed by remaining code (e.g., show)
    get_config_path,
    initialize_config,
    load_config_file,
    # Removed save_config_file as it was only used by LLM code
    # Removed 'settings as global_settings'
)
# Removed llm.utils import
# Removed utils.errors import (ConfigurationError, LLMServiceError)
# Removed factory import
# Removed interfaces import

# Import the LLM subcommand app from the new file
from .config_llm import llm_app

# Create main config app
config_app = typer.Typer(help="Configuration management commands")

# --- Existing Commands (init, show) ---

@config_app.command("init")
def config_init(
    config_dir: Optional[str] = typer.Option(
        None, "--config-dir", "-c", help="Configuration directory path"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force overwrite existing configuration"
    ),
) -> int:
    """Initialize Testronaut configuration."""
    try:
        config_path = Path(config_dir) if config_dir else get_config_path()
        result = initialize_config(config_path, force=force)
        console.print(f"Configuration initialized at: [bold green]{result}[/bold green]")
        console.print(f"Default config file: [bold]{result / 'config.yaml'}[/bold]")
        return 0
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        logger.exception("Failed to initialize configuration")
        return 1


@config_app.command("show")
def config_show() -> int:
    """Show current configuration."""
    try:
        # Reload settings from file to show current state
        settings = Settings() # Load defaults
        config_file = get_config_path() / 'config.yaml'
        if config_file.exists():
             try:
                  config_dict = load_config_file(config_file)
                  # Manually update settings object for display purposes
                  # This is a simplified update, might need refinement for deep nesting
                  settings = Settings(**config_dict)
             except Exception as load_err:
                  console.print(f"[yellow]Warning: Could not load config file {config_file}: {load_err}[/yellow]")

        table = Table(title="Testronaut Configuration", box=box.ROUNDED)
        table.add_column("Setting", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")

        # General
        table.add_row("Config Path", str(settings.config_path))
        table.add_row("Debug Mode", str(settings.debug))

        # Logging
        table.add_row("Log Level", settings.logging.level)
        table.add_row("Log Format", settings.logging.format)
        table.add_row("Log File", settings.logging.output_file or "Console")

        # Database
        table.add_row("Database URL", settings.database.url) # Show potentially unresolved URL

        # Execution
        table.add_row("Use Docker", str(settings.execution.use_docker))
        table.add_row("Default Docker Image", settings.execution.docker_image)
        table.add_row("Default Timeout", f"{settings.execution.timeout}s")

        # LLM - Main
        table.add_row("LLM Provider", settings.llm.provider)

        # LLM - Provider Specific
        provider_config = settings.llm.provider_settings.get(settings.llm.provider, {})
        if settings.llm.provider == "llama-cpp":
             table.add_row("LLM Model Path", str(provider_config.get("model_path", "Not Set")))
             table.add_row("LLM Context Size (n_ctx)", str(provider_config.get("n_ctx", "Default")))
             table.add_row("LLM GPU Layers", str(provider_config.get("n_gpu_layers", "Default")))
             # List registered models briefly
             registered = provider_config.get("registered_models", [])
             table.add_row("LLM Registered Models", f"{len(registered)} model(s) - use 'config llm list'")
        elif settings.llm.provider in ["openai", "anthropic"]:
             api_key_status = "Configured" if provider_config.get("api_key") else "Not Configured (uses env var?)"
             table.add_row("LLM API Key", api_key_status)
             models = provider_config.get("models", {})
             table.add_row("LLM Default Model", models.get("default", settings.llm.model))
             # Add other relevant cloud settings if needed
        else:
             table.add_row(f"{settings.llm.provider} Settings", str(provider_config))


        console.print(table)
        return 0
    except Exception as e:
        console.print(f"[bold red]Error showing configuration:[/bold red] {str(e)}")
        logger.exception(f"Error showing configuration: {str(e)}")
        return 1


# Add the llm app (imported from config_llm.py) to the main config app
config_app.add_typer(llm_app, name="llm")

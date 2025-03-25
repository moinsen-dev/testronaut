"""
Configuration management commands for Testronaut.
"""

from typing import Optional

import typer
from rich import box
from rich.table import Table

from testronaut.cli.common import console, logger
from testronaut.config import Settings, get_config_path, initialize_config
from testronaut.utils.llm import LLMService

# Create config app
config_app = typer.Typer(help="Configuration management commands")


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
        result = initialize_config(config_dir, force=force)
        console.print(f"Configuration initialized at: [bold green]{result}[/bold green]")

        # Display config path information
        config_path = get_config_path()
        console.print(f"Config path set to: [bold]{config_path}[/bold]")

        return 0
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        logger.exception("Failed to initialize configuration")
        return 1


@config_app.command("show")
def config_show() -> int:
    """Show current configuration."""
    try:
        settings = Settings()

        # Create a rich table
        table = Table(title="Testronaut Configuration", box=box.ROUNDED)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        # Add general settings
        table.add_row("App Name", settings.app_name)
        table.add_row("Debug Mode", str(settings.debug))
        table.add_row("Config Path", str(settings.config_path))

        # Add database settings
        table.add_row("Database URL", settings.database.url)

        # Add logging settings
        table.add_row("Log Level", settings.logging.level)
        table.add_row("Log Format", settings.logging.format)

        # Add LLM settings
        table.add_row("LLM Provider", settings.llm.provider)

        # Get the current provider settings
        provider_settings = settings.llm.current_provider_settings
        models = provider_settings.get("models", {})

        # Add model information if available
        if "default" in models:
            table.add_row("LLM Default Model", models["default"])
        else:
            table.add_row("LLM Model", settings.llm.model)

        # Show API key status (but not the actual key)
        api_key_status = "Configured" if provider_settings.get("api_key") else "Not configured"
        table.add_row("LLM API Key", api_key_status)

        # Show task-specific models if configured
        for task, model in models.items():
            if task != "default":
                table.add_row(f"LLM {task.capitalize()} Model", model)

        # Add execution settings if they exist and have values
        if hasattr(settings, "execution"):
            execution = settings.execution
            if hasattr(execution, "docker_image"):
                table.add_row("Default Docker Image", execution.docker_image)
            if hasattr(execution, "timeout"):
                table.add_row("Default Timeout", f"{execution.timeout} seconds")

        # Print the table
        console.print(table)

        return 0
    except Exception as e:
        console.print(f"[bold red]Error showing configuration:[/bold red] {str(e)}")
        logger.exception(f"Error showing configuration: {str(e)}")
        return 1


@config_app.command("test-llm")
def test_llm() -> int:
    """Test the LLM service configuration."""
    try:
        # Create the LLM service
        service = LLMService()

        # Get provider information
        provider_name = service.provider_name
        model = service.settings.llm.get_model_for_task("chat")

        console.print(
            f"Testing LLM service with provider: [bold]{provider_name}[/bold], model: [bold]{model}[/bold]"
        )

        # Generate a simple response
        prompt = (
            "Generate a short test message to verify that the LLM service is working correctly."
        )

        with console.status("Generating response...", spinner="dots"):
            response = service.generate_text(prompt, max_tokens=100)

        # Display the response
        console.print(
            "\n[bold green]═══════════════════════ LLM Response ═══════════════════════[/bold green]"
        )
        console.print(response)
        console.print(f"[dim]Provider: {provider_name}, Model: {model}[/dim]")
        console.print(
            "[bold green]═══════════════════════════════════════════════════════════[/bold green]\n"
        )

        console.print("[bold green]LLM service test successful![/bold green]")
        return 0

    except Exception as e:
        console.print(f"[bold red]Error testing LLM service:[/bold red] {str(e)}")
        logger.exception(f"Error testing LLM service: {str(e)}")
        return 1

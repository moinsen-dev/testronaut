"""
Configuration management commands for Testronaut.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any

import typer
import yaml
import questionary # Import questionary
from rich import box
from rich.table import Table
from rich.prompt import Confirm
from huggingface_hub import list_repo_files, HfApi # Import Hub utilities

from testronaut.cli.common import console, logger
from testronaut.config import (
    Settings,
    RegisteredModel,
    get_config_path,
    initialize_config,
    load_config_file,
    save_config_file,
    # Removed 'settings as global_settings' - use get_settings() if singleton needed
)
from testronaut.llm.utils import download_gguf_model, get_models_dir
from testronaut.utils.errors import ConfigurationError, LLMServiceError
from testronaut.factory import registry # Import factory registry
from testronaut.interfaces import LLMManager # Correct import path for interface

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


# --- New LLM Subcommand Group ---

llm_app = typer.Typer(help="Manage local LLM models (GGUF format via llama-cpp)")

def _load_current_config() -> Dict[str, Any]:
    """Loads the current configuration from the default file."""
    config_file = get_config_path() / 'config.yaml'
    if not config_file.exists():
        console.print(f"[yellow]Warning: Config file {config_file} not found. Initializing default config.[/yellow]")
        initialize_config(config_file.parent) # Initialize in the directory
        # Fallback to default settings if init fails or file still not there
        if not config_file.exists():
             return Settings().model_dump()

    try:
        return load_config_file(config_file)
    except Exception as e:
        raise ConfigurationError(f"Failed to load config file {config_file}: {e}") from e

def _save_current_config(config_dict: Dict[str, Any]):
    """Saves the configuration dictionary to the default file."""
    config_file = get_config_path() / 'config.yaml'
    try:
        save_config_file(config_dict, config_file)
    except Exception as e:
        raise ConfigurationError(f"Failed to save config file {config_file}: {e}") from e

def _get_llama_cpp_settings(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Safely gets the llama-cpp settings dictionary, creating if necessary."""
    if "llm" not in config_dict:
        config_dict["llm"] = {}
    if "provider_settings" not in config_dict["llm"]:
        config_dict["llm"]["provider_settings"] = {}
    if "llama-cpp" not in config_dict["llm"]["provider_settings"]:
        # Initialize with defaults from the Pydantic model if possible
        # For simplicity here, just create the basic structure
        config_dict["llm"]["provider_settings"]["llama-cpp"] = {
            "model_path": None,
            "registered_models": [],
            "n_ctx": 4096,
            "n_gpu_layers": 0,
            "verbose": False,
        }
    # Ensure registered_models list exists
    if "registered_models" not in config_dict["llm"]["provider_settings"]["llama-cpp"]:
        config_dict["llm"]["provider_settings"]["llama-cpp"]["registered_models"] = []

    return config_dict["llm"]["provider_settings"]["llama-cpp"]


@llm_app.command("add")
def llm_add(
    identifier: str = typer.Argument(
        ..., help="Hugging Face repo ID (e.g., 'TheBloke/Mistral-7B-Instruct-v0.2-GGUF'), repo ID/filename, OR local file path."
    ),
    name: Optional[str] = typer.Option(
        None, "--name", "-n", help="Short name to register the model (defaults to filename stem)."
    ),
) -> int:
    """Add a local model (download from Hub or use local path)."""
    try:
        config_dict = _load_current_config()
        llama_settings = _get_llama_cpp_settings(config_dict)
        # Initialize as empty list, then update if value exists
        registered_models: List[Dict[str, Any]] = []
        registered_models_raw = llama_settings.get("registered_models")
        if registered_models_raw is not None:
            registered_models = registered_models_raw # Assume it's the correct type if not None


        repo_id: Optional[str] = None
        filename: Optional[str] = None
        source: str = identifier
        local_path: Path
        is_hub_id = "/" in identifier # Basic check: Assume it's a Hub ID if it contains a slash

        if is_hub_id:
            # Check if it's a full repo_id/filename.gguf identifier
            if identifier.lower().endswith(".gguf") and identifier.count("/") >= 1:
                 parts = identifier.split("/")
                 repo_id = "/".join(parts[:-1])
                 filename = parts[-1]
                 console.print(f"Identified Hub repo '{repo_id}' and filename '{filename}'.")
            else:
                 # Assume it's just a repo_id, try to find the GGUF file
                 repo_id = identifier
                 console.print(f"Identifier '{repo_id}' looks like a Hub repository. Searching for GGUF files...")
                 try:
                      api = HfApi()
                      all_files = api.list_repo_files(repo_id=repo_id)
                      gguf_files = sorted([f for f in all_files if f.lower().endswith(".gguf")])

                      if not gguf_files:
                           console.print(f"[bold red]Error:[/bold red] No .gguf files found in repository '{repo_id}'.")
                           return 1
                      elif len(gguf_files) == 1:
                           filename = gguf_files[0]
                           console.print(f"Found unique GGUF file: '{filename}'.")
                      else:
                           # Display files in a table and let user choose
                           console.print(f"Found multiple GGUF files in repository '{repo_id}'. Fetching details...")
                           model_table = Table(title=f"Available GGUF Files in {repo_id}", box=box.MINIMAL)
                           model_table.add_column("Index", style="dim", justify="right")
                           model_table.add_column("Filename", style="cyan")
                           model_table.add_column("Size (MB)", style="magenta", justify="right")

                           file_details = []
                           with console.status("Fetching file details...", spinner="dots"):
                               model_info = api.model_info(repo_id=repo_id)
                               for idx, gguf_file in enumerate(gguf_files):
                                   size_mb_str = "N/A"
                                   try:
                                       file_info = next((f for f in model_info.siblings if f.rfilename == gguf_file), None)
                                       if file_info and file_info.size:
                                           size_mb = file_info.size / (1024 * 1024)
                                           size_mb_str = f"{size_mb:.1f}"
                                   except Exception:
                                       pass # Ignore errors fetching size for individual files
                                   model_table.add_row(str(idx + 1), gguf_file, size_mb_str)
                                   file_details.append({"index": str(idx + 1), "name": gguf_file, "size": size_mb_str})

                           console.print(model_table)

                           # Use questionary with just the filenames for selection clarity
                           filename = questionary.select(
                               "Please choose the GGUF file to download:",
                               choices=gguf_files, # Select directly from the list of filenames
                           ).ask()

                           # Add check in case filename is somehow None (e.g., user cancelled)
                           if filename is None:
                                console.print("Model addition cancelled.")
                                return 1
                           console.print(f"Selected GGUF file: '{filename}'.")

                 except Exception as e:
                      console.print(f"[bold red]Error accessing Hub repository '{repo_id}':[/bold red] {e}")
                      return 1

            # Proceed with download if we determined repo_id and filename
            if repo_id and filename:
                 try:
                      console.print(f"Attempting to download '{filename}' from Hub repo '{repo_id}'...")
                      local_path = download_gguf_model(repo_id=repo_id, filename=filename)
                      source = f"{repo_id}/{filename}" # Store the full identifier as source
                 except Exception as e:
                      console.print(f"[bold red]Error downloading model:[/bold red] {e}")
                      return 1
            else:
                 # Should not happen if logic above is correct, but as a safeguard
                 console.print("[bold red]Error:[/bold red] Could not determine repository ID and filename.")
                 return 1
        else:
            # Treat as local path
            console.print(f"Identifier '{identifier}' does not contain '/'. Treating as local path.")
            local_path = Path(os.path.expanduser(identifier))
            if not local_path.is_file():
                console.print(f"[bold red]Error:[/bold red] Local path '{local_path}' is not a valid file.")
                return 1
            if not local_path.name.lower().endswith(".gguf"):
                 console.print(f"[bold red]Error:[/bold red] Local file '{local_path.name}' must have a .gguf extension.")
                 return 1
            filename = local_path.name
            source = f"local:{local_path.name}" # Indicate it's a local file source
            console.print(f"Using local model file: {local_path}")

        # Determine registration name
        reg_name = name if name else Path(filename).stem # Use filename stem if name not provided

        # Add assertion to help type checker confirm registered_models is a list
        assert isinstance(registered_models, list)

        # Check for conflicts (using .get() for robustness with dict keys)
        if any(m.get("name") == reg_name for m in registered_models):
            console.print(f"[bold red]Error:[/bold red] A model with the name '{reg_name}' is already registered.")
            return 1
        # Revert to any() and ignore persistent Pylance warning (likely false positive)
        if any(Path(m.get("path", "")) == local_path for m in registered_models): # type: ignore
            console.print(f"[bold red]Error:[/bold red] The model path '{local_path}' is already registered under a different name.")
            return 1

        # Add to registry
        new_model = RegisteredModel(name=reg_name, path=str(local_path.resolve()), source=source)
        registered_models.append(new_model.model_dump()) # Add as dict
        llama_settings["registered_models"] = registered_models # Update the list in the dict

        # --- Automatically set the newly added model as default ---
        console.print(f"Setting '{reg_name}' as the default llama-cpp model...")
        config_dict["llm"]["provider"] = "llama-cpp" # Switch provider
        llama_settings["model_path"] = new_model.path # Set the model path
        # --- End auto-set ---

        _save_current_config(config_dict)
        console.print(f"Model '{reg_name}' added successfully from '{source}'.")
        console.print(f"Path: {new_model.path}")
        console.print(f"[bold green]'{reg_name}' is now the active default model (provider: llama-cpp).[/bold green]")
        return 0

    except Exception as e:
        console.print(f"[bold red]Error adding model:[/bold red] {str(e)}")
        logger.exception("Error adding LLM model")
        return 1


@llm_app.command("list")
def llm_list() -> int:
    """List registered local models."""
    try:
        config_dict = _load_current_config()
        llama_settings = _get_llama_cpp_settings(config_dict)
        registered_models_data: List[Dict[str, Any]] = llama_settings.get("registered_models", [])
        current_path_str = llama_settings.get("model_path")
        current_path = Path(current_path_str) if current_path_str else None

        table = Table(title="Registered Local LLM Models (llama-cpp)", box=box.ROUNDED)
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Path", style="magenta")
        table.add_column("Source", style="blue", no_wrap=True)
        table.add_column("Default", style="green", justify="center")

        if not registered_models_data:
            console.print("No local models registered yet. Use 'testronaut config llm add'.")
            return 0

        # Parse models using Pydantic for validation/structure
        registered_models = [RegisteredModel(**data) for data in registered_models_data]

        for model in registered_models:
            is_default = current_path and Path(model.path).resolve() == current_path.resolve()
            table.add_row(
                model.name,
                model.path,
                model.source or "Unknown",
                "✅" if is_default else "",
            )

        console.print(table)
        return 0

    except Exception as e:
        console.print(f"[bold red]Error listing models:[/bold red] {str(e)}")
        logger.exception("Error listing LLM models")
        return 1


@llm_app.command("remove")
def llm_remove(
    name: str = typer.Argument(..., help="Name of the registered model to remove."),
    delete_file: bool = typer.Option(False, "--delete-file", help="Also delete the model file if it's in the Testronaut models directory.")
) -> int:
    """Remove a registered local model."""
    try:
        config_dict = _load_current_config()
        llama_settings = _get_llama_cpp_settings(config_dict)
        registered_models: List[Dict[str, Any]] = llama_settings.get("registered_models", [])
        current_path_str = llama_settings.get("model_path")

        initial_count = len(registered_models)
        model_to_remove: Optional[Dict[str, Any]] = None
        model_path_to_delete: Optional[Path] = None

        # Find the model
        for model_data in registered_models:
             if model_data.get("name") == name:
                  model_to_remove = model_data
                  break

        if model_to_remove is None:
            console.print(f"[bold red]Error:[/bold red] Model '{name}' not found.")
            return 1

        # Remove from list
        registered_models = [m for m in registered_models if m.get("name") != name]
        llama_settings["registered_models"] = registered_models

        # Check if it was the default and clear the path if so
        if current_path_str and Path(model_to_remove.get("path", "")).resolve() == Path(current_path_str).resolve():
            llama_settings["model_path"] = None
            console.print(f"[yellow]Note:[/yellow] Removed model '{name}' was the default. Default model path cleared.")

        # Handle file deletion
        model_path = Path(model_to_remove.get("path", ""))
        models_dir = get_models_dir()
        if delete_file:
            # Only delete if it's within the managed directory
            try:
                if model_path.is_relative_to(models_dir):
                     if Confirm.ask(f"Are you sure you want to delete the file '{model_path}'?"):
                          model_path.unlink(missing_ok=True)
                          console.print(f"Deleted model file: {model_path}")
                     else:
                          console.print("File deletion cancelled.")
                else:
                     console.print(f"[yellow]Warning:[/yellow] Cannot delete file '{model_path}' as it is outside the managed directory '{models_dir}'.")
            except Exception as e:
                 console.print(f"[bold red]Error deleting file {model_path}:[/bold red] {e}")
                 # Continue with config removal even if file deletion fails

        _save_current_config(config_dict)
        console.print(f"Model '{name}' removed successfully.")
        return 0

    except Exception as e:
        console.print(f"[bold red]Error removing model:[/bold red] {str(e)}")
        logger.exception("Error removing LLM model")
        return 1


@llm_app.command("set")
def llm_set(
    name: str = typer.Argument(..., help="Name of the registered model to set as default for llama-cpp.")
) -> int:
    """Set a registered local model as the default for llama-cpp provider."""
    try:
        config_dict = _load_current_config()
        llama_settings = _get_llama_cpp_settings(config_dict)
        registered_models: List[Dict[str, Any]] = llama_settings.get("registered_models", [])

        model_to_set: Optional[Dict[str, Any]] = None
        for model_data in registered_models:
             if model_data.get("name") == name:
                  model_to_set = model_data
                  break

        if model_to_set is None:
            console.print(f"[bold red]Error:[/bold red] Model '{name}' not found.")
            return 1

        model_path = model_to_set.get("path")
        if not model_path or not Path(model_path).exists():
             console.print(f"[bold red]Error:[/bold red] Model path '{model_path}' for '{name}' is invalid or file does not exist.")
             return 1

        # Update settings
        config_dict["llm"]["provider"] = "llama-cpp" # Switch provider to llama-cpp
        llama_settings["model_path"] = str(Path(model_path).resolve()) # Set the specific model path

        _save_current_config(config_dict)
        console.print(f"Default LLM provider set to 'llama-cpp'.")
        console.print(f"Active model set to '{name}' ({llama_settings['model_path']}).")
        return 0

    except Exception as e:
        console.print(f"[bold red]Error setting default model:[/bold red] {str(e)}")
        logger.exception("Error setting default LLM model")
        return 1


def _get_llm_manager() -> LLMManager:
    """Helper function to instantiate the LLM Manager based on current settings."""
    try:
        # Load current settings to pass to the factory/manager
        current_config = _load_current_config()
        llm_settings_dict = current_config.get("llm", {})

        # The factory creates the manager instance, which should handle its own initialization
        # based on the passed config (or defaults if keys are missing)
        llm_factory = registry.get_factory("llm_manager")
        if llm_factory is None:
            raise ConfigurationError("'llm_manager' factory not found in registry.")

        # Pass the llm section of the config to the manager's __init__
        # The manager's __init__ should then use these settings to initialize the provider
        manager = llm_factory.create(manager_type="default", **llm_settings_dict)
        return manager
    except Exception as e:
        # Catch errors during factory creation or manager initialization
        raise LLMServiceError(f"Failed to create or initialize LLM Manager: {e}") from e


@llm_app.command("test")
def llm_test() -> int:
    """Send a simple test message to the configured LLM."""
    try:
        console.print("Initializing LLM Manager for test...")
        manager = _get_llm_manager()

        # Check if a provider was successfully initialized
        if manager.provider is None:
             # The manager's __init__ likely printed a warning already
             console.print("[bold red]Error:[/bold red] LLM provider could not be initialized. Check configuration (`config show`) and logs.")
             # Try to provide more specific guidance based on config
             current_config = _load_current_config()
             llm_config = current_config.get("llm", {})
             provider = llm_config.get("provider")
             if provider == "llama-cpp":
                  model_path = llm_config.get("provider_settings", {}).get("llama-cpp", {}).get("model_path")
                  if not model_path:
                       console.print("Hint: For llama-cpp, ensure 'model_path' is set in config or use 'config llm set <model_name>'.")
                  elif not Path(model_path).exists():
                       console.print(f"Hint: Configured model path '{model_path}' does not exist.")
             elif provider in ["openai", "anthropic"]:
                  api_key = llm_config.get("provider_settings", {}).get(provider, {}).get("api_key")
                  if not api_key:
                       env_var = f"{provider.upper()}_API_KEY"
                       console.print(f"Hint: Ensure API key for '{provider}' is set in config or via the {env_var} environment variable.")

             return 1

        provider_name = manager.provider_name
        # Try to get model info (might vary depending on provider implementation)
        model_info = "N/A"
        if provider_name == "llama-cpp":
             model_info = Path(manager.provider.model_path).name # type: ignore # Accessing provider specific attr
        # Add checks for other providers if needed

        console.print(f"Testing LLM service with provider: [bold]{provider_name}[/bold], model: [bold]{model_info}[/bold]")
        prompt = "Briefly introduce yourself and say 'Test successful!'"

        with console.status("Generating response...", spinner="dots"):
            response = manager.generate_text(prompt, max_tokens=50, temperature=0.5)

        console.print("\n[bold green]--- LLM Test Response ---[/bold green]")
        console.print(response)
        console.print("[bold green]-------------------------[/bold green]\n")
        console.print("[bold green]LLM service test successful![/bold green]")
        return 0

    except LLMServiceError as e:
         console.print(f"[bold red]LLM Service Error:[/bold red] {e}")
         # Attempt to provide more context if possible
         if "provider has not been initialized" in str(e):
              console.print("Hint: Check your LLM configuration using 'testronaut config show'. Ensure the provider and necessary settings (API key or model path) are correct.")
         return 1
    except Exception as e:
        console.print(f"[bold red]Unexpected Error testing LLM service:[/bold red] {str(e)}")
        logger.exception("Unexpected Error testing LLM service")
        return 1


@llm_app.command("chat")
def llm_chat(
    max_tokens: int = typer.Option(512, "--max-tokens", "-t", help="Max tokens per response."),
    temperature: float = typer.Option(0.7, "--temp", help="Sampling temperature."),
) -> int:
    """Start an interactive chat session with the configured LLM."""
    try:
        console.print("Initializing LLM Manager for chat...")
        manager = _get_llm_manager()

        if manager.provider is None:
             console.print("[bold red]Error:[/bold red] LLM provider could not be initialized. Check configuration (`config show`) and logs.")
             return 1

        provider_name = manager.provider_name
        model_info = "N/A"
        if provider_name == "llama-cpp":
             model_info = Path(manager.provider.model_path).name # type: ignore

        console.print(f"\n[bold]Chatting with {provider_name} ({model_info}). Type '/quit' or '/exit' to end.[/bold]")

        while True:
            prompt = questionary.text("You:", qmark=">", default="").ask()

            if prompt is None or prompt.strip().lower() in ["/quit", "/exit"]:
                console.print("[yellow]Exiting chat.[/yellow]")
                break

            if not prompt.strip():
                continue

            with console.status("Model thinking...", spinner="dots"):
                try:
                    response = manager.generate_text(
                        prompt, max_tokens=max_tokens, temperature=temperature
                    )
                    console.print(f"[bold blue]Model:[/bold blue] {response}")
                except LLMServiceError as e:
                     console.print(f"[bold red]LLM Error:[/bold red] {e}")
                except Exception as e:
                     console.print(f"[bold red]Unexpected Error:[/bold red] {e}")
                     logger.exception("Unexpected error during chat generation")

        return 0

    except LLMServiceError as e:
         console.print(f"[bold red]LLM Service Error:[/bold red] {e}")
         return 1
    except Exception as e:
        console.print(f"[bold red]Unexpected Error starting chat:[/bold red] {str(e)}")
        logger.exception("Unexpected Error starting chat")
        return 1


# Add the llm app to the main config app
config_app.add_typer(llm_app, name="llm")

# Note: The original test_llm command is now removed.

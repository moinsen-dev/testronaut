"""
LLM Utilities.

This module provides helper functions for LLM-related tasks,
such as downloading models.
"""

import os
from pathlib import Path
from typing import Optional

from huggingface_hub import hf_hub_download
# Import the specific error from the correct submodule
from huggingface_hub.errors import HfHubHTTPError

# Import the function to access the settings singleton
from testronaut.config import get_settings
from testronaut.utils.errors import LLMServiceError


def get_models_dir() -> Path:
    """
    Get the directory where local models are stored.

    Defaults to ~/.testronaut/models

    Returns:
        Path object representing the models directory.
    """
    # Get the settings singleton instance
    settings = get_settings()
    # Use the main config directory from settings and add '/models'
    models_dir = settings.config_path / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir


def download_gguf_model(
    repo_id: str,
    filename: str,
    models_dir: Optional[Path] = None,
    revision: Optional[str] = None,
) -> Path:
    """
    Downloads a GGUF model file from Hugging Face Hub.

    Args:
        repo_id: The Hugging Face repository ID (e.g., "TheBloke/Mistral-7B-Instruct-v0.2-GGUF").
        filename: The specific GGUF filename within the repository (e.g., "mistral-7b-instruct-v0.2.Q4_K_M.gguf").
        models_dir: The directory to save the model to. Defaults to ~/.testronaut/models/.
        revision: Optional specific revision (branch, tag, commit hash) of the model.

    Returns:
        The local path to the downloaded GGUF file.

    Raises:
        LLMServiceError: If the download fails.
    """
    if models_dir is None:
        models_dir = get_models_dir()

    local_model_path = models_dir / filename

    # Check if model already exists locally
    if local_model_path.exists():
        print(f"Model '{filename}' already exists locally at {local_model_path}. Skipping download.")
        return local_model_path

    print(f"Downloading model '{filename}' from repository '{repo_id}'...")
    try:
        downloaded_path_str = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=models_dir,
            local_dir_use_symlinks=False, # Avoid symlinks, store directly
            revision=revision,
            resume_download=True,
        )
        downloaded_path = Path(downloaded_path_str)

        # hf_hub_download might place it in a subdirectory structure, ensure it's where we expect
        if downloaded_path.name != filename:
             # This case might happen if local_dir structure changes in hf_hub
             # For now, assume it downloads directly or handle potential moves if needed
             print(f"Warning: Downloaded path name '{downloaded_path.name}' differs from expected filename '{filename}'.")


        # Ensure the final expected path exists after download
        if not local_model_path.exists():
             # If the file isn't at the expected flat path, try moving it if it's the only file downloaded
             if downloaded_path.is_file() and downloaded_path.parent != models_dir:
                  try:
                       downloaded_path.rename(local_model_path)
                       print(f"Moved downloaded file to {local_model_path}")
                  except OSError as e:
                       raise LLMServiceError(f"Failed to move downloaded model to expected location {local_model_path}: {e}") from e
             else:
                  raise LLMServiceError(f"Model file not found at expected location {local_model_path} after download attempt.")


        print(f"Model downloaded successfully to: {local_model_path}")
        return local_model_path

    except HfHubHTTPError as e:
        raise LLMServiceError(
            f"Failed to download model '{filename}' from '{repo_id}'. "
            f"Check repository ID and filename. Status: {e.response.status_code}. Error: {e}"
        ) from e
    except Exception as e:
        # Catch other potential errors (network, disk space, etc.)
        raise LLMServiceError(
            f"An unexpected error occurred during model download: {e}"
        ) from e

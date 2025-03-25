#!/usr/bin/env python3
"""
Script to download and convert the microsoft_Phi-4-mini-instruct-Q4_K_M.gguf model to GGUF format.

This script will:
1. Download the model from Hugging Face
2. Convert it to GGUF format using llama.cpp
3. Save it to the configured models directory
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import torch
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer

from testronaut.config import Settings
from testronaut.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


def download_model(model_id: str, output_dir: Path) -> Path:
    """
    Download the model from Hugging Face.

    Args:
        model_id: The Hugging Face model ID
        output_dir: Directory to save the model

    Returns:
        Path to the downloaded model
    """
    logger.info(f"Downloading model {model_id}")

    try:
        # Download model and tokenizer
        model_path = snapshot_download(
            repo_id=model_id, local_dir=output_dir / "original", ignore_patterns=["*.md", "*.txt"]
        )

        logger.info(f"Model downloaded to {model_path}")
        return Path(model_path)

    except Exception as e:
        logger.error(f"Failed to download model: {e}")
        raise


def convert_to_gguf(model_path: Path, output_dir: Path) -> Path:
    """
    Convert the model to GGUF format.

    Args:
        model_path: Path to the downloaded model
        output_dir: Directory to save the converted model

    Returns:
        Path to the converted model
    """
    logger.info("Converting model to GGUF format")

    try:
        # Load model and tokenizer
        model = AutoModelForCausalLM.from_pretrained(
            model_path, torch_dtype=torch.float16, device_map="auto"
        )
        tokenizer = AutoTokenizer.from_pretrained(model_path)

        # Save model in safetensors format first
        safetensors_path = output_dir / "safetensors"
        model.save_pretrained(safetensors_path, safe_serialization=True)
        tokenizer.save_pretrained(safetensors_path)

        # Convert to GGUF using llama.cpp
        gguf_path = output_dir / "microsoft_Phi-4-mini-instruct-Q4_K_M.gguf.gguf"
        subprocess.run(
            [
                "python3",
                "-m",
                "llama_cpp.convert_hf_to_gguf",
                "--outfile",
                str(gguf_path),
                "--model-dir",
                str(safetensors_path),
                "--outtype",
                "f16",
            ],
            check=True,
        )

        logger.info(f"Model converted and saved to {gguf_path}")
        return gguf_path

    except Exception as e:
        logger.error(f"Failed to convert model: {e}")
        raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download and convert microsoft_Phi-4-mini-instruct-Q4_K_M.gguf model"
    )
    parser.add_argument(
        "--model-id",
        default="microsoft/microsoft_Phi-4-mini-instruct-Q4_K_M.gguf",
        help="Hugging Face model ID",
    )
    parser.add_argument(
        "--output-dir", type=Path, help="Output directory (default: ~/.testronaut/models)"
    )
    args = parser.parse_args()

    try:
        # Load settings
        settings = Settings()

        # Get output directory
        output_dir = args.output_dir or Path(
            os.path.expanduser(settings.llm.provider_settings["llama"]["model_path"])
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        # Download and convert
        model_path = download_model(args.model_id, output_dir)
        gguf_path = convert_to_gguf(model_path, output_dir)

        logger.info("Model successfully downloaded and converted!")
        logger.info(f"Model path: {gguf_path}")

        # Update config if needed
        if settings.llm.provider != "llama":
            logger.info(
                "To use this model, update your config to use the 'llama' provider "
                "and set the model path in the provider settings."
            )

    except Exception as e:
        logger.error(f"Failed to process model: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

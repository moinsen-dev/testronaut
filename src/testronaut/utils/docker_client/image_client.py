"""
Docker Image Client.

Provides methods for managing Docker images (e.g., pulling).
"""
from typing import Optional

from testronaut.utils.command import CommandRunner
from testronaut.utils.errors import DockerError
from testronaut.utils.logging import get_logger

logger = get_logger(__name__)

class ImageClient:
    """Client for Docker image operations."""

    def __init__(self, command_runner: Optional[CommandRunner] = None):
        """
        Initialize the Docker image client.

        Args:
            command_runner: Command runner for executing Docker commands.
        """
        self.command_runner = command_runner or CommandRunner()
        # Consider adding a check here if docker is available using SystemClient?
        # Or assume it's checked higher up. For now, assume checked elsewhere.

    def pull_image(self, image: str, quiet: bool = False) -> None:
        """
        Pull a Docker image.

        Args:
            image: The Docker image to pull.
            quiet: Whether to suppress output.

        Raises:
            DockerError: If the image pull fails.
        """
        try:
            command = ["docker", "pull", image]
            if quiet:
                command.append("--quiet")

            logger.info(f"Pulling Docker image: {image}")
            result = self.command_runner.run(
                command,
                check=True # Ensure command execution errors are raised
            )

            logger.info(f"Docker image pulled successfully: {image}")

        except Exception as e:
            # Catch CommandExecutionError specifically if needed, or general Exception
            logger.error(f"Failed to pull Docker image '{image}': {e}", exc_info=True)
            raise DockerError(
                f"Failed to pull Docker image: {image}",
                details={"error": str(e)}
            ) from e

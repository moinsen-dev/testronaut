"""
Docker Volume Client.

Provides methods for managing Docker volumes.
"""
import uuid
from typing import Optional

from testronaut.utils.command import CommandRunner
from testronaut.utils.errors import DockerError
from testronaut.utils.logging import get_logger

logger = get_logger(__name__)

class VolumeClient:
    """Client for Docker volume operations."""

    def __init__(self, command_runner: Optional[CommandRunner] = None):
        """
        Initialize the Docker volume client.

        Args:
            command_runner: Command runner for executing Docker commands.
        """
        self.command_runner = command_runner or CommandRunner()
        # Assume docker availability is checked elsewhere

    def create_volume(self, name: Optional[str] = None) -> str:
        """
        Create a Docker volume.

        Args:
            name: The name of the volume. If None, a unique name is generated.

        Returns:
            The name of the created volume.

        Raises:
            DockerError: If the volume creation fails.
        """
        try:
            # Generate a volume name if not provided
            volume_name = name if name else f"testronaut-volume-{uuid.uuid4().hex[:8]}"

            # Prepare volume create command
            command = ["docker", "volume", "create", volume_name]

            logger.debug(f"Creating Docker volume: {volume_name}")
            result = self.command_runner.run(
                command,
                check=True
            )

            # Docker volume create returns the name of the volume
            created_volume_name = result.output.strip()

            logger.debug(f"Docker volume created: {created_volume_name}")
            # Ensure the returned name matches the requested/generated name
            if created_volume_name != volume_name:
                 logger.warning(f"Created volume name '{created_volume_name}' differs from requested name '{volume_name}'. Using created name.")
            return created_volume_name

        except Exception as e:
            logger.error(f"Failed to create Docker volume '{volume_name}': {e}", exc_info=True)
            raise DockerError(
                f"Failed to create Docker volume: {volume_name}",
                details={"error": str(e)}
            ) from e

    def remove_volume(self, volume_name: str, force: bool = False) -> None:
        """
        Remove a Docker volume.

        Args:
            volume_name: The name of the volume to remove.
            force: Whether to force removal of the volume.

        Raises:
            DockerError: If the volume removal fails.
        """
        try:
            command = ["docker", "volume", "rm"]
            if force:
                command.append("--force")
            command.append(volume_name)

            logger.debug(f"Removing Docker volume: {volume_name}")
            result = self.command_runner.run(
                command,
                check=True
            )

            logger.debug(f"Docker volume removed: {volume_name}")

        except Exception as e:
            logger.error(f"Failed to remove Docker volume '{volume_name}': {e}", exc_info=True)
            raise DockerError(
                f"Failed to remove Docker volume: {volume_name}",
                details={"error": str(e)}
            ) from e

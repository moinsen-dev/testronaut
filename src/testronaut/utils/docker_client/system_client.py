"""
Docker System Client.

Provides methods for checking Docker availability and status.
"""
import json
from typing import Any, Dict, Optional

from testronaut.utils.command import CommandRunner
# Import CommandExecutionError as well
from testronaut.utils.errors import DockerError, CommandExecutionError
from testronaut.utils.logging import get_logger

logger = get_logger(__name__)

class SystemClient:
    """Client for Docker system-level operations."""

    def __init__(self, command_runner: Optional[CommandRunner] = None):
        """
        Initialize the Docker system client.

        Args:
            command_runner: Command runner for executing Docker commands.
        """
        self.command_runner = command_runner or CommandRunner()

    def is_docker_available(self) -> bool:
        """
        Check if Docker is available on the system.

        Returns:
            True if Docker is available, False otherwise.
        """
        available = self.command_runner.is_command_available("docker")
        if not available:
            logger.warning("Docker command not found in PATH.")
        return available

    def check_docker_status(self) -> Dict[str, Any]:
        """
        Check the status of the Docker daemon.

        Returns:
            A dictionary with information about the Docker daemon.

        Raises:
            DockerError: If Docker is not available or the status check fails.
        """
        if not self.is_docker_available():
            raise DockerError(
                "Docker is not available on the system",
                details={"solution": "Install Docker and ensure it's in the PATH"}
            )

        try:
            # Run docker info command
            result = self.command_runner.run(
                ["docker", "info", "--format", "{{json .}}"],
                check=True
            )

            # Parse JSON output
            info = json.loads(result.output)

            # Check if Docker daemon is running (ServerVersion is a good indicator)
            if not info.get("ServerVersion"):
                logger.error("Docker daemon does not appear to be running (missing ServerVersion in 'docker info').")
                raise DockerError(
                    "Docker daemon is not running",
                    details={"output": result.output}
                )

            logger.info("Docker daemon is running.")
            return info

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse 'docker info' output: {e}")
            raise DockerError(
                "Failed to parse Docker info output",
                details={"error": str(e), "output": result.output if 'result' in locals() else None}
            ) from e
        except CommandExecutionError as e:
             logger.error(f"Command 'docker info' failed: {e}")
             raise DockerError(
                 "Failed to execute 'docker info'",
                 details={"error": str(e)}
             ) from e
        except Exception as e:
            logger.error(f"Unexpected error checking Docker status: {e}", exc_info=True)
            raise DockerError(
                "Failed to check Docker status",
                details={"error": str(e)}
            ) from e

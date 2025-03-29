"""
Docker Network Client.

Provides methods for managing Docker networks.
"""
import uuid
from typing import Optional

from testronaut.utils.command import CommandRunner
from testronaut.utils.errors import DockerError
from testronaut.utils.logging import get_logger

logger = get_logger(__name__)

class NetworkClient:
    """Client for Docker network operations."""

    def __init__(self, command_runner: Optional[CommandRunner] = None):
        """
        Initialize the Docker network client.

        Args:
            command_runner: Command runner for executing Docker commands.
        """
        self.command_runner = command_runner or CommandRunner()
        # Assume docker availability is checked elsewhere

    def create_network(
        self,
        name: Optional[str] = None,
        driver: str = "bridge",
        subnet: Optional[str] = None,
        gateway: Optional[str] = None
    ) -> str:
        """
        Create a Docker network.

        Args:
            name: The name of the network. If None, a unique name is generated.
            driver: The network driver.
            subnet: The subnet for the network.
            gateway: The gateway for the network.

        Returns:
            The ID or name of the created network (Docker returns the name if provided, ID otherwise).

        Raises:
            DockerError: If the network creation fails.
        """
        try:
            # Generate a network name if not provided
            network_name = name if name else f"testronaut-network-{uuid.uuid4().hex[:8]}"

            # Prepare network create command
            command = ["docker", "network", "create", "--driver", driver]

            # Add subnet and gateway if provided
            if subnet:
                command.extend(["--subnet", subnet])
            if gateway:
                command.extend(["--gateway", gateway])

            # Add network name
            command.append(network_name)

            logger.debug(f"Creating Docker network: {network_name}")
            result = self.command_runner.run(
                command,
                check=True
            )

            # Docker returns the name if provided, otherwise the ID.
            # We'll return whatever Docker gives back.
            created_network_identifier = result.output.strip()

            logger.debug(f"Docker network created: {created_network_identifier}")
            return created_network_identifier

        except Exception as e:
            logger.error(f"Failed to create Docker network '{network_name}': {e}", exc_info=True)
            raise DockerError(
                f"Failed to create Docker network: {network_name}",
                details={"error": str(e)}
            ) from e

    def remove_network(self, network_id_or_name: str) -> None:
        """
        Remove a Docker network.

        Args:
            network_id_or_name: The ID or name of the network to remove.

        Raises:
            DockerError: If the network removal fails.
        """
        try:
            command = ["docker", "network", "rm", network_id_or_name]

            logger.debug(f"Removing Docker network: {network_id_or_name}")
            result = self.command_runner.run(
                command,
                check=True
            )

            logger.debug(f"Docker network removed: {network_id_or_name}")

        except Exception as e:
            logger.error(f"Failed to remove Docker network '{network_id_or_name}': {e}", exc_info=True)
            raise DockerError(
                f"Failed to remove Docker network: {network_id_or_name}",
                details={"error": str(e)}
            ) from e

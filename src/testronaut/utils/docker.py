"""
Docker Integration Utilities.

This module provides utilities for managing Docker containers for test isolation.
"""
# Keep necessary imports for DockerTestEnvironment
import json
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from testronaut.utils.command import CommandRunner
from testronaut.utils.errors import DockerError
from testronaut.utils.logging import get_logger

# Import the new specific client classes
from .docker_client import (
    SystemClient,
    ImageClient,
    ContainerClient,
    NetworkClient,
    VolumeClient,
)

# Initialize logger
logger = get_logger(__name__)


class DockerClient:
    """
    Facade for interacting with Docker resources.

    Instantiates and provides access to specific clients for managing
    containers, images, networks, volumes, and system status.
    """

    def __init__(self, command_runner: Optional[CommandRunner] = None):
        """
        Initialize the Docker client facade.

        Args:
            command_runner: Command runner for executing Docker commands.
                            If None, a default one will be created.
        """
        runner = command_runner or CommandRunner()
        self.system = SystemClient(runner)
        self.images = ImageClient(runner)
        self.containers = ContainerClient(runner)
        self.networks = NetworkClient(runner)
        self.volumes = VolumeClient(runner)

        # Perform initial check
        if not self.system.is_docker_available():
            # Logged within is_docker_available
            pass
        else:
            # Optionally check daemon status on init, but might slow down startup
            # try:
            #     self.system.check_docker_status()
            # except DockerError as e:
            #     logger.warning(f"Docker available but daemon check failed: {e}")
            pass

    # --- Convenience Methods (delegating to specific clients) ---

    def is_docker_available(self) -> bool:
        """Check if Docker command is available."""
        return self.system.is_docker_available()

    def check_docker_status(self) -> Dict[str, Any]:
        """Check Docker daemon status."""
        return self.system.check_docker_status()

    def pull_image(self, image: str, quiet: bool = False) -> None:
        """Pull a Docker image."""
        self.images.pull_image(image, quiet)

    def run_container(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Run a Docker container."""
        # Handle the 'pull' argument which now belongs to ImageClient
        pull = kwargs.pop('pull', False)
        image = kwargs.get('image')
        if pull and image:
            self.pull_image(image, quiet=True) # Pull quietly before running
        return self.containers.run_container(*args, **kwargs)

    def stop_container(self, container_id: str, timeout: Optional[int] = None) -> None:
        """Stop a Docker container."""
        self.containers.stop_container(container_id, timeout)

    def remove_container(self, container_id: str, force: bool = False) -> None:
        """Remove a Docker container."""
        self.containers.remove_container(container_id, force)

    def create_network(self, *args: Any, **kwargs: Any) -> str:
        """Create a Docker network."""
        return self.networks.create_network(*args, **kwargs)

    def remove_network(self, network_id: str) -> None:
        """Remove a Docker network."""
        self.networks.remove_network(network_id)

    def create_volume(self, *args: Any, **kwargs: Any) -> str:
        """Create a Docker volume."""
        return self.volumes.create_volume(*args, **kwargs)

    def remove_volume(self, volume_name: str, force: bool = False) -> None:
        """Remove a Docker volume."""
        self.volumes.remove_volume(volume_name, force)

    def copy_to_container(self, *args: Any, **kwargs: Any) -> None:
        """Copy files/dirs to a container."""
        self.containers.copy_to_container(*args, **kwargs)

    def copy_from_container(self, *args: Any, **kwargs: Any) -> None:
        """Copy files/dirs from a container."""
        self.containers.copy_from_container(*args, **kwargs)


class DockerTestEnvironment:
    """Utility for managing Docker test environments."""

    def __init__(
        self,
        image: str,
        docker_client: Optional[DockerClient] = None,
        base_work_dir: Optional[Union[str, Path]] = None,
        network: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        pull_image: bool = True
    ):
        """
        Initialize the Docker test environment.

        Args:
            image: The Docker image to use.
            docker_client: Docker client for managing containers.
            base_work_dir: Base working directory on the host.
            network: Docker network to use.
            environment: Environment variables for containers.
            pull_image: Whether to pull the image before running containers.
        """
        self.image = image
        # Use the facade DockerClient
        self.docker_client = docker_client or DockerClient()
        self.base_work_dir = Path(base_work_dir) if base_work_dir else None
        self.network_name = network # Store provided network name
        self.environment = environment or {}
        self.pull_image = pull_image

        # Generated resources
        self._managed_network_id: Optional[str] = None # ID if we create it
        self._work_dir: Optional[Path] = None
        # Volumes are not explicitly managed by this class currently
        # self._volumes: Dict[str, str] = {}
        self._containers: Dict[str, str] = {} # Maps test name to container ID/Name

        # Check Docker availability via the facade
        if not self.docker_client.is_docker_available():
            # Error logged by client
            raise DockerError(
                "Docker is not available or not running.",
                details={"solution": "Install Docker and ensure it's in the PATH"}
            )

    def setup(self) -> Dict[str, Any]:
        """
        Set up the Docker test environment.

        Returns:
            A dictionary with information about the environment.

        Raises:
            DockerError: If the environment setup fails.
        """
        try:
            # Create a work directory if not provided
            if not self.base_work_dir:
                self._work_dir = Path(tempfile.mkdtemp(prefix="testronaut-"))
            else:
                self._work_dir = self.base_work_dir
                self._work_dir.mkdir(parents=True, exist_ok=True)

            # Create a network if not provided
            if self.network_name is None:
                # Use the specific network client via the facade
                self._managed_network_id = self.docker_client.create_network()
                self.network_name = self._managed_network_id # Use the created ID/Name
            else:
                # If a network name was provided, ensure it exists? (Optional check)
                pass

            # Pull the image if requested (using facade)
            if self.pull_image:
                self.docker_client.pull_image(self.image, quiet=True)

            # Return environment information
            # Return environment information
            return {
                "image": self.image,
                "work_dir": str(self._work_dir),
                "network": self.network_name, # Return the network name/ID being used
                "managed_network": self._managed_network_id is not None,
                "environment": self.environment
            }

        except Exception as e:
            # Clean up any resources that were created
            self.teardown()

            raise DockerError(
                "Failed to set up Docker test environment",
                details={"error": str(e)}
            ) from e

    def run_test(
        self,
        command: Union[str, List[str]],
        environment: Optional[Dict[str, str]] = None,
        name: Optional[str] = None,
        timeout: Optional[int] = None,
        work_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run a test in the Docker environment.

        Args:
            command: The command to run.
            environment: Additional environment variables.
            name: A name for the test container.
            timeout: Timeout for the test in seconds.
            work_dir: Working directory in the container.

        Returns:
            A dictionary with the test results.

        Raises:
            DockerError: If the test execution fails.
        """
        if not self._work_dir:
            raise DockerError(
                "Docker test environment not set up",
                details={"solution": "Call setup() before running tests"}
            )

        # Generate a container name if not provided
        if not name:
            name = f"testronaut-test-{uuid.uuid4().hex[:8]}"

        # Combine environment variables
        merged_env = {}
        merged_env.update(self.environment)
        if environment:
            merged_env.update(environment)

        # Prepare volumes
        volumes = {
            str(self._work_dir): "/workspace"
        }

        # Run the container
        try:
            result = self.docker_client.run_container(
                image=self.image,
                command=command,
                environment=merged_env,
                volumes=volumes,
                work_dir=work_dir or "/workspace",
                network=self.network_name, # Use the assigned network name/ID
                container_name=name,
                remove=True, # Keep removing test containers by default
                timeout=timeout
            )

            # Store container information
            self._containers[name] = result.get("container_id", "")

            return result

        except Exception as e:
            raise DockerError(
                f"Failed to run test in Docker container: {name}",
                details={"error": str(e), "command": command, "container_name": name}
            ) from e

    def copy_to_workspace(self, source: Union[str, Path], destination: Optional[str] = None) -> str:
        """
        Copy a file to the workspace directory.

        Args:
            source: The source file or directory on the host.
            destination: The destination path in the workspace directory (relative to workspace root).
                         If None, the file is copied to the workspace root.

        Returns:
            The path to the file in the container workspace.

        Raises:
            DockerError: If the copy operation fails.
        """
        if not self._work_dir:
            raise DockerError(
                "Docker test environment not set up",
                details={"solution": "Call setup() before copying files"}
            )

        try:
            source_path = Path(source)

            # Determine destination path
            dest_path = self._work_dir
            if destination:
                dest_path = dest_path / destination
            else:
                dest_path = dest_path / source_path.name

            # Create parent directories if needed
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy the file or directory
            if source_path.is_dir():
                import shutil
                shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
            else:
                import shutil
                shutil.copy2(source_path, dest_path)

            # Return the path in the container
            container_path = f"/workspace/{dest_path.relative_to(self._work_dir)}"

            logger.debug(
                "Copied file to workspace",
                source=str(source_path),
                destination=str(dest_path),
                container_path=container_path
            )

            return container_path

        except Exception as e:
            raise DockerError(
                f"Failed to copy file to workspace: {source}",
                details={"error": str(e), "source": str(source), "destination": destination}
            ) from e

    def teardown(self) -> None:
        """
        Tear down the Docker test environment.

        Raises:
            DockerError: If the environment teardown fails.
        """
        errors = []

        # Stop and remove containers
        for name, container_id in self._containers.items():
            try:
                if container_id:
                    self.docker_client.remove_container(container_id, force=True)
            except Exception as e:
                errors.append(f"Failed to remove container {name}: {str(e)}")

            # Remove network if we created it
            if self._managed_network_id:
                try:
                    # Use facade to remove network
                    self.docker_client.remove_network(self._managed_network_id)
                except Exception as e:
                    errors.append(f"Failed to remove managed network {self._managed_network_id}: {str(e)}")

            # Volumes are not explicitly managed/created by this class, so don't remove them here
            # for name in self._volumes.keys():
            #     try:
            #         self.docker_client.remove_volume(name)
            #     except Exception as e:
            #         errors.append(f"Failed to remove volume {name}: {str(e)}")

        # Remove work directory if we created it
        if self._work_dir and self.base_work_dir is None:
            try:
                import shutil
                shutil.rmtree(self._work_dir, ignore_errors=True)
            except Exception as e:
                errors.append(f"Failed to remove work directory {self._work_dir}: {str(e)}")

        # Reset state
            # Reset state
            self._managed_network_id = None
            self._work_dir = None
            # self._volumes = {}
            self._containers = {}

        # Report errors
        if errors:
            logger.error(
                "Errors during Docker test environment teardown",
                errors=errors
            )
            raise DockerError(
                "Failed to tear down Docker test environment",
                details={"errors": errors}
            )

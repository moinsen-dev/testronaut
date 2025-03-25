"""
Docker Integration Utilities.

This module provides utilities for managing Docker containers for test isolation.
"""
import json
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from testronaut.utils.command import CommandRunner
from testronaut.utils.errors import DockerError
from testronaut.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


class DockerClient:
    """Client for managing Docker containers."""

    def __init__(self, command_runner: Optional[CommandRunner] = None):
        """
        Initialize the Docker client.

        Args:
            command_runner: Command runner for executing Docker commands.
        """
        self.command_runner = command_runner or CommandRunner()

        # Check if Docker is available
        if not self.is_docker_available():
            logger.warning("Docker is not available on the system")

    def is_docker_available(self) -> bool:
        """
        Check if Docker is available on the system.

        Returns:
            True if Docker is available, False otherwise.
        """
        return self.command_runner.is_command_available("docker")

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

            # Check if Docker daemon is running
            if not info.get("ServerVersion"):
                raise DockerError(
                    "Docker daemon is not running",
                    details={"output": result.output}
                )

            return info

        except json.JSONDecodeError as e:
            raise DockerError(
                "Failed to parse Docker info output",
                details={"error": str(e), "output": result.output if 'result' in locals() else None}
            ) from e

        except Exception as e:
            raise DockerError(
                "Failed to check Docker status",
                details={"error": str(e)}
            ) from e

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
                check=True
            )

            logger.info(f"Docker image pulled: {image}")

        except Exception as e:
            raise DockerError(
                f"Failed to pull Docker image: {image}",
                details={"error": str(e)}
            ) from e

    def run_container(
        self,
        image: str,
        command: Optional[Union[str, List[str]]] = None,
        environment: Optional[Dict[str, str]] = None,
        volumes: Optional[Dict[str, str]] = None,
        work_dir: Optional[Union[str, Path]] = None,
        network: Optional[str] = None,
        entrypoint: Optional[Union[str, List[str]]] = None,
        container_name: Optional[str] = None,
        remove: bool = True,
        tty: bool = False,
        interactive: bool = False,
        detach: bool = False,
        pull: bool = False,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run a Docker container.

        Args:
            image: The Docker image to run.
            command: The command to run in the container.
            environment: Environment variables for the container.
            volumes: Volumes to mount in the container.
            work_dir: Working directory in the container.
            network: Docker network to connect the container to.
            entrypoint: Entrypoint for the container.
            container_name: Name for the container.
            remove: Whether to remove the container after it exits.
            tty: Whether to allocate a TTY.
            interactive: Whether to keep STDIN open.
            detach: Whether to run the container in the background.
            pull: Whether to pull the image before running.
            timeout: Timeout for the container in seconds.

        Returns:
            A dictionary with information about the container.

        Raises:
            DockerError: If the container run fails.
        """
        # Ensure Docker is available
        if not self.is_docker_available():
            raise DockerError(
                "Docker is not available on the system",
                details={"solution": "Install Docker and ensure it's in the PATH"}
            )

        # Generate a container name if not provided
        if not container_name:
            container_name = f"testronaut-{uuid.uuid4().hex[:8]}"

        # Pull the image if requested
        if pull:
            self.pull_image(image, quiet=True)

        try:
            # Prepare docker run command
            docker_cmd = ["docker", "run"]

            # Add options
            if remove:
                docker_cmd.append("--rm")

            if tty:
                docker_cmd.append("--tty")

            if interactive:
                docker_cmd.append("--interactive")

            if detach:
                docker_cmd.append("--detach")

            if container_name:
                docker_cmd.extend(["--name", container_name])

            # Add environment variables
            if environment:
                for key, value in environment.items():
                    docker_cmd.extend(["--env", f"{key}={value}"])

            # Add volumes
            if volumes:
                for host_path, container_path in volumes.items():
                    docker_cmd.extend(["--volume", f"{host_path}:{container_path}"])

            # Add working directory
            if work_dir:
                docker_cmd.extend(["--workdir", str(work_dir)])

            # Add network
            if network:
                docker_cmd.extend(["--network", network])

            # Add entrypoint
            if entrypoint:
                if isinstance(entrypoint, list):
                    docker_cmd.extend(["--entrypoint", entrypoint[0]])
                    if len(entrypoint) > 1:
                        command = entrypoint[1:]
                else:
                    docker_cmd.extend(["--entrypoint", entrypoint])

            # Add image
            docker_cmd.append(image)

            # Add command
            if command:
                if isinstance(command, list):
                    docker_cmd.extend(command)
                else:
                    docker_cmd.append(command)

            # Log the Docker run command
            logger.debug(
                "Running Docker container",
                image=image,
                container_name=container_name,
                command=command,
                detach=detach
            )

            # Run the container
            result = self.command_runner.run(
                docker_cmd,
                timeout=timeout,
                check=True
            )

            # Get container ID if detached
            container_id = result.output.strip() if detach else None

            # Prepare result
            container_info = {
                "container_name": container_name,
                "container_id": container_id,
                "image": image,
                "command": command,
                "exit_code": result.return_code,
                "output": result.output,
                "error": result.error,
                "duration_ms": result.duration_ms,
                "detached": detach
            }

            logger.debug(
                "Docker container run completed",
                container_name=container_name,
                container_id=container_id,
                exit_code=result.return_code,
                duration_ms=result.duration_ms
            )

            return container_info

        except Exception as e:
            raise DockerError(
                f"Failed to run Docker container: {container_name}",
                details={
                    "error": str(e),
                    "image": image,
                    "command": command,
                    "container_name": container_name
                }
            ) from e

    def stop_container(self, container_id: str, timeout: Optional[int] = None) -> None:
        """
        Stop a Docker container.

        Args:
            container_id: The ID or name of the container to stop.
            timeout: Timeout in seconds before killing the container.

        Raises:
            DockerError: If the container stop fails.
        """
        try:
            command = ["docker", "stop"]
            if timeout is not None:
                command.extend(["--time", str(timeout)])
            command.append(container_id)

            logger.debug(f"Stopping Docker container: {container_id}")
            result = self.command_runner.run(
                command,
                check=True
            )

            logger.debug(f"Docker container stopped: {container_id}")

        except Exception as e:
            raise DockerError(
                f"Failed to stop Docker container: {container_id}",
                details={"error": str(e)}
            ) from e

    def remove_container(self, container_id: str, force: bool = False) -> None:
        """
        Remove a Docker container.

        Args:
            container_id: The ID or name of the container to remove.
            force: Whether to force removal of the container.

        Raises:
            DockerError: If the container removal fails.
        """
        try:
            command = ["docker", "rm"]
            if force:
                command.append("--force")
            command.append(container_id)

            logger.debug(f"Removing Docker container: {container_id}")
            result = self.command_runner.run(
                command,
                check=True
            )

            logger.debug(f"Docker container removed: {container_id}")

        except Exception as e:
            raise DockerError(
                f"Failed to remove Docker container: {container_id}",
                details={"error": str(e)}
            ) from e

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
            name: The name of the network.
            driver: The network driver.
            subnet: The subnet for the network.
            gateway: The gateway for the network.

        Returns:
            The ID of the created network.

        Raises:
            DockerError: If the network creation fails.
        """
        try:
            # Generate a network name if not provided
            if not name:
                name = f"testronaut-network-{uuid.uuid4().hex[:8]}"

            # Prepare network create command
            command = ["docker", "network", "create", "--driver", driver]

            # Add subnet and gateway if provided
            if subnet:
                command.extend(["--subnet", subnet])

            if gateway:
                command.extend(["--gateway", gateway])

            # Add network name
            command.append(name)

            logger.debug(f"Creating Docker network: {name}")
            result = self.command_runner.run(
                command,
                check=True
            )

            # Get network ID
            network_id = result.output.strip()

            logger.debug(f"Docker network created: {name} ({network_id})")

            return network_id

        except Exception as e:
            raise DockerError(
                f"Failed to create Docker network: {name}",
                details={"error": str(e)}
            ) from e

    def remove_network(self, network_id: str) -> None:
        """
        Remove a Docker network.

        Args:
            network_id: The ID or name of the network to remove.

        Raises:
            DockerError: If the network removal fails.
        """
        try:
            command = ["docker", "network", "rm", network_id]

            logger.debug(f"Removing Docker network: {network_id}")
            result = self.command_runner.run(
                command,
                check=True
            )

            logger.debug(f"Docker network removed: {network_id}")

        except Exception as e:
            raise DockerError(
                f"Failed to remove Docker network: {network_id}",
                details={"error": str(e)}
            ) from e

    def create_volume(self, name: Optional[str] = None) -> str:
        """
        Create a Docker volume.

        Args:
            name: The name of the volume.

        Returns:
            The name of the created volume.

        Raises:
            DockerError: If the volume creation fails.
        """
        try:
            # Generate a volume name if not provided
            if not name:
                name = f"testronaut-volume-{uuid.uuid4().hex[:8]}"

            # Prepare volume create command
            command = ["docker", "volume", "create", name]

            logger.debug(f"Creating Docker volume: {name}")
            result = self.command_runner.run(
                command,
                check=True
            )

            # Get volume name
            volume_name = result.output.strip()

            logger.debug(f"Docker volume created: {volume_name}")

            return volume_name

        except Exception as e:
            raise DockerError(
                f"Failed to create Docker volume: {name}",
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
            raise DockerError(
                f"Failed to remove Docker volume: {volume_name}",
                details={"error": str(e)}
            ) from e

    def copy_to_container(
        self,
        container_id: str,
        source: Union[str, Path],
        destination: str
    ) -> None:
        """
        Copy a file or directory to a container.

        Args:
            container_id: The ID or name of the container.
            source: The source file or directory on the host.
            destination: The destination path in the container.

        Raises:
            DockerError: If the copy operation fails.
        """
        try:
            # Prepare cp command
            command = ["docker", "cp", str(source), f"{container_id}:{destination}"]

            logger.debug(
                "Copying to Docker container",
                container_id=container_id,
                source=source,
                destination=destination
            )

            result = self.command_runner.run(
                command,
                check=True
            )

            logger.debug(
                "Copied to Docker container",
                container_id=container_id,
                source=source,
                destination=destination
            )

        except Exception as e:
            raise DockerError(
                f"Failed to copy to Docker container: {container_id}",
                details={
                    "error": str(e),
                    "source": str(source),
                    "destination": destination
                }
            ) from e

    def copy_from_container(
        self,
        container_id: str,
        source: str,
        destination: Union[str, Path]
    ) -> None:
        """
        Copy a file or directory from a container.

        Args:
            container_id: The ID or name of the container.
            source: The source path in the container.
            destination: The destination file or directory on the host.

        Raises:
            DockerError: If the copy operation fails.
        """
        try:
            # Prepare cp command
            command = ["docker", "cp", f"{container_id}:{source}", str(destination)]

            logger.debug(
                "Copying from Docker container",
                container_id=container_id,
                source=source,
                destination=destination
            )

            result = self.command_runner.run(
                command,
                check=True
            )

            logger.debug(
                "Copied from Docker container",
                container_id=container_id,
                source=source,
                destination=destination
            )

        except Exception as e:
            raise DockerError(
                f"Failed to copy from Docker container: {container_id}",
                details={
                    "error": str(e),
                    "source": source,
                    "destination": str(destination)
                }
            ) from e


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
        self.docker_client = docker_client or DockerClient()
        self.base_work_dir = Path(base_work_dir) if base_work_dir else None
        self.network = network
        self.environment = environment or {}
        self.pull_image = pull_image

        # Generated resources
        self._network_id: Optional[str] = None
        self._work_dir: Optional[Path] = None
        self._volumes: Dict[str, str] = {}
        self._containers: Dict[str, str] = {}

        # Check Docker availability
        if not self.docker_client.is_docker_available():
            raise DockerError(
                "Docker is not available on the system",
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

            # Create a network if needed
            if self.network is None:
                self._network_id = self.docker_client.create_network()
                self.network = self._network_id

            # Pull the image if requested
            if self.pull_image:
                self.docker_client.pull_image(self.image)

            # Return environment information
            return {
                "image": self.image,
                "work_dir": str(self._work_dir),
                "network": self.network,
                "managed_network": self._network_id is not None,
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
                network=self.network,
                container_name=name,
                remove=True,
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
        if self._network_id:
            try:
                self.docker_client.remove_network(self._network_id)
            except Exception as e:
                errors.append(f"Failed to remove network {self._network_id}: {str(e)}")

        # Remove volumes
        for name in self._volumes.keys():
            try:
                self.docker_client.remove_volume(name)
            except Exception as e:
                errors.append(f"Failed to remove volume {name}: {str(e)}")

        # Remove work directory if we created it
        if self._work_dir and self.base_work_dir is None:
            try:
                import shutil
                shutil.rmtree(self._work_dir, ignore_errors=True)
            except Exception as e:
                errors.append(f"Failed to remove work directory {self._work_dir}: {str(e)}")

        # Reset state
        self._network_id = None
        self._work_dir = None
        self._volumes = {}
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
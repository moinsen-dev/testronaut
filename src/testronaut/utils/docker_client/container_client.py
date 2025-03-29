"""
Docker Container Client.

Provides methods for managing Docker containers (run, stop, remove, copy).
"""
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from testronaut.utils.command import CommandRunner
from testronaut.utils.errors import DockerError
from testronaut.utils.logging import get_logger

logger = get_logger(__name__)

class ContainerClient:
    """Client for Docker container operations."""

    def __init__(self, command_runner: Optional[CommandRunner] = None):
        """
        Initialize the Docker container client.

        Args:
            command_runner: Command runner for executing Docker commands.
        """
        self.command_runner = command_runner or CommandRunner()
        # Assume docker availability is checked elsewhere

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
        # pull: bool = False, # Pulling should be handled by ImageClient
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run a Docker container.

        Args:
            image: The Docker image to run.
            command: The command to run in the container.
            environment: Environment variables for the container.
            volumes: Volumes to mount in the container. Format: {host_path: container_path}
            work_dir: Working directory in the container.
            network: Docker network to connect the container to.
            entrypoint: Entrypoint for the container.
            container_name: Name for the container.
            remove: Whether to remove the container after it exits.
            tty: Whether to allocate a TTY.
            interactive: Whether to keep STDIN open.
            detach: Whether to run the container in the background.
            timeout: Timeout for the container run command in seconds.

        Returns:
            A dictionary with information about the container run result.

        Raises:
            DockerError: If the container run fails.
        """
        # Generate a container name if not provided
        if not container_name:
            container_name = f"testronaut-run-{uuid.uuid4().hex[:8]}"

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
            entrypoint_cmd: Optional[List[str]] = None
            if entrypoint:
                if isinstance(entrypoint, list):
                    docker_cmd.extend(["--entrypoint", entrypoint[0]])
                    if len(entrypoint) > 1:
                        # If entrypoint is a list, the rest become the command
                        entrypoint_cmd = entrypoint[1:]
                else:
                    docker_cmd.extend(["--entrypoint", entrypoint])

            # Add image
            docker_cmd.append(image)

            # Add command (use entrypoint_cmd if derived from list entrypoint)
            final_command = entrypoint_cmd if entrypoint_cmd is not None else command
            if final_command:
                if isinstance(final_command, list):
                    docker_cmd.extend(final_command)
                else:
                    # Split string command respecting quotes
                    import shlex
                    docker_cmd.extend(shlex.split(final_command))


            # Log the Docker run command
            logger.debug(
                "Running Docker container",
                image=image,
                container_name=container_name,
                command=final_command, # Log the actual command being run
                detach=detach
            )

            # Run the container
            result = self.command_runner.run(
                docker_cmd,
                timeout=timeout,
                check=True # Raise error on failure
            )

            # Get container ID if detached
            container_id = result.output.strip() if detach else None

            # Prepare result
            container_info = {
                "container_name": container_name,
                "container_id": container_id,
                "image": image,
                "command": final_command, # Report the actual command run
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
            logger.error(f"Failed to run Docker container '{container_name}': {e}", exc_info=True)
            raise DockerError(
                f"Failed to run Docker container: {container_name}",
                details={
                    "error": str(e),
                    "image": image,
                    "command": final_command if 'final_command' in locals() else command,
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
            logger.error(f"Failed to stop Docker container '{container_id}': {e}", exc_info=True)
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
            logger.error(f"Failed to remove Docker container '{container_id}': {e}", exc_info=True)
            raise DockerError(
                f"Failed to remove Docker container: {container_id}",
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
                "Copied to Docker container successfully",
                container_id=container_id,
                source=source,
                destination=destination
            )

        except Exception as e:
            logger.error(f"Failed to copy to Docker container '{container_id}': {e}", exc_info=True)
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
                "Copied from Docker container successfully",
                container_id=container_id,
                source=source,
                destination=destination
            )

        except Exception as e:
            logger.error(f"Failed to copy from Docker container '{container_id}': {e}", exc_info=True)
            raise DockerError(
                f"Failed to copy from Docker container: {container_id}",
                details={
                    "error": str(e),
                    "source": source,
                    "destination": str(destination)
                }
            ) from e

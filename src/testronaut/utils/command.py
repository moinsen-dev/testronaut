"""
Command Execution Utilities.

This module provides utilities for executing shell commands with timeout and error handling.
"""
import os
import shlex
import signal
import subprocess
import threading
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Any, Callable, Tuple

from testronaut.utils.errors import CommandExecutionError, TimeoutError
from testronaut.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


@dataclass
class CommandResult:
    """Result of a command execution."""

    command: str
    return_code: int
    output: str
    error: str
    duration_ms: int
    timed_out: bool = False

    @property
    def succeeded(self) -> bool:
        """Whether the command execution was successful."""
        return self.return_code == 0 and not self.timed_out


class CommandRunner:
    """Utility for running shell commands."""

    def __init__(
        self,
        cwd: Optional[Union[str, Path]] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        shell: bool = False
    ):
        """
        Initialize the command runner.

        Args:
            cwd: Working directory for command execution.
            env: Environment variables for command execution.
            timeout: Default timeout in seconds.
            shell: Whether to run commands through the shell.
        """
        self.cwd = Path(cwd) if cwd else None
        self.env = env
        self.timeout = timeout
        self.shell = shell

        # Merge environment with system environment if provided
        if self.env:
            self.env = {**os.environ, **self.env}

    def run(
        self,
        command: Union[str, List[str]],
        cwd: Optional[Union[str, Path]] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        capture_output: bool = True,
        check: bool = False,
        shell: Optional[bool] = None
    ) -> CommandResult:
        """
        Run a command and return the result.

        Args:
            command: The command to run as a string or list of arguments.
            cwd: Working directory for command execution (overrides instance cwd).
            env: Environment variables for command execution (merges with instance env).
            timeout: Timeout in seconds (overrides instance timeout).
            capture_output: Whether to capture stdout and stderr.
            check: Whether to check the return code and raise an exception if it's non-zero.
            shell: Whether to run the command through the shell (overrides instance shell).

        Returns:
            The result of the command execution.

        Raises:
            CommandExecutionError: If the command execution fails and check is True.
            TimeoutError: If the command times out.
        """
        # Prepare command
        if isinstance(command, list):
            cmd_list = command
            cmd_str = " ".join(shlex.quote(arg) for arg in command)
        else:
            cmd_str = command
            if shell is None:
                shell = self.shell
            if shell:
                cmd_list = command
            else:
                cmd_list = shlex.split(command)

        # Prepare working directory
        effective_cwd = cwd or self.cwd
        if effective_cwd:
            effective_cwd = Path(effective_cwd)
            effective_cwd.mkdir(parents=True, exist_ok=True)

        # Prepare environment
        effective_env = self.env
        if env:
            if effective_env:
                effective_env = {**effective_env, **env}
            else:
                effective_env = {**os.environ, **env}

        # Prepare timeout
        effective_timeout = timeout if timeout is not None else self.timeout

        # Prepare shell parameter
        effective_shell = shell if shell is not None else self.shell

        # Prepare stdout and stderr
        stdout = subprocess.PIPE if capture_output else None
        stderr = subprocess.PIPE if capture_output else None

        # Log the command execution
        logger.debug(
            "Executing command",
            command=cmd_str,
            cwd=str(effective_cwd) if effective_cwd else None,
            timeout=effective_timeout,
            shell=effective_shell
        )

        # Execute the command
        start_time = __import__("time").time()
        process = None
        try:
            process = subprocess.Popen(
                cmd_list,
                cwd=effective_cwd,
                env=effective_env,
                stdout=stdout,
                stderr=stderr,
                shell=effective_shell,
                universal_newlines=True,
                bufsize=1  # Line buffered
            )

            timed_out = False
            output, error = process.communicate(timeout=effective_timeout)
            return_code = process.returncode

        except subprocess.TimeoutExpired:
            timed_out = True

            # Kill the process
            if process is not None:
                process.kill()
                output, error = process.communicate()
                return_code = process.returncode
            else:
                output, error = "", "Command timed out"
                return_code = -1

        except Exception as e:
            logger.error(
                "Command execution failed",
                command=cmd_str,
                error=str(e)
            )
            if process is not None:
                process.kill()
                output, error = process.communicate()
                return_code = process.returncode
            else:
                output, error = "", str(e)
                return_code = -1

        # Calculate duration
        end_time = __import__("time").time()
        duration_ms = int((end_time - start_time) * 1000)

        # Create result
        result = CommandResult(
            command=cmd_str,
            return_code=return_code,
            output=output or "",
            error=error or "",
            duration_ms=duration_ms,
            timed_out=timed_out
        )

        # Log the result
        log_level = "error" if not result.succeeded else "debug"
        getattr(logger, log_level)(
            "Command execution completed",
            command=cmd_str,
            return_code=return_code,
            duration_ms=duration_ms,
            timed_out=timed_out,
            success=result.succeeded
        )

        # Check result if requested
        if check and not result.succeeded:
            if timed_out:
                raise TimeoutError(
                    f"Command timed out after {effective_timeout} seconds: {cmd_str}",
                    details={
                        "command": cmd_str,
                        "timeout": effective_timeout,
                        "output": output,
                        "error": error
                    }
                )
            else:
                raise CommandExecutionError(
                    f"Command failed with exit code {return_code}: {cmd_str}",
                    details={
                        "command": cmd_str,
                        "return_code": return_code,
                        "output": output,
                        "error": error
                    }
                )

        return result

    def run_with_retries(
        self,
        command: Union[str, List[str]],
        retries: int = 3,
        retry_delay: float = 1.0,
        retry_backoff: float = 2.0,
        retry_on_return_codes: Optional[List[int]] = None,
        **kwargs
    ) -> CommandResult:
        """
        Run a command with retries on failure.

        Args:
            command: The command to run.
            retries: Maximum number of retry attempts.
            retry_delay: Initial delay between retries in seconds.
            retry_backoff: Backoff factor for retry delay.
            retry_on_return_codes: List of return codes to retry on. If None, retry on any non-zero code.
            **kwargs: Additional arguments for the run method.

        Returns:
            The result of the command execution.

        Raises:
            CommandExecutionError: If the command execution fails after all retries and check is True.
            TimeoutError: If the command times out after all retries.
        """
        # Disable check in kwargs as we'll handle it ourselves
        check = kwargs.pop("check", False)

        # Initialize retry variables
        attempt = 0
        delay = retry_delay
        last_result = None

        while attempt <= retries:
            try:
                result = self.run(command, check=False, **kwargs)

                # Check if command succeeded
                if result.succeeded:
                    # Command succeeded, return the result
                    return result

                # Check if we should retry based on return code
                if retry_on_return_codes is not None and result.return_code not in retry_on_return_codes:
                    # Don't retry for this return code
                    last_result = result
                    break

                # Store the result for potential error reporting
                last_result = result

                # Check if we've exhausted our retries
                if attempt >= retries:
                    break

                # Log the retry
                logger.warning(
                    "Retrying command",
                    command=result.command,
                    return_code=result.return_code,
                    attempt=attempt + 1,
                    max_attempts=retries,
                    delay=delay
                )

                # Wait before retrying
                __import__("time").sleep(delay)

                # Increase the delay for the next retry
                delay *= retry_backoff

            except Exception as e:
                # If we've exhausted our retries, re-raise the exception
                if attempt >= retries:
                    raise

                # Log the retry
                logger.warning(
                    "Retrying command after exception",
                    command=command if isinstance(command, str) else " ".join(command),
                    error=str(e),
                    attempt=attempt + 1,
                    max_attempts=retries,
                    delay=delay
                )

                # Wait before retrying
                __import__("time").sleep(delay)

                # Increase the delay for the next retry
                delay *= retry_backoff

            # Increment the attempt counter
            attempt += 1

        # If we've exhausted all retries and check is True, raise an exception
        if check and last_result and not last_result.succeeded:
            if last_result.timed_out:
                raise TimeoutError(
                    f"Command timed out after all retries: {last_result.command}",
                    details={
                        "command": last_result.command,
                        "retries": retries,
                        "output": last_result.output,
                        "error": last_result.error
                    }
                )
            else:
                raise CommandExecutionError(
                    f"Command failed with exit code {last_result.return_code} after all retries: {last_result.command}",
                    details={
                        "command": last_result.command,
                        "return_code": last_result.return_code,
                        "retries": retries,
                        "output": last_result.output,
                        "error": last_result.error
                    }
                )

        # Return the last result (which is a failure if we got here)
        return last_result or CommandResult(
            command=command if isinstance(command, str) else " ".join(command),
            return_code=-1,
            output="",
            error="No command was executed",
            duration_ms=0,
            timed_out=False
        )

    @staticmethod
    def is_command_available(command: str) -> bool:
        """
        Check if a command is available in the system PATH.

        Args:
            command: The command to check.

        Returns:
            True if the command is available, False otherwise.
        """
        # For Windows
        if os.name == "nt":
            command = command + ".exe"

        # Check if the command exists and is executable
        return any(
            os.access(os.path.join(path, command), os.X_OK)
            for path in os.environ.get("PATH", "").split(os.pathsep)
            if os.path.exists(os.path.join(path, command))
        )

    @staticmethod
    def parse_key_value_output(
        output: str,
        separator: str = ":",
        key_transform: Optional[Callable[[str], str]] = None
    ) -> Dict[str, str]:
        """
        Parse command output with key-value pairs.

        Args:
            output: The command output to parse.
            separator: The separator between keys and values.
            key_transform: A function to transform keys (e.g., lowercase).

        Returns:
            A dictionary with parsed key-value pairs.
        """
        result = {}
        for line in output.splitlines():
            line = line.strip()
            if not line or separator not in line:
                continue

            key, value = line.split(separator, 1)
            key = key.strip()
            value = value.strip()

            if key_transform:
                key = key_transform(key)

            result[key] = value

        return result
"""
Database migration utilities.

This module provides functions to manage database migrations with Alembic.
"""
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

import alembic.config


def get_migrations_dir() -> Path:
    """Get the directory containing migration scripts."""
    return Path(__file__).parent.absolute()


def run_alembic_command(command: List[str], capture_output: bool = False) -> Optional[str]:
    """
    Run an Alembic command.

    Args:
        command: The Alembic command and its arguments.
        capture_output: Whether to capture and return command output.

    Returns:
        The command output if capture_output is True, otherwise None.
    """
    alembic_args = [
        '--config', str(get_migrations_dir() / 'alembic.ini'),
        *command
    ]

    # Create Alembic config object
    alembic_cfg = alembic.config.Config(str(get_migrations_dir() / 'alembic.ini'))

    # Change to the migrations directory
    original_dir = os.getcwd()
    os.chdir(str(get_migrations_dir()))

    try:
        if capture_output:
            result = subprocess.run(
                ['alembic', *alembic_args],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        else:
            alembic.config.main(argv=alembic_args)
            return None
    except Exception as e:
        print(f"Error running Alembic command: {e}")
        raise
    finally:
        # Restore original directory
        os.chdir(original_dir)


def create_migration(message: str) -> None:
    """
    Create a new migration with the given message.

    Args:
        message: The migration message.
    """
    run_alembic_command(['revision', '--autogenerate', '-m', message])


def upgrade_database(revision: str = 'head') -> None:
    """
    Upgrade the database to the specified revision.

    Args:
        revision: The target revision, defaults to 'head'.
    """
    run_alembic_command(['upgrade', revision])


def downgrade_database(revision: str) -> None:
    """
    Downgrade the database to the specified revision.

    Args:
        revision: The target revision.
    """
    run_alembic_command(['downgrade', revision])


def get_current_revision() -> str:
    """
    Get the current database revision.

    Returns:
        The current revision or "No revision" if no migrations have been applied.
    """
    output = run_alembic_command(['current'], capture_output=True)
    if output and 'current' in output:
        return output.strip()
    return "No revision"


def get_migration_history() -> str:
    """
    Get the migration history.

    Returns:
        The migration history as a string.
    """
    return run_alembic_command(['history'], capture_output=True) or ""
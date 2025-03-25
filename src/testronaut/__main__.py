"""
Main entry point for the Testronaut CLI.

This module allows the package to be run as a script with `python -m testronaut`.
"""
import sys

from testronaut.cli import app

if __name__ == "__main__":
    sys.exit(app())
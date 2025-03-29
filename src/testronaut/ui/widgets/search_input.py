"""
SearchInput Widget for the Testronaut DB Browser.
"""
from textual.widgets import Input

class SearchInput(Input):
    """Search input widget."""

    def __init__(self) -> None:
        """Initialize search input."""
        super().__init__(placeholder="Search commands...")
        # Add any specific initialization if needed in the future

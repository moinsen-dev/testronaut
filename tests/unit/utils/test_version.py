"""
Unit tests for version utilities.
"""

import pytest

from testronaut.utils.version import (
    get_version_components,
    normalize_version,
    parse_version,
    requires_reanalysis,
)


@pytest.mark.unit
class TestVersionUtils:
    """Tests for version utility functions."""

    def test_parse_version_valid(self):
        """Test parse_version with valid version strings."""
        assert parse_version("1.2.3") == (1, 2, 3)
        assert parse_version("v2.0.1") == (2, 0, 1)
        assert parse_version("V3.4.5") == (3, 4, 5)
        assert parse_version("1.0") == (1, 0, 0)
        assert parse_version("2") == (2, 0, 0)

    def test_parse_version_invalid(self):
        """Test parse_version with invalid version strings."""
        assert parse_version("") is None
        assert parse_version("abc") is None
        assert parse_version("1.x.3") is None

    def test_normalize_version(self):
        """Test normalize_version function."""
        assert normalize_version("1.2.3") == "1.2.3"
        assert normalize_version("v2.0.1") == "2.0.1"
        assert normalize_version("1") == "1.0.0"
        # Test with unparseable version
        assert normalize_version("abc") == "abc"

    def test_requires_reanalysis(self):
        """Test requires_reanalysis function."""
        # Major version changes (should require reanalysis)
        assert requires_reanalysis("1.0.0", "2.0.0") is True
        assert requires_reanalysis("2.1.0", "3.0.0") is True

        # Minor version changes (should require reanalysis)
        assert requires_reanalysis("1.1.0", "1.2.0") is True
        assert requires_reanalysis("2.3.1", "2.4.1") is True

        # Patch version changes (should not require reanalysis)
        assert requires_reanalysis("1.0.1", "1.0.2") is False
        assert requires_reanalysis("2.3.4", "2.3.5") is False

        # Same version (should not require reanalysis)
        assert requires_reanalysis("1.2.3", "1.2.3") is False

        # Missing versions (should require reanalysis)
        assert requires_reanalysis("", "1.0.0") is True
        assert requires_reanalysis("1.0.0", "") is True
        assert requires_reanalysis("", "") is True

        # Invalid versions (should require reanalysis)
        assert requires_reanalysis("abc", "1.0.0") is True
        assert requires_reanalysis("1.0.0", "xyz") is True

    def test_get_version_components(self):
        """Test get_version_components function."""
        assert get_version_components("1.2.3") == (1, 2, 3)
        assert get_version_components("v2.0.1") == (2, 0, 1)
        assert get_version_components("3") == (3, 0, 0)
        assert get_version_components("") == (0, 0, 0)
        assert get_version_components("invalid") == (0, 0, 0)

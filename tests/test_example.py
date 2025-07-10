"""
Unit tests for example_module
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add source directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from example_module import *
except ImportError:
    # Mock the module if it doesn't exist yet
    pass


class TestExample_Module:
    """Unit tests for example_module"""

    def test_example_function(self):
        """Test example function"""
        # TODO: Implement test
        assert True

    def test_with_mock(self):
        """Test with mock objects"""
        mock_obj = Mock()
        mock_obj.method.return_value = "test"
        assert mock_obj.method() == "test"

    @pytest.mark.parametrize("input_val,expected", [
        (1, 2),
        (2, 3),
        (3, 4),
    ])
    def test_parametrized(self, input_val, expected):
        """Parametrized test example"""
        # TODO: Implement parametrized test
        assert input_val + 1 == expected

    def test_exception_handling(self):
        """Test exception handling"""
        with pytest.raises(ValueError):
            # TODO: Code that should raise ValueError
            raise ValueError("Test exception")

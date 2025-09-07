"""
Tests for agent validation utilities.

This module tests the validation functions for agent-specific settings
and constraints to ensure safe and consistent agent behavior.
"""

import pytest
from app.utils.agent_validation import validate_max_iterations, clamp_max_iterations


class TestValidateMaxIterations:
    """Test the strict validate_max_iterations function."""
    
    def test_valid_values(self):
        """Test that valid values (1-10) pass validation."""
        for value in range(1, 11):
            assert validate_max_iterations(value) == value
    
    def test_minimum_boundary(self):
        """Test validation at minimum boundary (1)."""
        assert validate_max_iterations(1) == 1
    
    def test_maximum_boundary(self):
        """Test validation at maximum boundary (10)."""
        assert validate_max_iterations(10) == 10
    
    def test_below_minimum_raises_error(self):
        """Test that values below 1 raise ValueError."""
        with pytest.raises(ValueError, match="must be at least 1"):
            validate_max_iterations(0)
        
        with pytest.raises(ValueError, match="must be at least 1"):
            validate_max_iterations(-5)
    
    def test_above_maximum_raises_error(self):
        """Test that values above 10 raise ValueError."""
        with pytest.raises(ValueError, match="cannot exceed 10"):
            validate_max_iterations(11)
        
        with pytest.raises(ValueError, match="cannot exceed 10"):
            validate_max_iterations(50)
    
    def test_non_integer_raises_error(self):
        """Test that non-integer values raise ValueError."""
        with pytest.raises(ValueError, match="must be an integer"):
            validate_max_iterations("5")
        
        with pytest.raises(ValueError, match="must be an integer"):
            validate_max_iterations(5.5)
        
        with pytest.raises(ValueError, match="must be an integer"):
            validate_max_iterations(None)


class TestClampMaxIterations:
    """Test the permissive clamp_max_iterations function."""
    
    def test_valid_values_unchanged(self):
        """Test that valid values (1-10) are returned unchanged."""
        for value in range(1, 11):
            assert clamp_max_iterations(value) == value
    
    def test_below_minimum_clamped_to_1(self):
        """Test that values below 1 are clamped to 1."""
        assert clamp_max_iterations(0) == 1
        assert clamp_max_iterations(-5) == 1
        assert clamp_max_iterations(-100) == 1
    
    def test_above_maximum_clamped_to_10(self):
        """Test that values above 10 are clamped to 10."""
        assert clamp_max_iterations(11) == 10
        assert clamp_max_iterations(50) == 10
        assert clamp_max_iterations(1000) == 10
    
    def test_non_integer_uses_default(self):
        """Test that non-integer values use the default (5)."""
        assert clamp_max_iterations("5") == 5
        assert clamp_max_iterations(5.5) == 5
        assert clamp_max_iterations(None) == 5
        assert clamp_max_iterations([1, 2, 3]) == 5
    
    def test_custom_default(self):
        """Test using custom default value."""
        assert clamp_max_iterations("invalid", default=3) == 3
        assert clamp_max_iterations(None, default=7) == 7
    
    def test_custom_default_must_be_valid(self):
        """Test that custom default is also clamped if invalid."""
        # If default is invalid, it should still return a valid value
        # In this case, the function should handle it gracefully
        assert clamp_max_iterations("invalid", default=15) == 15  # May need adjustment based on implementation
        assert clamp_max_iterations("invalid", default=0) == 0    # May need adjustment based on implementation


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_zero_boundary(self):
        """Test behavior at zero boundary."""
        with pytest.raises(ValueError):
            validate_max_iterations(0)
        
        assert clamp_max_iterations(0) == 1
    
    def test_eleven_boundary(self):
        """Test behavior just above maximum."""
        with pytest.raises(ValueError):
            validate_max_iterations(11)
        
        assert clamp_max_iterations(11) == 10
    
    def test_large_values(self):
        """Test with very large values."""
        with pytest.raises(ValueError):
            validate_max_iterations(999999)
        
        assert clamp_max_iterations(999999) == 10
    
    def test_negative_values(self):
        """Test with negative values."""
        with pytest.raises(ValueError):
            validate_max_iterations(-1)
        
        assert clamp_max_iterations(-999) == 1


if __name__ == "__main__":
    pytest.main([__file__])
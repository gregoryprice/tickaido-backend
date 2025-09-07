"""
Agent validation utilities for the AI Ticket Creator application.

This module provides validation functions for agent-specific settings
and constraints to ensure safe and consistent agent behavior.
"""

import logging

logger = logging.getLogger(__name__)


def validate_max_iterations(value: int) -> int:
    """
    Validate and ensure max_iterations is within safe bounds.
    
    Args:
        value: The max_iterations value to validate
        
    Returns:
        int: The validated max_iterations value (1-10)
        
    Raises:
        ValueError: If value is not a valid integer within bounds
        
    Example:
        >>> validate_max_iterations(5)
        5
        >>> validate_max_iterations(15)  # Will raise ValueError
    """
    if not isinstance(value, int):
        raise ValueError("max_iterations must be an integer")
    
    if value < 1:
        raise ValueError("max_iterations must be at least 1")
    
    if value > 10:
        raise ValueError("max_iterations cannot exceed 10")
    
    logger.debug(f"Validated max_iterations: {value}")
    return value


def clamp_max_iterations(value: int, default: int = 5) -> int:
    """
    Clamp max_iterations to valid range without raising exceptions.
    
    This is a more permissive version that clamps invalid values
    to the nearest valid bound instead of raising exceptions.
    
    Args:
        value: The max_iterations value to clamp
        default: Default value if input is not an integer
        
    Returns:
        int: A valid max_iterations value (1-10)
        
    Example:
        >>> clamp_max_iterations(15)
        10
        >>> clamp_max_iterations(0)
        1
        >>> clamp_max_iterations("invalid")
        5
    """
    if not isinstance(value, int):
        logger.warning(f"max_iterations must be an integer, got {type(value)}, using default: {default}")
        return default
    
    if value < 1:
        logger.warning(f"max_iterations {value} is below minimum, clamping to 1")
        return 1
    
    if value > 10:
        logger.warning(f"max_iterations {value} exceeds maximum, clamping to 10")  
        return 10
    
    return value
"""
Tests for agent schema max_iterations validation.

This module tests the Pydantic schema validation for agent max_iterations
to ensure proper bounds checking and error handling.
"""

import pytest
from pydantic import ValidationError
from app.schemas.agent import AgentCreateRequest, AgentUpdateRequest


class TestAgentCreateRequestMaxIterationsValidation:
    """Test AgentCreateRequest schema max_iterations validation."""
    
    def test_valid_max_iterations_values(self):
        """Test that valid max_iterations values (1-10) are accepted."""
        for value in range(1, 11):
            agent_data = {
                "name": "Test Agent",
                "agent_type": "customer_support",
                "role": "Test role",
                "max_iterations": value
            }
            agent = AgentCreateRequest(**agent_data)
            assert agent.max_iterations == value
    
    def test_default_max_iterations(self):
        """Test that default max_iterations is 5 when not specified."""
        agent_data = {
            "name": "Test Agent",
            "agent_type": "customer_support", 
            "role": "Test role"
        }
        agent = AgentCreateRequest(**agent_data)
        assert agent.max_iterations == 5  # Default value
    
    def test_max_iterations_minimum_boundary(self):
        """Test validation at minimum boundary (1)."""
        agent_data = {
            "name": "Test Agent",
            "agent_type": "customer_support",
            "role": "Test role",
            "max_iterations": 1
        }
        agent = AgentCreateRequest(**agent_data)
        assert agent.max_iterations == 1
    
    def test_max_iterations_maximum_boundary(self):
        """Test validation at maximum boundary (10)."""
        agent_data = {
            "name": "Test Agent", 
            "agent_type": "customer_support",
            "role": "Test role",
            "max_iterations": 10
        }
        agent = AgentCreateRequest(**agent_data)
        assert agent.max_iterations == 10
    
    def test_max_iterations_below_minimum_fails(self):
        """Test that max_iterations below 1 raises ValidationError."""
        agent_data = {
            "name": "Test Agent",
            "agent_type": "customer_support",
            "role": "Test role", 
            "max_iterations": 0
        }
        with pytest.raises(ValidationError) as exc_info:
            AgentCreateRequest(**agent_data)
        
        error = exc_info.value.errors()[0]
        assert "greater than or equal to 1" in str(error["msg"])
    
    def test_max_iterations_above_maximum_fails(self):
        """Test that max_iterations above 10 raises ValidationError."""
        agent_data = {
            "name": "Test Agent",
            "agent_type": "customer_support",
            "role": "Test role",
            "max_iterations": 11
        }
        with pytest.raises(ValidationError) as exc_info:
            AgentCreateRequest(**agent_data)
        
        error = exc_info.value.errors()[0]
        assert "less than or equal to 10" in str(error["msg"])
    
    def test_max_iterations_way_above_maximum_fails(self):
        """Test that max_iterations way above maximum fails.""" 
        agent_data = {
            "name": "Test Agent",
            "agent_type": "customer_support", 
            "role": "Test role",
            "max_iterations": 25
        }
        with pytest.raises(ValidationError) as exc_info:
            AgentCreateRequest(**agent_data)
        
        error = exc_info.value.errors()[0]
        assert "less than or equal to 10" in str(error["msg"])
    
    def test_max_iterations_non_integer_fails(self):
        """Test that non-integer max_iterations raises ValidationError."""
        agent_data = {
            "name": "Test Agent",
            "agent_type": "customer_support",
            "role": "Test role",
            "max_iterations": "invalid"  # String that can't be converted to int
        }
        with pytest.raises(ValidationError) as exc_info:
            AgentCreateRequest(**agent_data)
        
        error = exc_info.value.errors()[0]
        assert error["type"] == "int_parsing"


class TestAgentUpdateRequestMaxIterationsValidation:
    """Test AgentUpdateRequest schema max_iterations validation."""
    
    def test_valid_max_iterations_values(self):
        """Test that valid max_iterations values (1-10) are accepted."""
        for value in range(1, 11):
            update_data = {"max_iterations": value}
            update_request = AgentUpdateRequest(**update_data)
            assert update_request.max_iterations == value
    
    def test_none_max_iterations_allowed(self):
        """Test that None is allowed for optional max_iterations."""
        update_data = {"name": "Updated Agent"}
        update_request = AgentUpdateRequest(**update_data) 
        assert update_request.max_iterations is None
    
    def test_explicit_none_max_iterations(self):
        """Test explicitly setting max_iterations to None."""
        update_data = {"max_iterations": None}
        update_request = AgentUpdateRequest(**update_data)
        assert update_request.max_iterations is None
    
    def test_max_iterations_bounds_same_as_create(self):
        """Test that update request has same bounds as create (1-10)."""
        # Test minimum boundary
        update_data = {"max_iterations": 1}
        update_request = AgentUpdateRequest(**update_data)
        assert update_request.max_iterations == 1
        
        # Test maximum boundary
        update_data = {"max_iterations": 10}
        update_request = AgentUpdateRequest(**update_data)
        assert update_request.max_iterations == 10
        
        # Test below minimum fails
        with pytest.raises(ValidationError):
            AgentUpdateRequest(max_iterations=0)
        
        # Test above maximum fails
        with pytest.raises(ValidationError):
            AgentUpdateRequest(max_iterations=11)


class TestMaxIterationsBoundsRegression:
    """Regression tests to ensure bounds changed from 20 to 10."""
    
    def test_old_maximum_20_now_fails(self):
        """Test that the old maximum (20) now fails validation."""
        agent_data = {
            "name": "Test Agent",
            "agent_type": "customer_support",
            "role": "Test role",
            "max_iterations": 20  # This used to be valid, should now fail
        }
        with pytest.raises(ValidationError) as exc_info:
            AgentCreateRequest(**agent_data)
        
        error = exc_info.value.errors()[0]
        assert "less than or equal to 10" in str(error["msg"])
    
    def test_values_11_through_19_fail(self):
        """Test that values in the old valid range (11-19) now fail."""
        for value in [11, 15, 19]:
            agent_data = {
                "name": "Test Agent",
                "agent_type": "customer_support", 
                "role": "Test role",
                "max_iterations": value
            }
            with pytest.raises(ValidationError):
                AgentCreateRequest(**agent_data)
    
    def test_new_maximum_10_passes(self):
        """Test that the new maximum (10) passes validation."""
        agent_data = {
            "name": "Test Agent",
            "agent_type": "customer_support",
            "role": "Test role", 
            "max_iterations": 10
        }
        agent = AgentCreateRequest(**agent_data)
        assert agent.max_iterations == 10


class TestMaxIterationsDescription:
    """Test that field descriptions are accurate."""
    
    def test_description_mentions_iterations(self):
        """Test that field description mentions iterations."""
        schema = AgentCreateRequest.model_json_schema()
        max_iterations_field = schema["properties"]["max_iterations"]
        
        description = max_iterations_field.get("description", "")
        assert "iteration" in description.lower()
    
    def test_field_constraints_in_schema(self):
        """Test that schema shows correct minimum and maximum values."""
        schema = AgentCreateRequest.model_json_schema()
        max_iterations_field = schema["properties"]["max_iterations"]
        
        assert max_iterations_field.get("minimum") == 1
        assert max_iterations_field.get("maximum") == 10


if __name__ == "__main__":
    pytest.main([__file__])
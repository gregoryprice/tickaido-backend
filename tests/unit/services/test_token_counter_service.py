import pytest
from app.services.token_counter_service import token_counter_service

@pytest.mark.asyncio
async def test_count_message_tokens():
    """Test token counting for individual messages."""
    message = {
        "role": "user",
        "content": "Hello, how are you today?"
    }
    
    count = await token_counter_service.count_message_tokens(message)
    assert isinstance(count, int)
    assert count > 0
    assert count < 50  # Should be reasonable for short message

@pytest.mark.asyncio
async def test_count_message_tokens_empty():
    """Test token counting for empty messages."""
    message = {"role": "", "content": ""}
    count = await token_counter_service.count_message_tokens(message)
    assert count >= 1  # Should have at least 1 token

@pytest.mark.asyncio
async def test_count_total_tokens():
    """Test token counting for multiple messages."""
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there! How can I help?"},
        {"role": "user", "content": "What's the weather like?"}
    ]
    
    total = await token_counter_service.count_total_tokens(messages)
    assert isinstance(total, int)
    assert total > 0
    
    # Should be sum of individual counts
    individual_sum = 0
    for message in messages:
        individual_sum += await token_counter_service.count_message_tokens(message)
    
    assert total == individual_sum

@pytest.mark.asyncio
async def test_count_tokens_with_invalid_data():
    """Test token counting handles invalid data gracefully."""
    invalid_message = {"invalid": "data"}
    count = await token_counter_service.count_message_tokens(invalid_message)
    assert isinstance(count, int)
    assert count >= 1  # Should fallback gracefully
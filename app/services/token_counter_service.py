import logging
from typing import Any, Dict, List

import tiktoken

logger = logging.getLogger(__name__)

class TokenCounterService:
    def __init__(self):
        self.encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
    
    async def count_message_tokens(self, message: Dict[str, Any]) -> int:
        """Count tokens in a message dictionary."""
        try:
            content = str(message.get("content", ""))
            role = str(message.get("role", ""))
            
            # Format similar to OpenAI chat format for accurate counting
            formatted = f"{role}: {content}"
            return len(self.encoding.encode(formatted))
        except Exception as e:
            logger.error(f"Error counting tokens for message: {e}")
            # Fallback: rough estimation (4 chars = 1 token)
            content_len = len(str(message.get("content", "")))
            return max(1, content_len // 4)
    
    async def count_total_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Count total tokens across multiple messages."""
        total = 0
        for message in messages:
            total += await self.count_message_tokens(message)
        return total

token_counter_service = TokenCounterService()
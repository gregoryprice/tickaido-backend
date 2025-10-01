#!/usr/bin/env python3
"""
AIService - LLM-based content analysis using the existing ai_config.yaml configuration
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.config.settings import get_settings
from app.services.ai_config_service import AIConfigService

logger = logging.getLogger(__name__)


@dataclass
class TicketAnalysisResult:
    suggested_category: str
    suggested_priority: str
    suggested_subcategory: Optional[str] = None
    suggested_department: Optional[str] = None
    confidence: float = 0.0
    reasoning: str = ""
    keywords: List[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.tags is None:
            self.tags = []


class AIAnalysisService:
    """LLM-based content analysis using ai_config.yaml providers"""
    
    def __init__(self):
        self.settings = get_settings()
        self.ai_config_service = AIConfigService()
        ai_config = self.ai_config_service.load_config()
        self.ai_config = ai_config
        self.llm_client = self._initialize_llm_client()
    
    def _initialize_llm_client(self):
        """Initialize LLM client based on ai_config.yaml settings"""
        # Use existing AI configuration for consistency with other services
        content_config = self.ai_config.get("content_analysis", {})
        primary_provider = content_config.get("primary_provider", "openai")
        
        if primary_provider == "openai":
            return {
                "provider": "openai",
                "api_key": self.settings.openai_api_key,
                "model": content_config.get("openai", {}).get("model", "gpt-4"),
                "max_tokens": content_config.get("openai", {}).get("max_tokens", 2000)
            }
        elif primary_provider == "google":
            return {
                "provider": "google",
                "api_key": getattr(self.settings, 'gemini_api_key', None),
                "model": content_config.get("google", {}).get("model", "gemini-pro"),
                "max_tokens": content_config.get("google", {}).get("max_tokens", 2048)
            }
        elif primary_provider == "anthropic":
            return {
                "provider": "anthropic",
                "api_key": getattr(self.settings, 'anthropic_api_key', None),
                "model": content_config.get("anthropic", {}).get("model", "claude-3-sonnet"),
                "max_tokens": content_config.get("anthropic", {}).get("max_tokens", 2000)
            }
        else:
            # Fallback to OpenAI using existing configuration
            ai_providers = self.ai_config.get("ai_providers", {})
            openai_config = ai_providers.get("openai", {})
            primary_model = openai_config.get("models", {}).get("primary", {})
            
            return {
                "provider": "openai",
                "api_key": self.settings.openai_api_key,
                "model": primary_model.get("name", "gpt-4o"),
                "max_tokens": primary_model.get("max_tokens", 2000)
            }
    
    async def generate_summary(self, content: str, max_length: int = 500) -> str:
        """Generate content summary"""
        if not content or len(content.strip()) < 10:
            return "No content to summarize"
        
        # Truncate content based on model context limits
        max_content_tokens = self._get_max_content_tokens()
        content = self._truncate_content_by_tokens(content, max_content_tokens)
        
        prompt = f"""
        Summarize the following content in {max_length} characters or less. 
        Focus on the main topics, key information, and any details relevant.
        
        Content:
        {content}
        
        Summary:
        """
        
        try:
            summary = await self._generate_text(prompt)
            # Ensure summary doesn't exceed max length
            if len(summary) > max_length:
                summary = summary[:max_length-3] + "..."
            return summary.strip()
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return f"Summary generation failed: {str(e)[:100]}"
    
    async def detect_language(self, content: str) -> str:
        """Detect content language"""
        if not content or len(content.strip()) < 5:
            return "unknown"
        
        # Simple language detection using first 500 characters
        sample_text = content[:500]
        
        prompt = f"""
        Detect the primary language of this text. Respond with only the ISO 639-1 language code (e.g., "en", "es", "fr", "de", "it", "pt", "ja", "zh", "ko", "ar").
        
        Text: {sample_text}
        
        Language code:
        """
        
        try:
            response = await self._generate_text(prompt)
            # Extract just the language code
            lang_code = response.strip().lower()[:2]
            
            # Validate it's a reasonable language code
            common_languages = ["en", "es", "fr", "de", "it", "pt", "ja", "zh", "ko", "ar", "ru", "hi"]
            if lang_code in common_languages:
                return lang_code
            else:
                return "en"  # Default to English if detection fails
        except Exception:
            return "en"  # Default fallback
    
    async def analyze_audio_content(self, transcription: str) -> Dict[str, Any]:
        """Analyze transcribed audio for sentiment and topics"""
        if not transcription or len(transcription.strip()) < 10:
            return {
                "sentiment": "neutral",
                "key_topics": [],
                "urgency_level": "low",
                "confidence": 0.0
            }
        
        prompt = f"""
        Analyze the following audio transcription.

        Provide your analysis strictly in the following JSON format:
        {{
            "sentiment": "positive|neutral|negative|frustrated|angry",
            "key_topics": ["topic1", "topic2", "topic3"],
            "urgency_level": "low|medium|high|critical",
            "confidence": 0.85,
            "language": "en|es|fr|de|other" // Use ISO 639-1 codes or 'other' if not listed
        }}
        
        Transcription: {transcription}
        
        Analysis:
        """
        
        try:
            response = await self._generate_text(prompt)
            # Parse JSON response
            analysis = json.loads(response.strip())
            
            # Validate required fields
            required_fields = ["sentiment", "key_topics", "urgency_level", "confidence", "language"]
            for field in required_fields:
                if field not in analysis:
                    analysis[field] = "unknown" if field != "confidence" else 0.0
            
            return analysis
            
        except Exception as e:
            logger.error(f"Audio content analysis failed: {e}")
            return {
                "sentiment": "neutral",
                "key_topics": ["analysis_failed"],
                "urgency_level": "medium",
                "confidence": 0.0,
                "language": "unknown"
            }
    
    async def analyze_ticket_with_attachments(
        self, 
        title: str, 
        description: str, 
        attachments: List[Dict[str, Any]]
    ) -> TicketAnalysisResult:
        """Analyze ticket with file context for enhanced categorization"""
        
        # Build comprehensive context
        full_context = f"Title: {title}\n\nDescription: {description}\n\n"
        
        if attachments:
            full_context += "Attachments:\n"
            for i, attachment in enumerate(attachments, 1):
                full_context += f"{i}. {attachment['filename']} ({attachment['type']})\n"
                if attachment.get('content'):
                    # Include first 1000 chars of content
                    content_preview = attachment['content'][:1000]
                    full_context += f"   Content: {content_preview}\n"
                if attachment.get('summary'):
                    full_context += f"   Summary: {attachment['summary']}\n"
                full_context += "\n"
        
        prompt = f"""
        Analyze this support ticket with its attachments and provide enhanced categorization.
        
        Respond in this exact JSON format:
        {{
            "suggested_category": "technical|billing|feature_request|bug|user_access|general|integration|performance|security",
            "suggested_priority": "low|medium|high|critical",
            "suggested_subcategory": "specific subcategory",
            "suggested_department": "department name",
            "confidence": 0.85,
            "reasoning": "Explanation of categorization decisions",
            "keywords": ["keyword1", "keyword2", "keyword3"],
            "tags": ["tag1", "tag2"]
        }}
        
        Ticket Context:
        {full_context}
        
        Analysis:
        """
        
        try:
            response = await self._generate_text(prompt)
            analysis = json.loads(response.strip())
            
            return TicketAnalysisResult(
                suggested_category=analysis.get("suggested_category", "general"),
                suggested_priority=analysis.get("suggested_priority", "medium"),
                suggested_subcategory=analysis.get("suggested_subcategory"),
                suggested_department=analysis.get("suggested_department"),
                confidence=float(analysis.get("confidence", 0.5)),
                reasoning=analysis.get("reasoning", ""),
                keywords=analysis.get("keywords", []),
                tags=analysis.get("tags", [])
            )
            
        except Exception as e:
            logger.error(f"Ticket analysis failed: {e}")
            return TicketAnalysisResult(
                suggested_category="general",
                suggested_priority="medium",
                confidence=0.0,
                reasoning=f"Analysis failed: {str(e)}"
            )
    
    async def _generate_text(self, prompt: str) -> str:
        """Generate text using the configured LLM client"""
        provider = self.llm_client["provider"]
        
        if provider == "openai":
            return await self._call_openai(prompt)
        elif provider == "google":
            return await self._call_google(prompt)
        elif provider == "anthropic":
            return await self._call_anthropic(prompt)
        else:
            raise ValueError(f"Unknown AI provider: {provider}")
    
    async def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API"""
        import openai
        
        client = openai.AsyncOpenAI(api_key=self.llm_client["api_key"])
        
        response = await client.chat.completions.create(
            model=self.llm_client["model"],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=self.llm_client["max_tokens"]
        )
        
        return response.choices[0].message.content
    
    async def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic Claude API"""
        import anthropic
        
        client = anthropic.AsyncAnthropic(api_key=self.llm_client["api_key"])
        
        response = await client.messages.create(
            model=self.llm_client["model"],
            max_tokens=self.llm_client["max_tokens"],
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text
    
    def _get_max_content_tokens(self) -> int:
        """Get maximum tokens available for content based on model and completion requirements"""
        model = self.llm_client.get("model", "gpt-4")
        max_completion_tokens = self.llm_client.get("max_tokens", 2000)
        
        # Model context limits
        model_limits = {
            "gpt-4": 8192,
            "gpt-4o": 128000,
            "gpt-3.5-turbo": 16385,
            "gemini-pro": 30720,
            "claude-3-sonnet": 200000,
            "claude-3-opus": 200000
        }
        
        # Get context limit for the model (default to conservative 8K)
        context_limit = model_limits.get(model, 8192)
        
        # Reserve tokens for prompt structure, completion, and safety margin
        prompt_overhead = 200  # For prompt template
        safety_margin = 200    # Safety buffer
        
        available_tokens = context_limit - max_completion_tokens - prompt_overhead - safety_margin
        return max(1000, available_tokens)  # Ensure minimum viable content
    
    def _truncate_content_by_tokens(self, content: str, max_tokens: int) -> str:
        """Truncate content to fit within token limit using tiktoken for accurate counting"""
        try:
            import tiktoken
            
            # Get encoding for the model
            model = self.llm_client.get("model", "gpt-4")
            if model.startswith("gpt-4"):
                encoding = tiktoken.encoding_for_model("gpt-4")
            elif model.startswith("gpt-3.5"):
                encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
            else:
                # Fallback to cl100k_base for most modern models
                encoding = tiktoken.get_encoding("cl100k_base")
            
            # Count tokens
            tokens = encoding.encode(content)
            
            if len(tokens) <= max_tokens:
                return content
            
            # Truncate and decode back to text
            truncated_tokens = tokens[:max_tokens]
            truncated_content = encoding.decode(truncated_tokens)
            
            return truncated_content + "... [truncated due to length]"
            
        except Exception as e:
            logger.warning(f"Token counting failed, falling back to character truncation: {e}")
            # Fallback to conservative character-based truncation
            # Rough estimate: 1 token ≈ 3.5 characters for English text
            max_chars = int(max_tokens * 3.5)
            if len(content) > max_chars:
                return content[:max_chars] + "... [truncated due to length]"
            return content
    
    async def _call_google(self, prompt: str) -> str:
        """Call Google Gemini API - placeholder implementation"""
        # This would require Google AI Platform SDK implementation
        # For now, return a placeholder response
        return f"Google Gemini analysis: {prompt[:100]}..."
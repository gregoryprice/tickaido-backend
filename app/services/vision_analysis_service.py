#!/usr/bin/env python3
"""
VisionAnalysisService - Analyze images using computer vision and AI models
"""

import base64
import logging
import re
from typing import Dict, Any, List
from PIL import Image
from io import BytesIO

from app.config.settings import get_settings
from app.services.ai_config_service import AIConfigService

logger = logging.getLogger(__name__)


class VisionAnalysisService:
    """Computer vision analysis using AI models"""
    
    def __init__(self):
        self.settings = get_settings()
        self.ai_config_service = AIConfigService()
        # Uses ai_config.yaml to determine which vision API to use
        ai_config = self.ai_config_service.load_config()
        self.ai_config = ai_config
        self.vision_client = self._initialize_vision_client()
    
    def _initialize_vision_client(self):
        """Initialize vision client based on ai_config.yaml"""
        ai_config = self.ai_config
        primary_provider = ai_config.get("vision", {}).get("primary_provider", "openai")
        
        if primary_provider == "openai":
            return self._get_openai_config(ai_config)
        elif primary_provider == "google":
            return self._get_google_config(ai_config)
        elif primary_provider == "claude":
            return self._get_claude_config(ai_config)
        else:
            raise ValueError(f"Unsupported vision provider: {primary_provider}")
    
    def _get_openai_config(self, ai_config: Dict[str, Any]) -> Dict[str, Any]:
        """Get OpenAI vision configuration"""
        return {
            "provider": "openai",
            "api_key": self.settings.openai_api_key,
            "model": ai_config.get("vision", {}).get("openai", {}).get("model", "gpt-4-vision-preview")
        }
    
    def _get_google_config(self, ai_config: Dict[str, Any]) -> Dict[str, Any]:
        """Get Google vision configuration"""
        return {
            "provider": "google",
            "api_key": getattr(self.settings, 'google_vision_api_key', None),
            "model": ai_config.get("vision", {}).get("google", {}).get("model", "gemini-pro-vision")
        }
    
    def _get_claude_config(self, ai_config: Dict[str, Any]) -> Dict[str, Any]:
        """Get Claude vision configuration"""
        return {
            "provider": "claude",
            "api_key": getattr(self.settings, 'anthropic_api_key', None),
            "model": ai_config.get("vision", {}).get("anthropic", {}).get("model", "claude-3-opus")
        }
    
    async def analyze_image(self, image_content: bytes, features: List[str]) -> Dict[str, Any]:
        """
        Analyze image with specified features (DESCRIPTION, OBJECTS, TEXT, METADATA)
        
        Args:
            image_content: Raw image bytes
            features: List of analysis features to perform
            
        Returns:
            Dictionary with analysis results based on requested features
        """
        
        # Encode image for API
        image_b64 = base64.b64encode(image_content).decode('utf-8')
        
        # Get image metadata
        image = Image.open(BytesIO(image_content))
        metadata = {
            "width": image.width,
            "height": image.height,
            "format": image.format,
            "mode": image.mode,
            "size_bytes": len(image_content)
        }
        
        analysis_result = {
            "metadata": metadata,
            "method": f"vision_{self.ai_config.get('vision', {}).get('primary_provider', 'unknown')}"
        }
        
        # Build analysis prompt based on requested features
        prompt_parts = []
        
        if "DESCRIPTION" in features:
            prompt_parts.append(
                "Provide a thorough description of this image. If the image is a screenshot or technical diagram, describe the overall layout, the main sections or panels, and any notable visual features. Include details about the type of platform or system (if identifiable), the context or purpose of the interface, and any visible workflows or processes. If the image is not a technical screenshot, describe the main subjects, setting, and any significant visual elements."
            )
        
        if "OBJECTS" in features:
            prompt_parts.append(
                "Identify and list all visible objects and elements in the image. For technical screenshots or platform interfaces, include user interface components such as buttons, menus, icons, toolbars, dialogs, forms, input fields, tables, charts, navigation bars, and any interactive or graphical controls. Also, note any system messages, notifications, or status indicators. For non-technical images, list all distinguishable items, shapes, or figures present."
            )
        
        if "TEXT" in features:
            prompt_parts.append(
                "Extract and transcribe all readable text visible in the image. For technical screenshots, include window titles, menu items, button labels, field names, error or status messages, tooltips, and any other on-screen text. For other images, transcribe any visible signs, captions, or labels."
            )
        
        if not prompt_parts:
            prompt_parts.append("If the image is a screenshot of a software platform or technical system, analyze the possible function or purpose of the interface. Describe how a user might interact with the elements, what actions are likely available, and any workflows or processes suggested by the layout. Mention any indications of user roles, permissions, or system states if visible")
        
        full_prompt = " ".join(prompt_parts)
        
        # Call vision API
        logger.info(f"DEBUG: Calling vision API with prompt: {full_prompt}")
        vision_response = await self._call_vision_api(image_b64, full_prompt)
        logger.info(f"DEBUG: Vision API response: {vision_response}")
        # Parse response based on requested features
        if "DESCRIPTION" in features:
            analysis_result["description"] = vision_response
        
        if "OBJECTS" in features:
            # Extract object mentions from response
            objects = self._extract_objects_from_response(vision_response)
            analysis_result["objects"] = objects
        
        if "TEXT" in features:
            # Extract text mentions from response  
            extracted_text = self._extract_text_from_response(vision_response)
            analysis_result["extracted_text"] = extracted_text
        
        # Overall confidence (vision models typically don't provide this, so estimate)
        analysis_result["confidence"] = 0.85 if len(vision_response) > 20 else 0.6
        
        return analysis_result
    
    async def _call_vision_api(self, image_b64: str, prompt: str) -> str:
        """Call the configured vision API"""
        provider = self.vision_client["provider"]
        
        if provider == "openai":
            return await self._call_openai_vision(image_b64, prompt)
        elif provider == "google":
            return await self._call_google_vision(image_b64, prompt)
        elif provider == "claude":
            return await self._call_claude_vision(image_b64, prompt)
        else:
            raise ValueError(f"Unknown vision provider: {provider}")
    
    async def _call_openai_vision(self, image_b64: str, prompt: str) -> str:
        """Call OpenAI Vision API"""
        import openai
        
        client = openai.AsyncOpenAI(api_key=self.vision_client["api_key"])
        
        response = await client.chat.completions.create(
            model=self.vision_client["model"],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        
        return response.choices[0].message.content
    
    async def _call_claude_vision(self, image_b64: str, prompt: str) -> str:
        """Call Claude Vision API"""
        import anthropic
        
        client = anthropic.AsyncAnthropic(api_key=self.vision_client["api_key"])
        
        response = await client.messages.create(
            model=self.vision_client["model"],
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_b64
                            }
                        }
                    ]
                }
            ]
        )
        
        return response.content[0].text
    
    async def _call_google_vision(self, image_b64: str, prompt: str) -> str:
        """Call Google Vision API - placeholder implementation"""
        # This would require Google AI Platform SDK implementation
        # For now, return a placeholder response
        return f"Google Vision analysis of image with prompt: {prompt[:100]}..."
    
    def _extract_objects_from_response(self, response: str) -> List[str]:
        """Extract object/UI element mentions from vision response"""
        
        # Common UI/technical objects to look for
        ui_objects = [
            "button", "dialog", "window", "menu", "form", "input", "field", "text box",
            "dropdown", "checkbox", "radio button", "tab", "panel", "toolbar", "header",
            "footer", "sidebar", "navigation", "search box", "login", "error message",
            "warning", "notification", "popup", "modal", "alert"
        ]
        
        found_objects = []
        response_lower = response.lower()
        
        for obj in ui_objects:
            if obj in response_lower:
                found_objects.append(obj)
        
        return list(set(found_objects))  # Remove duplicates
    
    def _extract_text_from_response(self, response: str) -> str:
        """Extract mentioned text content from vision response"""
        
        # Look for quoted text or "text reads" patterns
        quoted_text = re.findall(r'"([^"]*)"', response)
        text_reads = re.findall(r'text reads?[:\s]+"([^"]*)"', response, re.IGNORECASE)
        says_patterns = re.findall(r'says?[:\s]+"([^"]*)"', response, re.IGNORECASE)
        
        all_text = quoted_text + text_reads + says_patterns
        return " | ".join(all_text) if all_text else ""
    
    async def detect_objects(self, image_content: bytes) -> List[str]:
        """Detect objects in image"""
        result = await self.analyze_image(image_content, ["OBJECTS"])
        return result.get("objects", [])
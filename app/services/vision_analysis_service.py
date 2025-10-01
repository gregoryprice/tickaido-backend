#!/usr/bin/env python3
"""
VisionAnalysisService - Analyze images using computer vision and AI models
"""

import base64
import logging
import re
import xml.etree.ElementTree as ET
from io import BytesIO
from typing import Any, Dict, List

from PIL import Image

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
        
        # Handle SVG files specially as they cannot be opened by PIL directly
        is_svg = self._is_svg_content(image_content)
        
        if is_svg:
            # For SVG files, convert to PNG first
            image_content = self._convert_svg_to_png(image_content)
        
        # Encode image for API
        image_b64 = base64.b64encode(image_content).decode('utf-8')
        
        # Get image metadata
        try:
            image = Image.open(BytesIO(image_content))
            metadata = {
                "width": image.width,
                "height": image.height,
                "format": image.format if not is_svg else "SVG",
                "mode": image.mode,
                "size_bytes": len(image_content),
                "original_format": "SVG" if is_svg else image.format
            }
        except Exception as e:
            logger.error(f"Failed to open image with PIL: {e}")
            # Fallback metadata for problematic images
            metadata = {
                "width": 0,
                "height": 0,
                "format": "SVG" if is_svg else "Unknown",
                "mode": "Unknown",
                "size_bytes": len(image_content),
                "error": str(e)
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
    
    def _is_svg_content(self, content: bytes) -> bool:
        """Check if content is SVG by looking for SVG elements"""
        try:
            # Decode bytes to string for XML parsing
            content_str = content.decode('utf-8', errors='ignore')
            
            # Check for SVG root element
            if '<svg' in content_str.lower() or content_str.strip().startswith('<?xml'):
                try:
                    # Try to parse as XML to confirm it's valid SVG
                    root = ET.fromstring(content_str)
                    return root.tag.lower().endswith('svg') or 'svg' in root.tag.lower()
                except ET.ParseError:
                    # If XML parsing fails, check for SVG string presence
                    return '<svg' in content_str.lower()
            return False
        except Exception:
            return False
    
    def _convert_svg_to_png(self, svg_content: bytes) -> bytes:
        """Convert SVG content to PNG bytes using cairosvg"""
        try:
            # Try to import cairosvg for SVG conversion
            try:
                import cairosvg
                png_bytes = cairosvg.svg2png(bytestring=svg_content)
                logger.info("Successfully converted SVG to PNG using cairosvg")
                return png_bytes
            except ImportError:
                logger.warning("cairosvg not available, falling back to PIL conversion attempt")
                # Fallback: Create a simple text-based representation
                return self._create_svg_fallback_image(svg_content)
                
        except Exception as e:
            logger.error(f"Failed to convert SVG to PNG: {e}")
            # Create a fallback image that indicates SVG content
            return self._create_svg_fallback_image(svg_content)
    
    def _create_svg_fallback_image(self, svg_content: bytes) -> bytes:
        """Create a fallback PNG image for SVG files that can't be converted"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a simple image indicating SVG content
            width, height = 400, 300
            img = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(img)
            
            # Draw text indicating this is an SVG file
            try:
                # Try to use a default font
                font = ImageFont.load_default()
            except:
                font = None
            
            text_lines = [
                "SVG File",
                "Vector Graphics Content",
                f"Size: {len(svg_content)} bytes"
            ]
            
            y_offset = height // 2 - 30
            for line in text_lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x_offset = (width - text_width) // 2
                draw.text((x_offset, y_offset), line, fill='black', font=font)
                y_offset += 25
            
            # Save to bytes
            output = BytesIO()
            img.save(output, format='PNG')
            output.seek(0)
            
            logger.info("Created fallback PNG image for SVG content")
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to create SVG fallback image: {e}")
            # Final fallback: create a minimal 1x1 PNG
            return self._create_minimal_png()
    
    def _create_minimal_png(self) -> bytes:
        """Create a minimal 1x1 white PNG as ultimate fallback"""
        try:
            from PIL import Image
            img = Image.new('RGB', (1, 1), color='white')
            output = BytesIO()
            img.save(output, format='PNG')
            output.seek(0)
            logger.info("Created minimal 1x1 PNG as final fallback")
            return output.getvalue()
        except Exception as e:
            logger.error(f"Failed to create minimal PNG: {e}")
            # Return a hardcoded minimal PNG if all else fails
            # This is a 1x1 white PNG encoded in bytes
            return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xdd\x8d\xb4\x1c\x00\x00\x00\x00IEND\xaeB`\x82'
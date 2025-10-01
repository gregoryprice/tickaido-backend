#!/usr/bin/env python3
"""
OCRService - Extract text from images using Optical Character Recognition
Uses Tesseract (free, local) with Google Vision API fallback.
"""

import logging
import xml.etree.ElementTree as ET
from io import BytesIO
from typing import Any, Dict

from PIL import Image

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class OCRService:
    """Text extraction from images using OCR"""
    
    def __init__(self):
        self.settings = get_settings()
        # Primary: Tesseract (free, local)
        # Fallback: Google Vision API (paid, cloud)
        
    async def extract_text_with_regions(self, image_content: bytes) -> Dict[str, Any]:
        """
        Extract text with bounding boxes and confidence scores
        
        Args:
            image_content: Raw image bytes
            
        Returns:
            Dictionary with text regions, bounding boxes, and confidence scores
        """
        # Handle SVG files by converting to PNG first
        is_svg = self._is_svg_content(image_content)
        if is_svg:
            logger.info("Converting SVG to PNG for OCR processing")
            image_content = self._convert_svg_to_png(image_content)
        
        try:
            # Try Tesseract first (free, local)
            return await self._extract_with_tesseract(image_content)
        except Exception as e:
            logger.warning(f"Tesseract OCR failed: {e}, falling back to Google Vision")
            # Fallback to Google Vision API if available
            if hasattr(self.settings, 'google_vision_api_key') and self.settings.google_vision_api_key:
                return await self._extract_with_google_vision(image_content)
            else:
                raise Exception("OCR extraction failed and no fallback available")
    
    async def _extract_with_tesseract(self, image_content: bytes) -> Dict[str, Any]:
        """Extract text using Tesseract OCR"""
        
        if not HAS_TESSERACT:
            raise Exception("Tesseract not available - install pytesseract package")
        
        # Load image
        image = Image.open(BytesIO(image_content))
        
        # Extract text with detailed data
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        
        # Process OCR results
        text_regions = []
        full_text = []
        
        for i in range(len(data['text'])):
            if int(data['conf'][i]) > 30:  # Confidence threshold
                text = data['text'][i].strip()
                if text:
                    text_regions.append({
                        "text": text,
                        "confidence": float(data['conf'][i]) / 100.0,
                        "geometry": {
                            "x": data['left'][i],
                            "y": data['top'][i], 
                            "width": data['width'][i],
                            "height": data['height'][i]
                        },
                        "block_num": data['block_num'][i],
                        "line_num": data['line_num'][i],
                        "word_num": data['word_num'][i]
                    })
                    full_text.append(text)
        
        return {
            "text_regions": text_regions,
            "full_text": " ".join(full_text),
            "method": "tesseract",
            "total_confidence": sum([r["confidence"] for r in text_regions]) / max(len(text_regions), 1)
        }
    
    async def _extract_with_google_vision(self, image_content: bytes) -> Dict[str, Any]:
        """Extract text using Google Vision API"""
        from google.cloud import vision
        
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_content)
        
        # Detect text
        response = client.text_detection(image=image)
        texts = response.text_annotations
        
        if response.error.message:
            raise Exception(f"Google Vision API error: {response.error.message}")
        
        text_regions = []
        full_text = ""
        
        if texts:
            full_text = texts[0].description  # First annotation is full text
            
            # Process individual text regions
            for text in texts[1:]:  # Skip first (full text)
                vertices = text.bounding_poly.vertices
                
                # Calculate bounding box
                x_coords = [v.x for v in vertices]
                y_coords = [v.y for v in vertices]
                
                text_regions.append({
                    "text": text.description,
                    "confidence": 0.95,  # Google Vision doesn't provide confidence per word
                    "geometry": {
                        "x": min(x_coords),
                        "y": min(y_coords),
                        "width": max(x_coords) - min(x_coords),
                        "height": max(y_coords) - min(y_coords)
                    }
                })
        
        return {
            "text_regions": text_regions,
            "full_text": full_text,
            "method": "google_vision",
            "total_confidence": 0.95
        }
    
    async def extract_text_from_image(self, image_content: bytes) -> str:
        """Simple text extraction from image"""
        result = await self.extract_text_with_regions(image_content)
        return result["full_text"]
    
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
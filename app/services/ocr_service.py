#!/usr/bin/env python3
"""
OCRService - Extract text from images using Optical Character Recognition
Uses Tesseract (free, local) with Google Vision API fallback.
"""

import logging
from typing import Dict, Any
from PIL import Image
from io import BytesIO

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
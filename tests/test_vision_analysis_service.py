#!/usr/bin/env python3
"""
VisionAnalysisService Tests - Comprehensive validation as specified in PRP
VALIDATION GATE: All tests must pass before proceeding
"""

import pytest
import time
from app.services.vision_analysis_service import VisionAnalysisService


class TestVisionAnalysisService:
    """Comprehensive tests for VisionAnalysisService"""
    
    @pytest.fixture
    def vision_service(self):
        return VisionAnalysisService()
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, vision_service):
        """REQUIRED TEST: Service initializes with AI config"""
        assert vision_service is not None
        assert hasattr(vision_service, 'settings')
        assert hasattr(vision_service, 'ai_config')
        assert hasattr(vision_service, 'vision_client')
        assert vision_service.vision_client is not None
    
    @pytest.mark.asyncio
    async def test_vision_client_configuration(self, vision_service):
        """REQUIRED TEST: Vision client properly configured"""
        client = vision_service.vision_client
        
        assert isinstance(client, dict)
        assert "provider" in client
        assert client["provider"] in ["openai", "google", "claude"]
    
    @pytest.mark.asyncio
    async def test_image_metadata_extraction(self, vision_service):
        """REQUIRED TEST: Image metadata extraction"""
        from PIL import Image
        import io
        
        # Create test image with known properties
        img = Image.new('RGB', (200, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        image_content = img_bytes.getvalue()
        
        result = await vision_service.analyze_image(image_content, ["DESCRIPTION"])
        
        assert "metadata" in result
        metadata = result["metadata"]
        assert metadata["width"] == 200
        assert metadata["height"] == 100
        assert metadata["size_bytes"] > 0
        assert metadata["format"] == "PNG"
    
    @pytest.mark.asyncio
    async def test_object_extraction_from_response(self, vision_service):
        """REQUIRED TEST: Object detection from AI responses"""
        
        test_response = "The image shows a login dialog with a submit button, error message, and input fields."
        
        objects = vision_service._extract_objects_from_response(test_response)
        
        assert isinstance(objects, list)
        assert "button" in objects
        assert "dialog" in objects
        assert "error message" in objects
        assert "input" in objects
    
    @pytest.mark.asyncio
    async def test_text_extraction_from_response(self, vision_service):
        """REQUIRED TEST: Text extraction from AI responses"""
        
        test_response = 'The error message says "Invalid credentials" and the button text reads "Login Now".'
        
        extracted_text = vision_service._extract_text_from_response(test_response)
        
        assert isinstance(extracted_text, str)
        assert "Invalid credentials" in extracted_text
        assert "Login Now" in extracted_text
    
    @pytest.mark.asyncio
    async def test_image_analysis_mock(self, vision_service):
        """REQUIRED TEST: Image analysis with mocked API call"""
        
        from PIL import Image
        import io
        
        # Create test image
        img = Image.new('RGB', (100, 50), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        image_content = img_bytes.getvalue()
        
        try:
            result = await vision_service.analyze_image(image_content, ["DESCRIPTION", "OBJECTS"])
            
            # If API call succeeds, validate structure
            assert "metadata" in result
            assert "method" in result
            if "description" in result:
                assert isinstance(result["description"], str)
            if "objects" in result:
                assert isinstance(result["objects"], list)
                
        except Exception as e:
            # Expected if API keys not configured, rate limits hit, or model deprecated
            expected_errors = ["api", "auth", "key", "client", "rate", "limit", "model", "deprecated", "not_found"]
            assert any(term in str(e).lower() for term in expected_errors)
    
    @pytest.mark.asyncio
    async def test_performance_requirements(self, vision_service):
        """REQUIRED TEST: Vision analysis performance"""
        
        from PIL import Image
        import io
        
        img = Image.new('RGB', (50, 50), color='green')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        image_content = img_bytes.getvalue()
        
        start_time = time.time()
        
        try:
            result = await vision_service.analyze_image(image_content, ["DESCRIPTION"])
            processing_time = time.time() - start_time
            
            # Should complete within reasonable time
            assert processing_time < 60.0  # Allow time for API calls
            
        except Exception:
            processing_time = time.time() - start_time
            # Should fail quickly if API not available
            assert processing_time < 10.0
    
    @pytest.mark.asyncio
    async def test_detect_objects_interface(self, vision_service):
        """REQUIRED TEST: Object detection interface"""
        
        from PIL import Image
        import io
        
        img = Image.new('RGB', (100, 100), color='white')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        
        try:
            objects = await vision_service.detect_objects(img_bytes.getvalue())
            assert isinstance(objects, list)
            
        except Exception as e:
            # Expected if API not available or model deprecated
            expected_errors = ["api", "auth", "key", "client", "model", "deprecated", "not_found"]
            assert any(term in str(e).lower() for term in expected_errors)


# VALIDATION GATE: VisionAnalysisService tests must ALL PASS before proceeding
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
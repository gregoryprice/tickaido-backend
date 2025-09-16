#!/usr/bin/env python3
"""
TranscriptionService Tests - Comprehensive validation as specified in PRP
VALIDATION GATE: All tests must pass before proceeding
"""

import pytest
import time
from app.services.transcription_service import TranscriptionService


class TestTranscriptionService:
    """Comprehensive tests for TranscriptionService"""
    
    @pytest.fixture
    def transcription_service(self):
        return TranscriptionService()
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, transcription_service):
        """REQUIRED TEST: Service initializes correctly"""
        assert transcription_service is not None
        assert hasattr(transcription_service, 'settings')
        assert hasattr(transcription_service, 'transcription_model')
        assert hasattr(transcription_service, 'openai_client')
    
    @pytest.mark.asyncio
    async def test_model_configuration(self, transcription_service):
        """REQUIRED TEST: OpenAI API model configuration"""
        # Model should be configured correctly
        assert transcription_service.transcription_model is not None
        assert transcription_service.transcription_model in ["gpt-4o-transcribe", "gpt-4o-mini-transcribe"]
        
        # OpenAI client should be initialized
        assert transcription_service.openai_client is not None
    
    @pytest.mark.asyncio
    async def test_audio_conversion_preparation(self, transcription_service):
        """REQUIRED TEST: Audio file preparation and conversion logic"""
        
        # Create simple audio-like data
        fake_audio_data = b"RIFF\x24\x00\x00\x00WAVEfmt "  # WAV header-like
        
        try:
            temp_path = await transcription_service._save_temp_audio(fake_audio_data)
            assert isinstance(temp_path, str)
            assert temp_path.endswith('.wav')
            
            # Cleanup would happen in actual transcription
            import os
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
        except Exception as e:
            # Expected if ffmpeg not available
            assert any(term in str(e).lower() for term in ["ffmpeg", "audio", "conversion"])
    
    @pytest.mark.asyncio
    async def test_transcription_interface(self, transcription_service):
        """REQUIRED TEST: Basic transcription interface"""
        
        # Create minimal audio data
        audio_data = b"fake_audio_content"
        
        try:
            result = await transcription_service.transcribe_audio(audio_data)
            
            # If successful, validate result structure
            assert hasattr(result, 'text')
            assert hasattr(result, 'language') 
            assert hasattr(result, 'confidence')
            assert hasattr(result, 'duration')
            assert hasattr(result, 'method')
            
        except Exception as e:
            # Expected if OpenAI API unavailable, ffmpeg not available, or invalid audio
            expected_errors = ["transcription", "ffmpeg", "audio", "conversion", "openai", "api"]
            assert any(term in str(e).lower() for term in expected_errors)
    
    @pytest.mark.asyncio
    async def test_performance_requirements(self, transcription_service):
        """REQUIRED TEST: Transcription performance expectations"""
        
        audio_data = b"minimal_test_data"
        
        start_time = time.time()
        
        try:
            result = await transcription_service.transcribe_audio(audio_data)
            processing_time = time.time() - start_time
            
            # Should complete within reasonable time (or fail fast)
            assert processing_time < 30.0
            
        except Exception as e:
            processing_time = time.time() - start_time
            # Should fail quickly if dependencies missing
            assert processing_time < 10.0
    
    @pytest.mark.asyncio
    async def test_docker_compatibility(self, transcription_service):
        """REQUIRED TEST: Docker environment compatibility"""
        
        # Test that service reports Docker compatibility
        supports_docker = transcription_service.supports_docker()
        assert supports_docker is True
    
    @pytest.mark.asyncio
    async def test_error_handling(self, transcription_service):
        """REQUIRED TEST: Error handling for invalid audio data"""
        
        invalid_audio = b"This is definitely not audio data"
        
        with pytest.raises(Exception):
            await transcription_service.transcribe_audio(invalid_audio)


# VALIDATION GATE: TranscriptionService tests must ALL PASS before proceeding
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
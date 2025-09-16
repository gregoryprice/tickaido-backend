#!/usr/bin/env python3
"""
TranscriptionService - Transcribe audio and video files using OpenAI API
"""

import os
import tempfile
import subprocess
import uuid
from typing import Dict, Any
from dataclasses import dataclass
import logging

from openai import AsyncOpenAI
from app.config.settings import get_settings
from app.services.ai_config_service import AIConfigService

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    text: str
    language: str
    confidence: float
    duration: float
    method: str


class TranscriptionService:
    """Audio/video transcription using OpenAI API"""
    
    def __init__(self):
        self.settings = get_settings()
        self.ai_config_service = AIConfigService()
        
        # Initialize OpenAI client
        self.openai_client = AsyncOpenAI(
            api_key=self.settings.openai_api_key
        )
        
        # Model selection from config
        ai_config = self.ai_config_service.load_config()
        self.transcription_model = ai_config.get("transcription", {}).get("model", "gpt-4o-mini-transcribe")
        
        # Validate model choice
        if self.transcription_model not in ["gpt-4o-transcribe", "gpt-4o-mini-transcribe"]:
            logger.warning(f"Invalid transcription model {self.transcription_model}, falling back to gpt-4o-mini-transcribe")
            self.transcription_model = "gpt-4o-mini-transcribe"
    
    async def transcribe_with_segments(self, audio_content: bytes) -> Dict[str, Any]:
        """
        Transcribe audio with timestamp segments using OpenAI API
        
        Args:
            audio_content: Raw audio bytes
            
        Returns:
            Dictionary with full transcription, segments, and metadata
        """
        # Save temporary audio file
        temp_path = await self._save_temp_audio(audio_content)
        
        try:
            # Prepare file for OpenAI API
            with open(temp_path, "rb") as audio_file:
                # Use appropriate parameters based on model
                transcription = await self.openai_client.audio.transcriptions.create(
                    model=self.transcription_model,
                    file=audio_file,
                    response_format="json"
                )
            
            # Process the response based on model capabilities
            if hasattr(transcription, 'segments') and transcription.segments:
                segments = []
                for segment in transcription.segments:
                    segments.append({
                        "start": segment.get("start", 0),
                        "end": segment.get("end", 0),
                        "text": segment.get("text", "").strip(),
                        "confidence": segment.get("avg_logprob", -0.5)
                    })
                
                # Calculate overall confidence (convert log prob to 0-1 scale)
                avg_logprob = getattr(transcription, 'avg_logprob', -1.0)
                confidence = max(0.0, min(1.0, (avg_logprob + 3.0) / 3.0))
                
                duration = segments[-1]["end"] if segments else 0.0
                language = getattr(transcription, 'language', 'unknown')
                
            else:
                text = transcription.text.strip()
                language = getattr(transcription, 'language', 'unknown')
                
                # Estimate confidence and duration for models without detailed metadata
                confidence = 0.85  # Default confidence for OpenAI API
                duration = self._estimate_duration(audio_content)
                
                # Create a single segment for the entire transcription
                segments = [{
                    "start": 0.0,
                    "end": duration,
                    "text": text,
                    "confidence": confidence
                }] if text else []
            
            return {
                "text": transcription.text.strip(),
                "language": language,
                "confidence": confidence,
                "duration": duration,
                "segments": segments,
                "method": f"openai_api_{self.transcription_model}"
            }
            
        except Exception as e:
            logger.error(f"OpenAI transcription failed: {e}")
            raise Exception(f"Transcription failed: {e}")
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    async def _save_temp_audio(self, audio_content: bytes) -> str:
        """Save audio content to temporary file"""
        
        # Create temp file with unique name
        temp_dir = tempfile.gettempdir()
        temp_filename = f"transcription_temp_{uuid.uuid4().hex}.wav"
        temp_path = os.path.join(temp_dir, temp_filename)
        
        # Convert to supported format if needed using ffmpeg
        await self._convert_to_supported_format(audio_content, temp_path)
        
        return temp_path
    
    async def _convert_to_supported_format(self, audio_content: bytes, output_path: str):
        """Convert audio to a format supported by OpenAI API"""
        
        # Save original file
        with tempfile.NamedTemporaryFile(delete=False) as temp_input:
            temp_input.write(audio_content)
            temp_input_path = temp_input.name
        
        try:
            # Convert to WAV format using ffmpeg (OpenAI supports mp3, mp4, mpeg, mpga, m4a, wav, webm)
            subprocess.run([
                "ffmpeg", "-i", temp_input_path,
                "-acodec", "pcm_s16le",
                "-ar", "16000",  # 16kHz sample rate
                "-ac", "1",      # Mono
                "-y",            # Overwrite output file
                output_path
            ], check=True, capture_output=True)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Audio conversion failed: {e}")
            # If conversion fails, try copying the original file
            # OpenAI API supports many formats natively
            try:
                with open(output_path, "wb") as f:
                    f.write(audio_content)
            except Exception as copy_error:
                raise Exception(f"Audio conversion and fallback failed: {copy_error}")
        finally:
            if os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
    
    def _estimate_duration(self, audio_content: bytes) -> float:
        """Estimate audio duration for models that don't provide it"""
        try:
            # Very rough estimate: assume 128 kbps MP3 encoding
            # This is just for fallback when duration isn't available
            estimated_seconds = len(audio_content) / (128 * 1024 / 8)  # 128 kbps in bytes per second
            return max(1.0, min(estimated_seconds, 1800.0))  # Cap between 1 and 1800 seconds
        except:
            return 60.0  # Default fallback
    
    async def transcribe_audio(self, audio_content: bytes, language: str = "auto") -> TranscriptionResult:
        """Basic transcription without segments"""
        result = await self.transcribe_with_segments(audio_content)
        
        return TranscriptionResult(
            text=result["text"],
            language=result["language"],
            confidence=result["confidence"],
            duration=result["duration"],
            method=result["method"]
        )
    
    def supports_docker(self) -> bool:
        """Check if service can run in Docker environment"""
        return True  # OpenAI API works in any environment with internet access
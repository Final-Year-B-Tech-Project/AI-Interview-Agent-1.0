from TTS.api import TTS
import torch
import numpy as np
import soundfile as sf
import tempfile
import os
import threading
from typing import Dict, Optional, Callable
import time

class CoquiVoiceService:
    def __init__(self):
        print("🚀 Initializing Coqui TTS Voice Service...")
        
        # Check GPU availability
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"📱 Using device: {self.device}")
        
        # Initialize TTS model
        self.tts_model = None
        self.is_speaking = False
        self.load_tts_model()
        
        # Note: Microphone functionality not implemented in this version
        print("ℹ️  Note: This version supports TTS only. Audio upload required for speech recognition.")
        print("✅ Coqui Voice Service ready!")
    
    def load_tts_model(self):
        """Load Coqui TTS model with error handling."""
        try:
            print("📥 Loading TTS model (this may take a moment on first run)...")
            
            # Use a more stable TTS model
            self.tts_model = TTS(
                model_name="tts_models/en/ljspeech/glow-tts",  # More stable model
                progress_bar=False,
                gpu=(self.device == "cuda")
            )
            
            print("✅ TTS model loaded successfully!")
            
        except Exception as e:
            print(f"❌ Error loading primary TTS model: {e}")
            print("🔄 Trying fallback model...")
            
            try:
                # Fallback to CPU-only model
                self.tts_model = TTS(
                    model_name="tts_models/en/ljspeech/speedy-speech",
                    progress_bar=False,
                    gpu=False  # Force CPU for stability
                )
                print("✅ Fallback TTS model loaded!")
                
            except Exception as e2:
                print(f"❌ Failed to load any TTS model: {e2}")
                raise
    
    def synthesize_speech(self, text: str, output_path: Optional[str] = None) -> Dict:
        """Generate speech from text with improved error handling."""
        try:
            if not self.tts_model:
                raise Exception("TTS model not loaded")
            
            # Clean and prepare text for TTS
            clean_text = self._clean_text_for_tts(text)
            print(f"🔊 Generating speech: {clean_text[:50]}...")
            
            self.is_speaking = True
            
            # Create temporary file if no output path specified
            if not output_path:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                output_path = temp_file.name
                temp_file.close()
            
            # Add professional interviewer tone
            formatted_text = f"Here's your interview question: {clean_text}"
            
            # Generate speech audio with error handling
            try:
                self.tts_model.tts_to_file(
                    text=formatted_text[:500],  # Limit text length to avoid tensor issues
                    file_path=output_path
                )
            except Exception as tts_error:
                print(f"⚠️ TTS generation warning: {tts_error}")
                # Fallback: try with shorter text
                self.tts_model.tts_to_file(
                    text=clean_text[:200],
                    file_path=output_path
                )
            
            self.is_speaking = False
            print(f"✅ Speech generated: {output_path}")
            
            return {
                "success": True,
                "audio_path": output_path,
                "text": text,
                "duration": self._get_audio_duration(output_path)
            }
            
        except Exception as e:
            self.is_speaking = False
            print(f"❌ Speech generation error: {e}")
            return {
                "success": False,
                "error": str(e),
                "audio_path": None
            }
    
    def _clean_text_for_tts(self, text: str) -> str:
        """Clean text to avoid TTS tensor dimension errors."""
        # Remove problematic characters and limit length
        clean_text = text.replace('\n', ' ').replace('\r', ' ')
        clean_text = ' '.join(clean_text.split())  # Normalize whitespace
        
        # Limit text length to prevent tensor dimension issues
        if len(clean_text) > 300:
            clean_text = clean_text[:300] + "..."
        
        return clean_text
    
    def speak_question_async(self, question_text: str, callback: Optional[Callable] = None):
        """Generate speech for interview question asynchronously."""
        def speak():
            try:
                result = self.synthesize_speech(question_text)
                
                if result["success"]:
                    print(f"🎵 Audio ready: {result['audio_path']}")
                    if callback:
                        callback(result)
                else:
                    print(f"❌ Failed to generate speech: {result['error']}")
                    
            except Exception as e:
                print(f"❌ Async speech error: {e}")
        
        # Run in separate thread to avoid blocking
        thread = threading.Thread(target=speak)
        thread.daemon = True
        thread.start()
    
    def get_status(self) -> Dict:
        """Get current voice service status."""
        return {
            "tts_loaded": self.tts_model is not None,
            "is_speaking": self.is_speaking,
            "device": self.device,
            "gpu_available": torch.cuda.is_available(),
            "microphone_available": False,  # Not implemented in this version
            "microphone_note": "Audio upload required for speech recognition"
        }
    
    def test_system(self) -> Dict:
        """Test the TTS system."""
        try:
            test_text = "This is a test of the Coqui TTS system for your AI interview agent."
            result = self.synthesize_speech(test_text)
            
            # Clean up test file
            if result.get("audio_path") and os.path.exists(result["audio_path"]):
                os.unlink(result["audio_path"])
            
            return {
                "tts_working": result["success"],
                "gpu_available": torch.cuda.is_available(),
                "device": self.device,
                "model_loaded": self.tts_model is not None,
                "microphone_working": False  # Not implemented
            }
            
        except Exception as e:
            print(f"System test failed: {e}")
            return {
                "tts_working": False,
                "gpu_available": torch.cuda.is_available(),
                "device": self.device,
                "error": str(e)
            }
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """Get duration of audio file in seconds."""
        try:
            data, samplerate = sf.read(audio_path)
            return len(data) / samplerate
        except Exception:
            return 0.0

# Create global instance
voice_service = CoquiVoiceService()

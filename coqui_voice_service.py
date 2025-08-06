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
        
        print("✅ Coqui Voice Service ready!")
    
    def load_tts_model(self):
        """Load Coqui TTS model."""
        try:
            print("📥 Loading TTS model (this may take a moment on first run)...")
            
            # Use a good English TTS model that works well on your hardware
            self.tts_model = TTS(
                model_name="tts_models/en/ljspeech/tacotron2-DDC",
                progress_bar=False,
                gpu=(self.device == "cuda")
            )
            
            print("✅ TTS model loaded successfully!")
            
        except Exception as e:
            print(f"❌ Error loading TTS model: {e}")
            print("🔄 Trying alternative model...")
            
            try:
                # Fallback to a lighter model
                self.tts_model = TTS(
                    model_name="tts_models/en/ljspeech/glow-tts",
                    progress_bar=False,
                    gpu=False  # Force CPU for compatibility
                )
                print("✅ Fallback TTS model loaded!")
                
            except Exception as e2:
                print(f"❌ Failed to load any TTS model: {e2}")
                raise
    
    def synthesize_speech(self, text: str, output_path: Optional[str] = None) -> Dict:
        """Generate speech from text using Coqui TTS."""
        try:
            if not self.tts_model:
                raise Exception("TTS model not loaded")
            
            print(f"🔊 Generating speech: {text[:50]}...")
            self.is_speaking = True
            
            # Create temporary file if no output path specified
            if not output_path:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                output_path = temp_file.name
                temp_file.close()
            
            # Add professional interviewer tone
            formatted_text = f"Here's your interview question: {text}"
            
            # Generate speech audio
            self.tts_model.tts_to_file(
                text=formatted_text,
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
    
    def list_available_models(self) -> list:
        """Get list of available TTS models."""
        try:
            models = TTS.list_models()
            english_models = [model for model in models if "en/" in model]
            return english_models[:10]  # Return top 10 English models
        except Exception as e:
            print(f"Error listing models: {e}")
            return []
    
    def get_status(self) -> Dict:
        """Get current voice service status."""
        return {
            "tts_loaded": self.tts_model is not None,
            "is_speaking": self.is_speaking,
            "device": self.device,
            "gpu_available": torch.cuda.is_available(),
            "cuda_device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0
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
                "model_loaded": self.tts_model is not None
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

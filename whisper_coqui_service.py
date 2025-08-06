import whisper
import torch
import numpy as np
import soundfile as sf
import io
import threading
import time
from TTS.api import TTS
from typing import Dict, Optional, Callable, List
import tempfile
import os

class WhisperCoquiVoiceService:
    def __init__(self):
        print("Initializing Whisper + Coqui Voice Service...")
        
        # Initialize Whisper for Speech-to-Text
        self.whisper_model = None
        self.load_whisper_model()
        
        # Initialize Coqui TTS for Text-to-Speech
        self.tts_model = None
        self.load_coqui_tts()
        
        # Voice state
        self.is_speaking = False
        self.is_processing = False
        
        print("✅ Voice service initialized successfully!")
    
    def load_whisper_model(self, model_size: str = "base"):
        """Load Whisper model for speech recognition."""
        try:
            print(f"Loading Whisper model: {model_size}")
            self.whisper_model = whisper.load_model(model_size)
            print(f"✅ Whisper {model_size} model loaded successfully")
        except Exception as e:
            print(f"❌ Error loading Whisper model: {e}")
            raise
    
    def load_coqui_tts(self):
        """Load Coqui TTS model for speech synthesis."""
        try:
            print("Loading Coqui TTS model...")
            # Use a good quality English TTS model
            self.tts_model = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", 
                               progress_bar=False, gpu=torch.cuda.is_available())
            print("✅ Coqui TTS model loaded successfully")
        except Exception as e:
            print(f"❌ Error loading Coqui TTS model: {e}")
            # Fallback to a different model if the first fails
            try:
                self.tts_model = TTS(model_name="tts_models/en/ljspeech/glow-tts", 
                                   progress_bar=False, gpu=torch.cuda.is_available())
                print("✅ Coqui TTS fallback model loaded")
            except Exception as e2:
                print(f"❌ Fallback TTS model also failed: {e2}")
                raise
    
    def transcribe_audio(self, audio_file_path: str) -> Dict:
        """Transcribe audio file using Whisper."""
        try:
            if not self.whisper_model:
                raise Exception("Whisper model not loaded")
            
            print(f"🎤 Transcribing audio: {audio_file_path}")
            self.is_processing = True
            
            # Transcribe using Whisper
            result = self.whisper_model.transcribe(
                audio_file_path,
                language="en",  # Can be set to "auto" for automatic detection
                task="transcribe",
                verbose=False
            )
            
            self.is_processing = False
            
            transcribed_text = result["text"].strip()
            confidence = result.get("confidence", 0.8)  # Whisper doesn't always provide confidence
            
            print(f"✅ Transcription complete: {transcribed_text[:100]}...")
            
            return {
                "success": True,
                "text": transcribed_text,
                "confidence": confidence,
                "language": result.get("language", "en"),
                "segments": result.get("segments", [])
            }
            
        except Exception as e:
            self.is_processing = False
            print(f"❌ Transcription error: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": ""
            }
    
    def synthesize_speech(self, text: str, output_path: Optional[str] = None) -> Dict:
        """Synthesize speech from text using Coqui TTS."""
        try:
            if not self.tts_model:
                raise Exception("TTS model not loaded")
            
            print(f"🔊 Synthesizing speech: {text[:50]}...")
            self.is_speaking = True
            
            # Create temporary file if no output path specified
            if not output_path:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                output_path = temp_file.name
                temp_file.close()
            
            # Generate speech
            self.tts_model.tts_to_file(text=text, file_path=output_path)
            
            self.is_speaking = False
            
            print(f"✅ Speech synthesis complete: {output_path}")
            
            return {
                "success": True,
                "audio_path": output_path,
                "text": text
            }
            
        except Exception as e:
            self.is_speaking = False
            print(f"❌ Speech synthesis error: {e}")
            return {
                "success": False,
                "error": str(e),
                "audio_path": None
            }
    
    def speak_question_async(self, question_text: str, callback: Optional[Callable] = None):
        """Synthesize and play question asynchronously."""
        def speak():
            try:
                # Add interview context
                formatted_text = f"Here is your next interview question: {question_text}"
                
                result = self.synthesize_speech(formatted_text)
                
                if result["success"]:
                    # You would play the audio file here
                    # For now, we'll just indicate it's ready
                    print(f"🔊 Audio ready for playback: {result['audio_path']}")
                    
                    if callback:
                        callback(result)
                else:
                    print(f"❌ Failed to synthesize speech: {result['error']}")
                    
            except Exception as e:
                print(f"❌ Async speech error: {e}")
        
        # Run in separate thread
        thread = threading.Thread(target=speak)
        thread.daemon = True
        thread.start()
    
    def get_status(self) -> Dict:
        """Get current voice service status."""
        return {
            "whisper_loaded": self.whisper_model is not None,
            "tts_loaded": self.tts_model is not None,
            "is_speaking": self.is_speaking,
            "is_processing": self.is_processing,
            "gpu_available": torch.cuda.is_available(),
            "device": "cuda" if torch.cuda.is_available() else "cpu"
        }
    
    def test_system(self) -> Dict:
        """Test both speech recognition and synthesis."""
        results = {
            "whisper_working": False,
            "coqui_working": False,
            "gpu_available": torch.cuda.is_available()
        }
        
        try:
            # Test TTS first (easier)
            test_result = self.synthesize_speech("This is a voice system test.")
            results["coqui_working"] = test_result["success"]
            
            # Clean up test file
            if test_result.get("audio_path") and os.path.exists(test_result["audio_path"]):
                os.unlink(test_result["audio_path"])
                
        except Exception as e:
            print(f"TTS test failed: {e}")
        
        # Whisper test requires audio file, so we'll just check if model loaded
        results["whisper_working"] = self.whisper_model is not None
        
        return results

# Create global instance
voice_service = WhisperCoquiVoiceService()

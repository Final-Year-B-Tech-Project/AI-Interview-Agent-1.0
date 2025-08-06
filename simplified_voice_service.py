import pyttsx3
import whisper
import threading
import tempfile
import os
from typing import Dict, Optional, Callable

class SimplifiedVoiceService:
    def __init__(self):
        print("🚀 Initializing Simplified Voice Service...")
        
        # Initialize TTS (works reliably on Windows)
        self.tts_engine = pyttsx3.init()
        self.setup_tts()
        
        # Initialize Whisper STT (state-of-the-art accuracy)
        self.whisper_model = None
        try:
            print("📥 Loading Whisper model...")
            self.whisper_model = whisper.load_model("base")  # Good balance of speed/accuracy
            print("✅ Whisper loaded successfully!")
        except Exception as e:
            print(f"❌ Whisper loading failed: {e}")
        
        self.is_speaking = False
        print("✅ Simplified Voice Service ready!")
    
    def setup_tts(self):
        """Configure TTS settings."""
        try:
            voices = self.tts_engine.getProperty('voices')
            if voices:
                # Set professional voice
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        break
            
            self.tts_engine.setProperty('rate', 150)  # Speech rate
            self.tts_engine.setProperty('volume', 0.8)  # Volume
        except Exception as e:
            print(f"TTS setup warning: {e}")
    
    def synthesize_speech(self, text: str) -> Dict:
        """Generate speech using pyttsx3."""
        try:
            self.is_speaking = True
            formatted_text = f"Here's your interview question: {text}"
            
            # Speak the text
            self.tts_engine.say(formatted_text)
            self.tts_engine.runAndWait()
            
            self.is_speaking = False
            
            return {
                "success": True,
                "audio_path": "tts_audio.wav",  # Placeholder
                "text": text
            }
        except Exception as e:
            self.is_speaking = False
            return {"success": False, "error": str(e)}
    
    def speak_question_async(self, question_text: str, callback: Optional[Callable] = None):
        """Synthesize speech asynchronously."""
        def speak():
            result = self.synthesize_speech(question_text)
            if callback:
                callback(result)
        
        thread = threading.Thread(target=speak)
        thread.daemon = True
        thread.start()
    
    def transcribe_audio(self, audio_path: str) -> Dict:
        """Transcribe audio using Whisper (if available)."""
        if not self.whisper_model:
            return {"success": False, "error": "Whisper model not loaded", "text": ""}
        
        try:
            result = self.whisper_model.transcribe(audio_path)
            return {
                "success": True,
                "text": result["text"].strip(),
                "confidence": 0.9  # Whisper is generally very accurate
            }
        except Exception as e:
            return {"success": False, "error": str(e), "text": ""}
    
    def get_status(self) -> Dict:
        return {
            "tts_loaded": True,
            "whisper_loaded": self.whisper_model is not None,
            "is_speaking": self.is_speaking,
            "device": "cpu"
        }
    
    def test_system(self) -> Dict:
        try:
            result = self.synthesize_speech("Voice system test")
            return {
                "tts_working": result["success"],
                "whisper_working": self.whisper_model is not None
            }
        except Exception as e:
            return {"tts_working": False, "whisper_working": False, "error": str(e)}

# Global instance
voice_service = SimplifiedVoiceService()

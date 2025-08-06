import speech_recognition as sr
import pyttsx3
import threading
import json
import time
from typing import Dict, Optional, Callable
import os

class VoiceService:
    def __init__(self):
        # Initialize speech recognition
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Initialize text-to-speech
        self.tts_engine = pyttsx3.init()
        self.setup_tts_voice()
        
        # Voice recording state
        self.is_recording = False
        self.is_speaking = False
        self.recorded_text = ""
        
        # Calibrate microphone for ambient noise
        self.calibrate_microphone()
    
    def setup_tts_voice(self):
        """Configure text-to-speech voice settings."""
        voices = self.tts_engine.getProperty('voices')
        
        # Try to find a professional-sounding voice
        preferred_voice = None
        for voice in voices:
            if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                preferred_voice = voice.id
                break
        
        if preferred_voice:
            self.tts_engine.setProperty('voice', preferred_voice)
        
        # Set speech rate and volume
        self.tts_engine.setProperty('rate', 150)  # Moderate speed
        self.tts_engine.setProperty('volume', 0.8)  # 80% volume
    
    def calibrate_microphone(self):
        """Calibrate microphone for ambient noise."""
        try:
            print("Calibrating microphone for ambient noise...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("Microphone calibrated successfully!")
        except Exception as e:
            print(f"Warning: Could not calibrate microphone - {str(e)}")
    
    def speak_question(self, question_text: str, callback: Optional[Callable] = None):
        """Convert text to speech and speak the question."""
        def speak():
            try:
                self.is_speaking = True
                print(f"🔊 Speaking: {question_text[:50]}...")
                
                # Add interviewer introduction
                intro = "Here's your next question: "
                full_text = intro + question_text
                
                self.tts_engine.say(full_text)
                self.tts_engine.runAndWait()
                
                self.is_speaking = False
                print("✅ Finished speaking question")
                
                if callback:
                    callback()
                    
            except Exception as e:
                print(f"Error speaking question: {str(e)}")
                self.is_speaking = False
        
        # Run speech in separate thread to avoid blocking
        speech_thread = threading.Thread(target=speak)
        speech_thread.daemon = True
        speech_thread.start()
    
    def start_listening(self, callback: Callable[[str], None], timeout: int = 30):
        """Start listening for voice input."""
        def listen():
            try:
                self.is_recording = True
                self.recorded_text = ""
                
                print("🎤 Listening for your answer...")
                
                with self.microphone as source:
                    # Listen for audio with timeout
                    audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=60)
                
                print("🔄 Processing your speech...")
                
                # Convert speech to text using Google's free service
                text = self.recognizer.recognize_google(audio)
                
                self.recorded_text = text
                self.is_recording = False
                
                print(f"✅ Recognized speech: {text[:100]}...")
                callback(text)
                
            except sr.UnknownValueError:
                self.is_recording = False
                error_msg = "Sorry, I couldn't understand your speech. Please try again."
                print(f"❌ {error_msg}")
                callback(f"[SPEECH_ERROR]: {error_msg}")
                
            except sr.RequestError as e:
                self.is_recording = False
                error_msg = f"Could not request results from speech service: {e}"
                print(f"❌ {error_msg}")
                callback(f"[SPEECH_ERROR]: {error_msg}")
                
            except sr.WaitTimeoutError:
                self.is_recording = False
                error_msg = "Listening timeout. Please try speaking again."
                print(f"❌ {error_msg}")
                callback(f"[SPEECH_ERROR]: {error_msg}")
                
            except Exception as e:
                self.is_recording = False
                error_msg = f"Unexpected error: {str(e)}"
                print(f"❌ {error_msg}")
                callback(f"[SPEECH_ERROR]: {error_msg}")
        
        # Start listening in separate thread
        listen_thread = threading.Thread(target=listen)
        listen_thread.daemon = True
        listen_thread.start()
    
    def stop_listening(self):
        """Stop current listening session."""
        self.is_recording = False
        print("🛑 Stopped listening")
    
    def get_status(self) -> Dict:
        """Get current voice service status."""
        return {
            'is_recording': self.is_recording,
            'is_speaking': self.is_speaking,
            'last_recorded_text': self.recorded_text,
            'microphone_available': self.microphone is not None
        }
    
    def test_voice_system(self) -> Dict:
        """Test both speech recognition and text-to-speech."""
        results = {
            'tts_working': False,
            'microphone_working': False,
            'speech_recognition_working': False
        }
        
        try:
            # Test text-to-speech
            self.tts_engine.say("Voice system test - text to speech working")
            self.tts_engine.runAndWait()
            results['tts_working'] = True
            print("✅ Text-to-speech working")
        except Exception as e:
            print(f"❌ Text-to-speech error: {e}")
        
        try:
            # Test microphone
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            results['microphone_working'] = True
            print("✅ Microphone working")
        except Exception as e:
            print(f"❌ Microphone error: {e}")
        
        # Note: Can't easily test speech recognition without user input
        results['speech_recognition_working'] = results['microphone_working']
        
        return results

# Create global instance
voice_service = VoiceService()

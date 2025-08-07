# Create vapi_service.py
import requests
import os
from typing import Dict, Optional

class VAPIService:
    def __init__(self):
        self.api_key = os.getenv('VAPI_API_KEY')
        self.base_url = "https://api.vapi.ai"
        
    def create_voice_call(self, assistant_config: Dict) -> Dict:
        """Create a voice call with VAPI."""
        try:
            response = requests.post(
                f"{self.base_url}/call",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=assistant_config
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_interview_assistant_config(self, question: str) -> Dict:
        """Get VAPI assistant configuration for interview."""
        return {
            "assistant": {
                "firstMessage": f"Here's your interview question: {question}. Please provide your answer when ready.",
                "model": {
                    "provider": "openai",
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a professional AI interviewer. Ask the provided question and wait for the candidate's response. Keep interactions brief and professional."
                        }
                    ]
                },
                "voice": {
                    "provider": "11labs",
                    "voiceId": "21m00Tcm4TlvDq8ikWAM"  # Professional voice
                }
            }
        }

# Add to your .env
VAPI_API_KEY=your_vapi_key_here

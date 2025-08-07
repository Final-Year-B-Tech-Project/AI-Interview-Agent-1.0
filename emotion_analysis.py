import cv2
import numpy as np
from deepface import DeepFace
import threading
import time
from typing import Dict, List
import json
from collections import deque
import matplotlib.pyplot as plt

class EmotionAnalysisService:
    def __init__(self):
        """Initialize real-time emotion analysis system."""
        print("😊 Initializing Emotion Analysis System...")
        
        # Emotion tracking
        self.emotion_history = deque(maxlen=50)  # Store last 50 emotion readings
        self.confidence_scores = deque(maxlen=50)
        self.current_dominant_emotion = "neutral"
        
        # Confidence analysis
        self.confidence_indicators = {
            "eye_contact": 0.0,
            "facial_stability": 0.0,
            "emotion_consistency": 0.0,
            "voice_emotion_match": 0.0
        }
        
        # Interview-specific metrics
        self.stress_indicators = []
        self.engagement_score = 0.0
        self.authenticity_score = 0.0
        
        print("✅ Emotion Analysis System ready!")
    
    def analyze_frame_emotions(self, frame: np.ndarray) -> Dict:
        """Analyze emotions in a single frame."""
        try:
            # Resize frame for faster processing
            small_frame = cv2.resize(frame, (320, 240))
            
            # Analyze with DeepFace
            analysis = DeepFace.analyze(
                img_path=small_frame,
                actions=['emotion'],
                enforce_detection=False
            )
            
            if isinstance(analysis, list):
                analysis = analysis[0]
            
            emotions = analysis['emotion']
            dominant_emotion = analysis['dominant_emotion']
            
            # Calculate confidence score
            confidence = max(emotions.values()) / 100.0
            
            # Store in history
            self.emotion_history.append(emotions)
            self.confidence_scores.append(confidence)
            self.current_dominant_emotion = dominant_emotion
            
            # Calculate interview-specific metrics
            interview_metrics = self._calculate_interview_metrics(emotions, confidence)
            
            return {
                "success": True,
                "emotions": emotions,
                "dominant_emotion": dominant_emotion,
                "confidence": round(confidence, 3),
                "interview_metrics": interview_metrics,
                "timestamp": time.time()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "emotions": {},
                "dominant_emotion": "unknown",
                "confidence": 0.0
            }
    
    def _calculate_interview_metrics(self, emotions: Dict, confidence: float) -> Dict:
        """Calculate interview-specific emotional metrics."""
        try:
            # Stress indicators
            stress_emotions = ['angry', 'fear', 'sad']
            stress_level = sum(emotions.get(emotion, 0) for emotion in stress_emotions) / 100.0
            
            # Engagement indicators  
            engaged_emotions = ['happy', 'surprise']
            engagement_level = sum(emotions.get(emotion, 0) for emotion in engaged_emotions) / 100.0
            
            # Confidence indicators
            confident_emotions = ['happy', 'neutral']
            confidence_level = sum(emotions.get(emotion, 0) for emotion in confident_emotions) / 100.0
            
            # Authenticity (consistency over time)
            authenticity = self._calculate_authenticity_score()
            
            return {
                "stress_level": round(stress_level, 3),
                "engagement_level": round(engagement_level, 3),
                "confidence_level": round(confidence_level, 3),
                "authenticity_score": round(authenticity, 3),
                "emotional_stability": self._calculate_emotional_stability()
            }
            
        except Exception as e:
            return {
                "stress_level": 0.0,
                "engagement_level": 0.0,
                "confidence_level": 0.0,
                "authenticity_score": 0.0,
                "emotional_stability": 0.0,
                "error": str(e)
            }
    
    def _calculate_authenticity_score(self) -> float:
        """Calculate authenticity based on emotion consistency."""
        if len(self.emotion_history) < 5:
            return 0.5  # Neutral score
        
        try:
            # Calculate variance in dominant emotions
            recent_emotions = list(self.emotion_history)[-10:]  # Last 10 readings
            
            emotion_consistency = 0.0
            if recent_emotions:
                # Calculate how consistent emotions are
                emotion_changes = 0
                prev_dominant = None
                
                for emotions in recent_emotions:
                    current_dominant = max(emotions.keys(), key=lambda x: emotions[x])
                    if prev_dominant and current_dominant != prev_dominant:
                        emotion_changes += 1
                    prev_dominant = current_dominant
                
                # Higher consistency = higher authenticity
                emotion_consistency = 1.0 - (emotion_changes / len(recent_emotions))
            
            return max(0.0, min(1.0, emotion_consistency))
            
        except:
            return 0.5
    
    def _calculate_emotional_stability(self) -> float:
        """Calculate emotional stability score."""
        if len(self.confidence_scores) < 3:
            return 0.5
        
        try:
            recent_confidences = list(self.confidence_scores)[-5:]
            if not recent_confidences:
                return 0.5
            
            # Calculate standard deviation
            mean_confidence = sum(recent_confidences) / len(recent_confidences)
            variance = sum((x - mean_confidence) ** 2 for x in recent_confidences) / len(recent_confidences)
            std_dev = variance ** 0.5
            
            # Lower std_dev = higher stability
            stability = max(0.0, 1.0 - (std_dev * 2))
            return stability
            
        except:
            return 0.5
    
    def detect_deception_indicators(self) -> Dict:
        """Detect potential deception indicators from facial expressions."""
        if len(self.emotion_history) < 5:
            return {"deception_risk": "INSUFFICIENT_DATA"}
        
        try:
            recent_emotions = list(self.emotion_history)[-10:]
            
            deception_flags = []
            risk_score = 0.0
            
            # Check for micro-expressions (rapid emotion changes)
            emotion_volatility = self._calculate_emotion_volatility(recent_emotions)
            if emotion_volatility > 0.7:
                deception_flags.append("High emotional volatility - possible stress/deception")
                risk_score += 0.3
            
            # Check for inappropriate emotions
            avg_emotions = self._calculate_average_emotions(recent_emotions)
            if avg_emotions.get('disgust', 0) > 15:
                deception_flags.append("Elevated disgust levels - possible discomfort with deception")
                risk_score += 0.2
            
            # Check for forced expressions
            if avg_emotions.get('happy', 0) > 70 and avg_emotions.get('fear', 0) > 10:
                deception_flags.append("Forced happiness with underlying fear")
                risk_score += 0.3
            
            # Overall risk assessment
            if risk_score >= 0.6:
                risk_level = "HIGH"
            elif risk_score >= 0.3:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
            
            return {
                "deception_risk": risk_level,
                "risk_score": round(risk_score, 3),
                "flags": deception_flags,
                "emotional_volatility": round(emotion_volatility, 3),
                "average_emotions": avg_emotions
            }
            
        except Exception as e:
            return {
                "deception_risk": "ERROR",
                "error": str(e)
            }
    
    def _calculate_emotion_volatility(self, emotions_list: List[Dict]) -> float:
        """Calculate how much emotions fluctuate."""
        if len(emotions_list) < 3:
            return 0.0
        
        try:
            # Calculate changes between consecutive emotion readings
            total_change = 0.0
            comparisons = 0
            
            for i in range(1, len(emotions_list)):
                prev_emotions = emotions_list[i-1]
                curr_emotions = emotions_list[i]
                
                # Calculate total change in all emotions
                frame_change = 0.0
                for emotion in prev_emotions:
                    if emotion in curr_emotions:
                        frame_change += abs(curr_emotions[emotion] - prev_emotions[emotion])
                
                total_change += frame_change
                comparisons += 1
            
            average_change = total_change / comparisons if comparisons > 0 else 0.0
            volatility = average_change / 700.0  # Normalize (7 emotions * 100 max change)
            
            return min(1.0, volatility)
            
        except:
            return 0.0
    
    def _calculate_average_emotions(self, emotions_list: List[Dict]) -> Dict:
        """Calculate average emotion scores."""
        if not emotions_list:
            return {}
        
        try:
            avg_emotions = {}
            emotion_names = emotions_list[0].keys()
            
            for emotion in emotion_names:
                total = sum(emotions.get(emotion, 0) for emotions in emotions_list)
                avg_emotions[emotion] = round(total / len(emotions_list), 2)
            
            return avg_emotions
            
        except:
            return {}
    
    def generate_emotion_report(self) -> Dict:
        """Generate comprehensive emotion analysis report."""
        if not self.emotion_history:
            return {"error": "No emotion data available"}
        
        try:
            # Overall statistics
            avg_emotions = self._calculate_average_emotions(list(self.emotion_history))
            emotion_volatility = self._calculate_emotion_volatility(list(self.emotion_history))
            authenticity = self._calculate_authenticity_score()
            
            # Interview performance indicators
            avg_confidence = sum(self.confidence_scores) / len(self.confidence_scores)
            
            # Engagement analysis
            engagement_emotions = ['happy', 'surprise', 'neutral']
            engagement_score = sum(avg_emotions.get(emotion, 0) for emotion in engagement_emotions) / 100.0
            
            # Stress analysis  
            stress_emotions = ['angry', 'fear', 'sad']
            stress_score = sum(avg_emotions.get(emotion, 0) for emotion in stress_emotions) / 100.0
            
            # Deception analysis
            deception_analysis = self.detect_deception_indicators()
            
            # Overall assessment
            overall_score = (authenticity + engagement_score + (1 - stress_score) + avg_confidence) / 4
            
            return {
                "overall_emotional_score": round(overall_score * 100, 1),
                "average_emotions": avg_emotions,
                "dominant_emotion": self.current_dominant_emotion,
                "authenticity_score": round(authenticity * 100, 1),
                "engagement_score": round(engagement_score * 100, 1),
                "stress_level": round(stress_score * 100, 1),
                "emotional_stability": round((1 - emotion_volatility) * 100, 1),
                "average_confidence": round(avg_confidence * 100, 1),
                "deception_analysis": deception_analysis,
                "total_frames_analyzed": len(self.emotion_history),
                "interview_duration": f"{len(self.emotion_history) * 2} seconds"  # Assuming 0.5 FPS analysis
            }
            
        except Exception as e:
            return {"error": str(e)}

# Global instance
emotion_analyzer = EmotionAnalysisService()

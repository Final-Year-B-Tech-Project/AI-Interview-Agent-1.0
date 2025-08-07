import cv2
import numpy as np
import time
import threading
from typing import Dict, List, Optional
import face_recognition
import dlib
import mediapipe as mp
from deepface import DeepFace
import json
from datetime import datetime

class ProxyDetectionService:
    def __init__(self):
        """Initialize proxy detection with multiple AI models."""
        print("🔒 Initializing Proxy Detection System...")
        
        # Face recognition models
        self.face_detector = dlib.get_frontal_face_detector()
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=2,  # Detect multiple faces
            refine_landmarks=True
        )
        
        # Voice analysis
        self.voice_samples = []
        self.baseline_voice_pattern = None
        
        # Behavioral tracking
        self.behavioral_flags = []
        self.suspicious_activities = 0
        self.reference_face_encoding = None
        
        # Detection thresholds
        self.FACE_CONSISTENCY_THRESHOLD = 0.6
        self.VOICE_CONSISTENCY_THRESHOLD = 0.7
        self.BEHAVIORAL_ALERT_THRESHOLD = 3
        
        print("✅ Proxy Detection System ready!")
    
    def initialize_candidate_identity(self, image_path: str = None, 
                                    webcam_frame: np.ndarray = None) -> Dict:
        """Initialize candidate's baseline identity markers."""
        try:
            if image_path:
                image = face_recognition.load_image_file(image_path)
            elif webcam_frame is not None:
                image = webcam_frame
            else:
                return {"success": False, "error": "No image provided"}
            
            # Extract face encoding
            face_encodings = face_recognition.face_encodings(image)
            if not face_encodings:
                return {"success": False, "error": "No face detected in image"}
            
            self.reference_face_encoding = face_encodings[0]
            
            # Analyze facial features with DeepFace
            try:
                face_analysis = DeepFace.analyze(image, actions=['age', 'gender', 'race'])
                self.baseline_demographics = face_analysis
            except:
                self.baseline_demographics = {}
            
            return {
                "success": True,
                "message": "Candidate identity initialized",
                "face_detected": True,
                "demographics": self.baseline_demographics
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def real_time_face_verification(self, frame: np.ndarray) -> Dict:
        """Continuously verify candidate's face against baseline."""
        try:
            if self.reference_face_encoding is None:
                return {"authenticated": False, "error": "No baseline face encoding"}
            
            # Detect faces in current frame
            face_locations = face_recognition.face_locations(frame)
            face_encodings = face_recognition.face_encodings(frame, face_locations)
            
            results = {
                "authenticated": False,
                "face_count": len(face_locations),
                "confidence": 0.0,
                "alerts": []
            }
            
            # Check for multiple faces (proxy assistance)
            if len(face_locations) > 1:
                results["alerts"].append("⚠️ Multiple faces detected - possible assistance")
                self.suspicious_activities += 1
            
            if len(face_locations) == 0:
                results["alerts"].append("❌ No face detected - candidate may have left")
                self.suspicious_activities += 1
                return results
            
            # Compare with reference face
            if face_encodings:
                current_face = face_encodings[0]
                face_distance = face_recognition.face_distance([self.reference_face_encoding], current_face)[0]
                confidence = 1 - face_distance
                
                results["confidence"] = round(confidence, 3)
                
                if confidence >= self.FACE_CONSISTENCY_THRESHOLD:
                    results["authenticated"] = True
                else:
                    results["alerts"].append(f"🚨 Face mismatch detected - confidence: {confidence:.3f}")
                    self.suspicious_activities += 1
            
            return results
            
        except Exception as e:
            return {"authenticated": False, "error": str(e)}
    
    def detect_behavioral_anomalies(self, frame: np.ndarray) -> Dict:
        """Detect suspicious behavioral patterns."""
        try:
            results = {
                "behavioral_score": 0,
                "anomalies": [],
                "eye_contact_score": 0,
                "attention_score": 0
            }
            
            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_results = self.face_mesh.process(rgb_frame)
            
            if face_results.multi_face_landmarks:
                for face_landmarks in face_results.multi_face_landmarks:
                    # Analyze eye gaze direction
                    eye_contact = self._analyze_eye_contact(face_landmarks)
                    results["eye_contact_score"] = eye_contact
                    
                    # Detect unnatural head movements
                    head_stability = self._analyze_head_stability(face_landmarks)
                    results["attention_score"] = head_stability
                    
                    # Check for robotic/unnatural expressions
                    if eye_contact < 0.3:
                        results["anomalies"].append("👁️ Poor eye contact - possible reading from script")
                    
                    if head_stability < 0.4:
                        results["anomalies"].append("🤖 Unnatural head movements - possible pre-recorded video")
                    
                    # Calculate overall behavioral score
                    results["behavioral_score"] = (eye_contact + head_stability) / 2
            
            return results
            
        except Exception as e:
            return {"behavioral_score": 0, "error": str(e)}
    
    def _analyze_eye_contact(self, face_landmarks) -> float:
        """Analyze eye contact quality and direction."""
        try:
            # Extract eye landmarks (MediaPipe indices)
            left_eye_indices = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
            right_eye_indices = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
            
            # Calculate eye aspect ratio and gaze direction
            left_eye_ratio = self._calculate_eye_aspect_ratio(face_landmarks, left_eye_indices)
            right_eye_ratio = self._calculate_eye_aspect_ratio(face_landmarks, right_eye_indices)
            
            # Eye contact score based on eye openness and direction
            avg_ratio = (left_eye_ratio + right_eye_ratio) / 2
            return min(1.0, max(0.0, avg_ratio * 2))  # Normalize to 0-1
            
        except:
            return 0.5  # Default neutral score
    
    def _calculate_eye_aspect_ratio(self, landmarks, indices) -> float:
        """Calculate eye aspect ratio for eye contact detection."""
        try:
            points = [(landmarks.landmark[i].x, landmarks.landmark[i].y) for i in indices[:6]]
            
            # Eye aspect ratio calculation
            A = np.linalg.norm(np.array(points[1]) - np.array(points[5]))
            B = np.linalg.norm(np.array(points[2]) - np.array(points[4]))
            C = np.linalg.norm(np.array(points[0]) - np.array(points[3]))
            
            ear = (A + B) / (2.0 * C)
            return ear
            
        except:
            return 0.2
    
    def _analyze_head_stability(self, face_landmarks) -> float:
        """Analyze head movement stability and naturalness."""
        try:
            # Use nose tip as reference point
            nose_tip = face_landmarks.landmark[1]
            forehead = face_landmarks.landmark[10]
            chin = face_landmarks.landmark[152]
            
            # Calculate head pose stability
            vertical_alignment = abs(nose_tip.y - (forehead.y + chin.y) / 2)
            stability_score = 1.0 - min(1.0, vertical_alignment * 10)
            
            return stability_score
            
        except:
            return 0.5
    
    def analyze_voice_consistency(self, audio_features: Dict) -> Dict:
        """Analyze voice patterns for consistency."""
        try:
            results = {
                "voice_match": False,
                "confidence": 0.0,
                "alerts": []
            }
            
            if not self.baseline_voice_pattern:
                # First voice sample - establish baseline
                self.baseline_voice_pattern = audio_features
                results["voice_match"] = True
                results["confidence"] = 1.0
                return results
            
            # Compare with baseline (simplified)
            pitch_similarity = self._compare_voice_features(
                audio_features.get('pitch', 0),
                self.baseline_voice_pattern.get('pitch', 0)
            )
            
            tone_similarity = self._compare_voice_features(
                audio_features.get('tone', 0),
                self.baseline_voice_pattern.get('tone', 0)
            )
            
            overall_similarity = (pitch_similarity + tone_similarity) / 2
            results["confidence"] = overall_similarity
            
            if overall_similarity >= self.VOICE_CONSISTENCY_THRESHOLD:
                results["voice_match"] = True
            else:
                results["alerts"].append(f"🎤 Voice pattern mismatch - confidence: {overall_similarity:.3f}")
                self.suspicious_activities += 1
            
            return results
            
        except Exception as e:
            return {"voice_match": False, "error": str(e)}
    
    def _compare_voice_features(self, current: float, baseline: float) -> float:
        """Compare voice feature similarity."""
        if baseline == 0:
            return 1.0
        
        difference = abs(current - baseline) / max(abs(baseline), 1)
        similarity = max(0.0, 1.0 - difference)
        return similarity
    
    def detect_screen_sharing_indicators(self, frame: np.ndarray) -> Dict:
        """Detect signs of screen sharing or remote assistance."""
        try:
            results = {
                "screen_sharing_detected": False,
                "suspicious_elements": [],
                "confidence": 0.0
            }
            
            # Convert to grayscale for analysis
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Look for unusual patterns that might indicate screen sharing
            # Check for pixelation or compression artifacts
            blur_level = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            if blur_level < 50:  # Very low - possible screen sharing
                results["suspicious_elements"].append("📺 Low image quality - possible screen sharing")
                results["confidence"] += 0.3
            
            # Check for rectangular boundaries (common in screen sharing)
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            large_rectangles = 0
            for contour in contours:
                if cv2.contourArea(contour) > 1000:
                    approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
                    if len(approx) == 4:  # Rectangle
                        large_rectangles += 1
            
            if large_rectangles > 5:
                results["suspicious_elements"].append("🖥️ Multiple rectangular elements - possible application windows")
                results["confidence"] += 0.4
            
            results["screen_sharing_detected"] = results["confidence"] > 0.5
            
            return results
            
        except Exception as e:
            return {"screen_sharing_detected": False, "error": str(e)}
    
    def generate_security_report(self) -> Dict:
        """Generate comprehensive security report."""
        total_alerts = self.suspicious_activities
        risk_level = "LOW"
        
        if total_alerts >= 5:
            risk_level = "HIGH"
        elif total_alerts >= 3:
            risk_level = "MEDIUM"
        
        recommendations = []
        if total_alerts > 0:
            recommendations.extend([
                "Verify candidate identity with additional documentation",
                "Conduct follow-up verification call",
                "Ask spontaneous personal questions not in resume"
            ])
        
        if risk_level == "HIGH":
            recommendations.extend([
                "🚨 IMMEDIATE ACTION: Pause interview for identity verification",
                "Request additional ID verification",
                "Consider in-person or phone verification"
            ])
        
        return {
            "risk_level": risk_level,
            "total_suspicious_activities": total_alerts,
            "security_score": max(0, 100 - (total_alerts * 10)),
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat(),
            "behavioral_flags": self.behavioral_flags
        }

# Global instance
proxy_detector = ProxyDetectionService()

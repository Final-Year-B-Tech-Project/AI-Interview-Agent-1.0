import os
import json
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class AIInterviewService:
    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.base_url = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
        # UPGRADED: DeepSeek R1T2 Chimera - much better and faster!
        self.model = os.getenv('OPENROUTER_MODEL', 'tngtech/deepseek-r1t2-chimera:free')
        
        if not self.api_key or self.api_key == 'sk-or-v1-your-key-here-replace-this':
            print("WARNING: OPENROUTER_API_KEY not properly configured!")
            self.api_key = None

    def generate_interview_question(self, domain: str, difficulty: str, question_type: str, 
                                  previous_answers: List[Dict] = None, question_number: int = 1) -> Dict:
        """Generate varied interview questions with better context - Enhanced with R1T2 Chimera."""
        
        # If no API key, use fallback
        if not self.api_key:
            return self._get_fallback_question(domain, difficulty, question_type)
        
        # Build context from previous answers to avoid repetition
        context = ""
        answered_topics = []
        if previous_answers:
            for ans in previous_answers[-3:]:  # Last 3 questions for context
                topics = self._extract_topics(ans.get('question', ''))
                answered_topics.extend(topics)
            
            if answered_topics:
                context = f"Previously discussed topics: {', '.join(answered_topics)}. "
        
        # Question progression logic for natural interview flow
        if question_number == 1:
            question_focus = "Start with a warm, conversational foundational question"
            greeting = "Let's start with: "
        elif question_number <= 3:
            question_focus = "Focus on practical application and hands-on experience"  
            greeting = "Now let me ask you: "
        elif question_number <= 6:
            question_focus = "Ask about problem-solving and real-world scenarios"
            greeting = "Here's an interesting challenge: "
        else:
            question_focus = "Explore advanced topics and leadership/design decisions"
            greeting = "Let's dive deeper: "
        
        # Enhanced prompt for R1T2 Chimera's superior reasoning
        prompt = f"""You are conducting a professional {domain} voice interview. This is question #{question_number} of 8.

Domain: {domain}
Difficulty: {difficulty}
Type: {question_type}
Question Focus: {question_focus}
{context}

CRITICAL Requirements:
1. Generate a UNIQUE question completely different from any previously discussed topics
2. Question should be perfectly suited for {domain} at {difficulty} level
3. {question_focus}
4. For "technical" questions - focus on skills, algorithms, system design, coding problems
5. For "behavioral" questions - focus on past experiences, problem-solving approach, leadership
6. Make the question conversational and natural for voice delivery
7. Avoid repeating ANY topics from: {answered_topics}
8. Keep under 100 words for clear voice delivery
9. Make it sound like a real interviewer asking naturally

Start your response with: "{greeting}" and then provide the question.

Generate ONLY the complete question text with the greeting, nothing else."""

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:5000",
                    "X-Title": "AI Interview Agent"
                },
                json={
                    "model": self.model,  # Using superior R1T2 Chimera!
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 300,
                    "temperature": 0.8  # More creative questions
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                question_text = result['choices'][0]['message']['content'].strip()
                
                return {
                    'question_text': question_text,
                    'generated_by_ai': True,
                    'model_used': self.model,
                    'question_number': question_number
                }
            else:
                print(f"OpenRouter API Error: {response.status_code} - {response.text}")
                return self._get_fallback_question(domain, difficulty, question_type)
        
        except Exception as e:
            print(f"Error generating question: {str(e)}")
            return self._get_fallback_question(domain, difficulty, question_type)

    def _extract_topics(self, question_text: str) -> List[str]:
        """Extract key topics from a question to avoid repetition."""
        # Simple keyword extraction
        common_words = {'what', 'how', 'why', 'when', 'where', 'tell', 'describe', 'explain', 'the', 'a', 'an', 'is', 'are', 'you', 'me', 'about', 'your', 'can', 'would', 'should', 'do', 'does', 'did', 'have', 'has', 'had', 'will', 'with', 'for', 'on', 'in', 'at', 'by', 'from', 'to', 'of', 'and', 'or', 'but'}
        
        words = question_text.lower().split()
        topics = [word.strip('.,!?()[]{}":;') for word in words if len(word) > 3 and word not in common_words]
        return list(set(topics))  # Remove duplicates

    def evaluate_answer(self, question: str, answer: str, domain: str, 
                       difficulty: str, expected_keywords: List[str] = None) -> Dict:
        """Enhanced answer evaluation using R1T2 Chimera's superior reasoning."""
        
        # If no API key, use fallback
        if not self.api_key:
            return self._get_fallback_evaluation(answer)
        
        # Enhanced evaluation prompt for R1T2 Chimera
        prompt = f"""You are an expert {domain} interviewer evaluating a candidate's voice response.

Question Asked: {question}
Candidate's Voice Answer: {answer}
Domain: {domain}
Difficulty Level: {difficulty}
Expected Keywords: {expected_keywords or []}

COMPREHENSIVE EVALUATION CRITERIA:
1. Technical Accuracy (25%) - Correct information and concepts
2. Depth of Knowledge (25%) - Understanding and detail level  
3. Communication Clarity (20%) - How well they explained concepts
4. Practical Application (15%) - Real-world examples and experience
5. Completeness (15%) - Addressed all parts of the question

SCORING GUIDE for {difficulty} level:
- 9-10: Exceptional answer with deep insight and clear examples
- 7-8: Strong answer demonstrating solid understanding  
- 5-6: Adequate answer but missing some depth or clarity
- 3-4: Basic answer with significant gaps
- 1-2: Poor answer showing fundamental misunderstandings

Provide your response in this EXACT JSON format:
{{
    "score": 7,
    "detailed_feedback": "The candidate demonstrated excellent understanding of core concepts. Their explanation of [specific topic] was particularly strong, showing practical experience. However, they could have elaborated more on [specific area] to provide a more complete answer.",
    "strengths": ["Strong technical foundation", "Clear communication", "Good practical examples"],
    "improvement_areas": ["Could provide more specific examples", "Missed discussing edge cases", "Consider scalability aspects"],
    "follow_up_suggestion": "Can you tell me more about how you would handle [specific scenario]?"
}}"""

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:5000",
                    "X-Title": "AI Interview Agent"
                },
                json={
                    "model": self.model,  # R1T2 Chimera's superior evaluation
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.2  # More consistent evaluations
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                evaluation_text = result['choices'][0]['message']['content'].strip()
                
                # Try to parse JSON response
                try:
                    evaluation = json.loads(evaluation_text)
                    # Ensure score is within valid range
                    evaluation['score'] = max(1, min(10, evaluation.get('score', 5)))
                    return evaluation
                except json.JSONDecodeError:
                    # If JSON parsing fails, extract score and create response
                    score = self._extract_score_from_text(evaluation_text)
                    return {
                        "score": score,
                        "detailed_feedback": evaluation_text,
                        "strengths": ["Answer provided", "Attempted to address the question"],
                        "improvement_areas": ["Review the detailed feedback above"],
                        "follow_up_suggestion": "Try to provide more specific examples in your next answer."
                    }
            else:
                return self._get_fallback_evaluation(answer)
        
        except Exception as e:
            print(f"Error evaluating answer: {str(e)}")
            return self._get_fallback_evaluation(answer)

    def generate_interview_feedback(self, interview_data: Dict) -> Dict:
        """Generate comprehensive interview feedback using R1T2 Chimera."""
        
        # If no API key, use fallback
        if not self.api_key:
            return self._get_fallback_feedback(interview_data.get('overall_score', 0))
        
        answers = interview_data.get('answers', [])
        overall_score = interview_data.get('overall_score', 0)
        domain = interview_data.get('domain', 'General')
        
        # Detailed answer analysis for R1T2 Chimera
        answers_analysis = "\n".join([
            f"Q{i+1} (Score: {ans.get('score', 0)}/10): {ans.get('question', '')[:80]}..."
            f"\nCandidate Response: {ans.get('answer', '')[:100]}..."
            for i, ans in enumerate(answers[:6])  # First 6 questions
        ])
        
        # Enhanced feedback prompt for R1T2 Chimera's superior analysis
        prompt = f"""Conduct a comprehensive analysis of this {domain} voice interview performance:

INTERVIEW SUMMARY:
Domain: {domain}  
Overall Score: {overall_score}/10
Total Questions: {len(answers)}

DETAILED QUESTION ANALYSIS:
{answers_analysis}

COMPREHENSIVE ASSESSMENT REQUIRED:
Analyze the candidate's performance across technical knowledge, communication skills, problem-solving approach, and domain expertise. Consider their consistency across questions and how their answers demonstrate real-world application.

Provide detailed analysis in this EXACT JSON format:
{{
    "overall_assessment": "Comprehensive 3-4 sentence summary of the candidate's overall performance, highlighting their strongest areas and main development needs",
    "key_strengths": ["Specific strength with context", "Another specific strength", "Third strength area"],
    "areas_for_improvement": ["Specific area with actionable advice", "Technical gap to address", "Communication aspect to improve"],
    "specific_recommendations": ["Concrete action they should take", "Resource or practice suggestion", "Skill development focus"],
    "next_steps": "Detailed paragraph about immediate actions the candidate should take to improve, including specific resources, practice areas, or learning paths",
    "industry_comparison": "How does this performance compare to other candidates at similar experience levels? What percentile would this place them in for {domain} roles?"
}}"""

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:5000",
                    "X-Title": "AI Interview Agent"
                },
                json={
                    "model": self.model,  # R1T2 Chimera's comprehensive analysis
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 800,
                    "temperature": 0.3
                },
                timeout=45
            )
            
            if response.status_code == 200:
                result = response.json()
                feedback_text = result['choices'][0]['message']['content'].strip()
                
                try:
                    return json.loads(feedback_text)
                except json.JSONDecodeError:
                    return {
                        "overall_assessment": feedback_text[:300] + "...",
                        "key_strengths": ["Completed the interview successfully", "Demonstrated engagement", "Provided thoughtful responses"],
                        "areas_for_improvement": ["Review detailed AI feedback", "Focus on specific examples", "Practice technical explanations"],
                        "specific_recommendations": ["Take more practice interviews", "Study core domain concepts", "Prepare concrete examples"],
                        "next_steps": "Continue practicing with similar interview questions and focus on providing more specific, detailed examples from your experience.",
                        "industry_comparison": f"This performance shows {['developing', 'emerging', 'solid', 'strong'][min(3, overall_score//3)]} potential for {domain} roles."
                    }
            else:
                return self._get_fallback_feedback(overall_score)
        
        except Exception as e:
            print(f"Error generating feedback: {str(e)}")
            return self._get_fallback_feedback(overall_score)

    def _get_fallback_question(self, domain: str, difficulty: str, question_type: str) -> Dict:
        """Enhanced fallback questions when AI fails."""
        fallback_questions = {
            'Software Engineering': {
                'beginner': {
                    'technical': "Let's start with: What's the difference between a list and an array in programming, and when would you use each?",
                    'behavioral': "Tell me about: Describe a time you had to learn a new programming language or technology. How did you approach it?"
                },
                'intermediate': {
                    'technical': "Now let me ask you: How would you design a REST API for a todo application? Walk me through your approach.",
                    'behavioral': "Here's a scenario: Describe a challenging bug you encountered. What was your debugging process?"
                },
                'expert': {
                    'technical': "Let's dive deeper: How would you architect a system to handle 1 million concurrent users? Consider scalability and performance.",
                    'behavioral': "Tell me about: Describe a time you had to make a critical technical decision with incomplete information."
                }
            },
            'Data Science': {
                'beginner': {
                    'technical': "Let's start with: What's the difference between supervised and unsupervised learning? Can you give me examples?",
                    'behavioral': "Tell me about: Walk me through a data analysis project you worked on from start to finish."
                },
                'intermediate': {
                    'technical': "Now let me ask: How would you handle missing data in a dataset? What are the different approaches?",
                    'behavioral': "Here's a challenge: Describe a time when your analysis revealed unexpected insights. How did you communicate this?"
                },
                'expert': {
                    'technical': "Let's explore: How would you build and deploy a real-time recommendation system for millions of users?",
                    'behavioral': "Tell me about: Describe a situation where your data analysis directly influenced major business decisions."
                }
            }
        }
        
        question = fallback_questions.get(domain, fallback_questions['Software Engineering']).get(difficulty, {}).get(question_type, "Tell me about yourself and your experience in this field.")
        
        return {
            'question_text': question,
            'generated_by_ai': False,
            'model_used': 'fallback'
        }

    def _get_fallback_evaluation(self, answer: str) -> Dict:
        """Enhanced fallback evaluation when AI fails."""
        words = answer.split()
        word_count = len(words)
        
        # Improved scoring logic
        if word_count < 15:
            score = 3
            feedback = "Your answer is quite brief. Try to provide more detailed explanations and specific examples."
        elif word_count < 50:
            score = 5  
            feedback = "Good start! Your answer covers the basics. Consider adding more detail and specific examples to strengthen your response."
        elif word_count < 100:
            score = 7
            feedback = "Well-structured answer! You demonstrated good understanding. Adding more technical depth or real-world examples would make it even stronger."
        else:
            score = 8
            feedback = "Comprehensive answer! You provided good detail and coverage of the topic. Your explanation was thorough and well-organized."
        
        # Bonus for technical keywords
        technical_keywords = ['algorithm', 'data', 'system', 'design', 'implement', 'optimize', 'performance', 'scalability', 'architecture', 'framework', 'database', 'api', 'security']
        keyword_bonus = min(1, sum(0.2 for keyword in technical_keywords if keyword.lower() in answer.lower()))
        score = min(10, int(score + keyword_bonus))
        
        return {
            "score": score,
            "detailed_feedback": feedback,
            "strengths": ["Provided a substantive response", "Demonstrated understanding of the topic"],
            "improvement_areas": ["Consider adding more specific examples", "Provide more technical depth where appropriate"],
            "follow_up_suggestion": "Try to include concrete examples from your experience to illustrate your points."
        }

    def _get_fallback_feedback(self, overall_score: int) -> Dict:
        """Enhanced fallback feedback when AI fails."""
        if overall_score >= 8:
            assessment = "Excellent performance! You demonstrated strong technical knowledge and communication skills across multiple areas."
            strengths = ["Strong technical foundation", "Clear communication", "Comprehensive answers"]
            next_steps = "Continue building on your strengths. Consider exploring advanced topics and leadership opportunities in your field."
        elif overall_score >= 6:
            assessment = "Good performance with solid understanding of core concepts. There are opportunities to demonstrate more depth and practical experience."
            strengths = ["Good foundational knowledge", "Engaged responses", "Understanding of key concepts"]
            next_steps = "Focus on gaining more hands-on experience and preparing specific examples that demonstrate your problem-solving abilities."
        elif overall_score >= 4:
            assessment = "Average performance showing basic understanding. Focus on strengthening technical knowledge and providing more detailed responses."
            strengths = ["Completed all questions", "Basic understanding", "Willingness to engage"]
            next_steps = "Dedicate time to studying core concepts in your field and practice explaining technical topics clearly and concisely."
        else:
            assessment = "Keep practicing! Focus on building fundamental knowledge and improving communication of technical concepts."
            strengths = ["Showed effort", "Completed the interview", "Room for growth"]
            next_steps = "Start with foundational learning resources and take practice interviews to build confidence and technical knowledge."
        
        return {
            "overall_assessment": f"You completed the interview with a score of {overall_score}/10. {assessment}",
            "key_strengths": strengths,
            "areas_for_improvement": ["Technical depth", "Communication clarity", "Specific examples", "Problem-solving methodology"],
            "specific_recommendations": ["Practice explaining technical concepts aloud", "Prepare concrete examples from your experience", "Review fundamental concepts in your domain"],
            "next_steps": next_steps,
            "industry_comparison": f"This performance represents {'excellent', 'above-average', 'developing', 'entry-level'}[min(3, max(0, (overall_score-1)//2))] readiness for professional roles in your field."
        }

    def _extract_score_from_text(self, text: str) -> int:
        """Extract numeric score from text."""
        import re
        scores = re.findall(r'\b([1-9]|10)\b', text)
        if scores:
            return int(scores[0])
        return 5  # Default score

# Create global instance
ai_service = AIInterviewService()

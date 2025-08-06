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
        self.model = os.getenv('OPENROUTER_MODEL', 'openai/gpt-3.5-turbo')
        
        if not self.api_key or self.api_key == 'sk-or-v1-your-key-here-replace-this':
            print("WARNING: OPENROUTER_API_KEY not properly configured!")
            self.api_key = None

    def generate_interview_question(self, domain: str, difficulty: str, question_type: str, 
                                  previous_answers: List[Dict] = None) -> Dict:
        """Generate a dynamic interview question based on context."""
        
        # If no API key, use fallback
        if not self.api_key:
            return self._get_fallback_question(domain, difficulty, question_type)
        
        # Build context from previous answers
        context = ""
        if previous_answers:
            context = "\n".join([
                f"Previous Q: {ans.get('question', '')[:50]}... | Answer Quality: {ans.get('score', 0)}/10"
                for ans in previous_answers[-3:]  # Last 3 questions for context
            ])
        
        prompt = f"""You are an expert interviewer for {domain} positions. Generate a {difficulty} level {question_type} interview question.

Domain: {domain}
Difficulty: {difficulty} 
Question Type: {question_type}
Previous Context: {context}

Requirements:
1. Question should be relevant to {domain} field
2. Appropriate for {difficulty} level (beginner = basic concepts, intermediate = practical application, expert = advanced design)
3. If {question_type} is "technical" - focus on skills, algorithms, or technical knowledge
4. If {question_type} is "behavioral" - focus on past experiences, problem-solving approach
5. If previous answers show high scores, increase complexity slightly
6. If previous answers show low scores, adjust to be more foundational

Generate ONLY the question text, nothing else. Make it specific and clear."""

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
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200,
                    "temperature": 0.8
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                question_text = result['choices'][0]['message']['content'].strip()
                
                return {
                    'question_text': question_text,
                    'generated_by_ai': True,
                    'model_used': self.model
                }
            else:
                print(f"OpenRouter API Error: {response.status_code} - {response.text}")
                return self._get_fallback_question(domain, difficulty, question_type)
                
        except Exception as e:
            print(f"Error generating question: {str(e)}")
            return self._get_fallback_question(domain, difficulty, question_type)

    def evaluate_answer(self, question: str, answer: str, domain: str, 
                       difficulty: str, expected_keywords: List[str] = None) -> Dict:
        """Evaluate an interview answer using AI."""
        
        # If no API key, use fallback
        if not self.api_key:
            return self._get_fallback_evaluation(answer)
        
        prompt = f"""You are an expert interviewer evaluating a candidate's answer for a {domain} position.

Question: {question}
Candidate's Answer: {answer}
Domain: {domain}
Difficulty Level: {difficulty}
Expected Keywords: {expected_keywords or []}

Evaluate the answer on a scale of 1-10 considering:
1. Technical accuracy and knowledge demonstration
2. Clarity and communication skills  
3. Completeness of the answer
4. Relevant examples or experiences mentioned
5. Understanding of concepts for {difficulty} level

Provide your response in this EXACT JSON format:
{{
    "score": 7,
    "detailed_feedback": "The candidate demonstrated good understanding of...",
    "strengths": ["Good technical knowledge", "Clear communication"],
    "improvement_areas": ["Could provide more specific examples", "Missed discussing scalability"],
    "follow_up_suggestion": "Can you explain how you would handle..."
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
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 400,
                    "temperature": 0.3
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                evaluation_text = result['choices'][0]['message']['content'].strip()
                
                # Try to parse JSON response
                try:
                    evaluation = json.loads(evaluation_text)
                    return evaluation
                except json.JSONDecodeError:
                    # If JSON parsing fails, extract score and create basic response
                    score = self._extract_score_from_text(evaluation_text)
                    return {
                        "score": score,
                        "detailed_feedback": evaluation_text,
                        "strengths": ["Answer provided"],
                        "improvement_areas": ["Review the feedback above"],
                        "follow_up_suggestion": ""
                    }
            else:
                return self._get_fallback_evaluation(answer)
                
        except Exception as e:
            print(f"Error evaluating answer: {str(e)}")
            return self._get_fallback_evaluation(answer)

    def generate_interview_feedback(self, interview_data: Dict) -> Dict:
        """Generate comprehensive interview feedback."""
        
        # If no API key, use fallback
        if not self.api_key:
            return self._get_fallback_feedback(interview_data.get('overall_score', 0))
        
        answers = interview_data.get('answers', [])
        overall_score = interview_data.get('overall_score', 0)
        domain = interview_data.get('domain', 'General')
        
        answers_summary = "\n".join([
            f"Q{i+1}: {ans.get('question', '')[:100]}... | Score: {ans.get('score', 0)}/10"
            for i, ans in enumerate(answers[:5])  # First 5 questions
        ])
        
        prompt = f"""Analyze this interview performance and provide comprehensive feedback:

Domain: {domain}
Overall Score: {overall_score}/10
Interview Summary:
{answers_summary}

Provide detailed analysis in this JSON format:
{{
    "overall_assessment": "Brief overall performance summary",
    "key_strengths": ["Strength 1", "Strength 2", "Strength 3"],
    "areas_for_improvement": ["Area 1", "Area 2", "Area 3"],
    "specific_recommendations": ["Recommendation 1", "Recommendation 2"],
    "next_steps": "What the candidate should do next to improve",
    "industry_comparison": "How does this compare to typical candidates?"
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
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.4
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                feedback_text = result['choices'][0]['message']['content'].strip()
                
                try:
                    return json.loads(feedback_text)
                except json.JSONDecodeError:
                    return {
                        "overall_assessment": feedback_text,
                        "key_strengths": ["Completed the interview"],
                        "areas_for_improvement": ["Review AI feedback"],
                        "specific_recommendations": ["Practice more interviews"],
                        "next_steps": "Continue practicing",
                        "industry_comparison": "Average performance"
                    }
            else:
                return self._get_fallback_feedback(overall_score)
                
        except Exception as e:
            print(f"Error generating feedback: {str(e)}")
            return self._get_fallback_feedback(overall_score)

    def _get_fallback_question(self, domain: str, difficulty: str, question_type: str) -> Dict:
        """Fallback questions when AI fails."""
        fallback_questions = {
            'Software Engineering': {
                'beginner': {
                    'technical': "What is the difference between a list and an array in programming?",
                    'behavioral': "Tell me about a time you had to learn a new programming language or technology."
                },
                'intermediate': {
                    'technical': "Explain how you would design a simple REST API for a todo application.",
                    'behavioral': "Describe a challenging bug you encountered and how you solved it."
                },
                'expert': {
                    'technical': "How would you design a system to handle 1 million concurrent users?",
                    'behavioral': "Tell me about a time you had to make a difficult technical decision."
                }
            },
            'Data Science': {
                'beginner': {
                    'technical': "What is the difference between supervised and unsupervised learning?",
                    'behavioral': "Tell me about a data analysis project you worked on."
                },
                'intermediate': {
                    'technical': "How would you handle missing data in a dataset?",
                    'behavioral': "Describe a time when you had to explain technical concepts to non-technical stakeholders."
                },
                'expert': {
                    'technical': "Explain how you would build a recommendation system from scratch.",
                    'behavioral': "Tell me about a time when your analysis led to important business decisions."
                }
            }
        }
        
        question = fallback_questions.get(domain, fallback_questions['Software Engineering']).get(difficulty, {}).get(question_type, "Tell me about yourself and your experience.")
        
        return {
            'question_text': question,
            'generated_by_ai': False,
            'model_used': 'fallback'
        }

    def _get_fallback_evaluation(self, answer: str) -> Dict:
        """Fallback evaluation when AI fails."""
        # Simple scoring based on answer length and keywords
        words = answer.split()
        word_count = len(words)
        
        if word_count < 10:
            score = 3
        elif word_count < 50:
            score = 5
        elif word_count < 100:
            score = 7
        else:
            score = 8
        
        # Bonus for technical keywords
        technical_keywords = ['algorithm', 'data', 'system', 'design', 'implement', 'optimize', 'performance']
        keyword_bonus = sum(1 for keyword in technical_keywords if keyword.lower() in answer.lower())
        score = min(10, score + keyword_bonus)
        
        return {
            "score": score,
            "detailed_feedback": f"Your answer shows effort and covers the topic. Score based on response length and structure: {score}/10. Try to provide more specific examples and technical details.",
            "strengths": ["Provided a response", "Attempted to answer the question"],
            "improvement_areas": ["Could provide more specific examples", "Consider adding more technical details"],
            "follow_up_suggestion": "Try to expand on your answer with specific examples from your experience."
        }

    def _get_fallback_feedback(self, overall_score: int) -> Dict:
        """Fallback feedback when AI fails."""
        if overall_score >= 8:
            assessment = "Excellent performance! You demonstrated strong knowledge and communication skills."
        elif overall_score >= 6:
            assessment = "Good performance with room for improvement in technical depth and examples."
        elif overall_score >= 4:
            assessment = "Average performance. Focus on strengthening your technical knowledge and communication."
        else:
            assessment = "Keep practicing! Focus on understanding fundamental concepts and providing detailed answers."
            
        return {
            "overall_assessment": f"You completed the interview with a score of {overall_score}/10. {assessment}",
            "key_strengths": ["Completed all questions", "Showed persistence", "Basic understanding"],
            "areas_for_improvement": ["Technical depth", "Communication clarity", "Specific examples"],
            "specific_recommendations": ["Practice more technical questions", "Review domain fundamentals", "Prepare concrete examples"],
            "next_steps": "Take more practice interviews and study core concepts in your domain",
            "industry_comparison": "With practice, you can reach industry-standard performance"
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

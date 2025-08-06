from database import db, Domain, Question, Interview, Answer
from ai_service import ai_service
from sqlalchemy import func
import random
from datetime import datetime

class InterviewService:
    def __init__(self):
        pass
    
    def get_domains(self):
        """Get all available domains."""
        return Domain.query.all()
    
    def create_interview(self, user, domain_id, difficulty_level, duration_minutes=30):
        """Create a new interview session."""
        interview = Interview(
            user_id=user.id,
            domain_id=domain_id,
            difficulty_level=difficulty_level,
            duration_minutes=duration_minutes,
            status='in_progress'
        )
        db.session.add(interview)
        db.session.commit()
        return interview
    
    def get_next_question(self, interview_id):
        """Get the next question for an interview - now AI-powered!"""
        # Get interview details
        interview = Interview.query.get(interview_id)
        if not interview:
            return None
        
        domain = Domain.query.get(interview.domain_id)
        
        # Get previous answers for context
        previous_answers = []
        answered_questions = Answer.query.filter_by(interview_id=interview_id).all()
        
        # Check if we've reached the question limit
        if len(answered_questions) >= 8:  # Limit to 8 questions per interview
            return None
        
        for ans in answered_questions:
            question = Question.query.get(ans.question_id)
            previous_answers.append({
                'question': question.question_text if question else '',
                'answer': ans.answer_text,
                'score': ans.score or 0
            })
        
        # Determine question type (alternate between technical and behavioral)
        question_type = 'technical' if len(answered_questions) % 2 == 0 else 'behavioral'
        
        # Generate AI question
        print(f"Generating AI question for {domain.name}, {interview.difficulty_level}, {question_type}")
        ai_response = ai_service.generate_interview_question(
            domain=domain.name,
            difficulty=interview.difficulty_level,
            question_type=question_type,
            previous_answers=previous_answers
        )
        
        # Create and store the new question
        question = Question(
            domain_id=interview.domain_id,
            question_text=ai_response['question_text'],
            difficulty_level=interview.difficulty_level,
            question_type=question_type,
            expected_answer="AI Generated - Dynamic",
            keywords="[]"
        )
        db.session.add(question)
        db.session.commit()
        
        print(f"Generated question: {question.question_text[:50]}...")
        return question
    
    def submit_answer(self, interview_id, question_id, answer_text, time_taken_seconds=None):
        """Submit an answer for a question - now with AI evaluation!"""
        # Get question and interview details
        question = Question.query.get(question_id)
        interview = Interview.query.get(interview_id)
        domain = Domain.query.get(interview.domain_id)
        
        print(f"Evaluating answer for question: {question.question_text[:50]}...")
        
        # Use AI to evaluate the answer
        evaluation = ai_service.evaluate_answer(
            question=question.question_text,
            answer=answer_text,
            domain=domain.name,
            difficulty=interview.difficulty_level,
            expected_keywords=question.keywords_list if hasattr(question, 'keywords_list') else []
        )
        
        answer = Answer(
            interview_id=interview_id,
            question_id=question_id,
            answer_text=answer_text,
            time_taken_seconds=time_taken_seconds,
            score=evaluation['score'],
            feedback=evaluation['detailed_feedback']
        )
        db.session.add(answer)
        db.session.commit()
        
        print(f"Answer evaluated with score: {evaluation['score']}/10")
        return answer, evaluation
    
    def complete_interview(self, interview_id):
        """Complete an interview and calculate overall score with AI feedback."""
        # Get all answers for this interview
        answers = Answer.query.filter_by(interview_id=interview_id).all()
        interview = Interview.query.get(interview_id)
        domain = Domain.query.get(interview.domain_id)
        
        if not answers:
            overall_score = 0
        else:
            # Calculate average score
            total_score = sum(answer.score for answer in answers if answer.score)
            overall_score = int(total_score / len(answers))
        
        # Prepare data for AI feedback
        interview_data = {
            'answers': [
                {
                    'question': Question.query.get(ans.question_id).question_text,
                    'answer': ans.answer_text,
                    'score': ans.score
                } for ans in answers
            ],
            'overall_score': overall_score,
            'domain': domain.name
        }
        
        print(f"Generating AI feedback for completed interview, score: {overall_score}")
        
        # Generate comprehensive AI feedback
        ai_feedback = ai_service.generate_interview_feedback(interview_data)
        
        # Update interview status and score
        interview.status = 'completed'
        interview.overall_score = overall_score
        interview.completed_at = datetime.utcnow()
        interview.feedback = f"""AI Assessment: {ai_feedback['overall_assessment']}

Key Strengths:
• {chr(10).join(f"  {strength}" for strength in ai_feedback['key_strengths'])}

Areas for Improvement:
• {chr(10).join(f"  {area}" for area in ai_feedback['areas_for_improvement'])}

Recommendations:
• {chr(10).join(f"  {rec}" for rec in ai_feedback['specific_recommendations'])}

Next Steps: {ai_feedback['next_steps']}

Industry Comparison: {ai_feedback['industry_comparison']}"""
        
        db.session.commit()
        return interview, ai_feedback
    
    def get_interview_results(self, interview_id):
        """Get detailed interview results."""
        interview = Interview.query.get(interview_id)
        if not interview:
            return None
        
        answers = Answer.query.filter_by(interview_id=interview_id).all()
        
        return {
            "interview": interview,
            "answers": answers,
            "total_questions": len(answers),
            "average_score": interview.overall_score,
            "status": interview.status
        }

# Create global instance
interview_service = InterviewService()

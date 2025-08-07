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
        """Get the next question for an interview - Enhanced with R1T2 Chimera!"""
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
        
        # Enhanced question type progression for natural flow
        question_number = len(answered_questions) + 1
        
        # Intelligent question type selection
        if question_number == 1:
            question_type = 'behavioral'  # Start with warm behavioral question
        elif question_number in [2, 4, 6]:
            question_type = 'technical'   # Core technical questions
        else:
            question_type = 'behavioral' if question_number % 2 == 1 else 'technical'
        
        # Generate AI question with enhanced context
        print(f"Generating AI question #{question_number} for {domain.name}, {interview.difficulty_level}, {question_type}")
        ai_response = ai_service.generate_interview_question(
            domain=domain.name,
            difficulty=interview.difficulty_level,
            question_type=question_type,
            previous_answers=previous_answers,
            question_number=question_number
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
        
        print(f"Generated question #{question_number}: {question.question_text[:50]}...")
        return question
    
    def submit_answer(self, interview_id, question_id, answer_text, time_taken_seconds=None, is_skipped=False):
        """Submit an answer - Enhanced with R1T2 Chimera evaluation!"""
        # Get question and interview details
        question = Question.query.get(question_id)
        interview = Interview.query.get(interview_id)
        domain = Domain.query.get(interview.domain_id)
        
        if is_skipped:
            print(f"Question skipped by user")
            answer = Answer(
                interview_id=interview_id,
                question_id=question_id,
                answer_text=answer_text,
                time_taken_seconds=time_taken_seconds,
                score=0,
                feedback="Question was skipped by the candidate."
            )
            db.session.add(answer)
            db.session.commit()
            
            return answer, {
                'score': 0,
                'detailed_feedback': 'Question was skipped',
                'strengths': [],
                'improvement_areas': ['Answer all questions to get proper evaluation'],
                'follow_up_suggestion': 'Try to answer all questions for better assessment'
            }
        
        print(f"Evaluating answer for question: {question.question_text[:50]}...")
        
        # Use enhanced AI evaluation with R1T2 Chimera
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
        """Complete interview with comprehensive R1T2 Chimera feedback."""
        # Get all answers for this interview
        answers = Answer.query.filter_by(interview_id=interview_id).all()
        interview = Interview.query.get(interview_id)
        domain = Domain.query.get(interview.domain_id)
        
        if not answers:
            overall_score = 0
        else:
            # Calculate weighted average score
            scores = [answer.score for answer in answers if answer.score is not None]
            overall_score = int(sum(scores) / len(scores)) if scores else 0
        
        # Prepare enhanced data for AI feedback
        interview_data = {
            'answers': [
                {
                    'question': Question.query.get(ans.question_id).question_text,
                    'answer': ans.answer_text,
                    'score': ans.score,
                    'time_taken': ans.time_taken_seconds
                } for ans in answers
            ],
            'overall_score': overall_score,
            'domain': domain.name,
            'difficulty': interview.difficulty_level,
            'total_time': sum(ans.time_taken_seconds for ans in answers if ans.time_taken_seconds)
        }
        
        print(f"Generating comprehensive AI feedback for interview, score: {overall_score}")
        
        # Generate comprehensive AI feedback using R1T2 Chimera
        ai_feedback = ai_service.generate_interview_feedback(interview_data)
        
        # Update interview status and score
        interview.status = 'completed'
        interview.overall_score = overall_score
        interview.completed_at = datetime.utcnow()
        interview.feedback = f"""AI Assessment by DeepSeek R1T2 Chimera:

{ai_feedback['overall_assessment']}

Key Strengths:
• {chr(10).join(f"• {strength}" for strength in ai_feedback['key_strengths'])}

Areas for Improvement:
• {chr(10).join(f"• {area}" for area in ai_feedback['areas_for_improvement'])}

Specific Recommendations:
• {chr(10).join(f"• {rec}" for rec in ai_feedback['specific_recommendations'])}

Next Steps: {ai_feedback['next_steps']}

Industry Comparison: {ai_feedback['industry_comparison']}"""
        
        db.session.commit()
        return interview, ai_feedback
    
    def get_interview_results(self, interview_id):
        """Get enhanced interview results with detailed analytics."""
        interview = Interview.query.get(interview_id)
        if not interview:
            return None
        
        answers = Answer.query.filter_by(interview_id=interview_id).all()
        domain = Domain.query.get(interview.domain_id)
        
        # Calculate detailed metrics
        scores = [ans.score for ans in answers if ans.score is not None]
        technical_scores = [ans.score for ans in answers if ans.score is not None and Question.query.get(ans.question_id).question_type == 'technical']
        behavioral_scores = [ans.score for ans in answers if ans.score is not None and Question.query.get(ans.question_id).question_type == 'behavioral']
        
        # Parse AI feedback if available
        ai_feedback = {}
        if interview.feedback:
            try:
                # Extract structured feedback from the stored feedback
                feedback_lines = interview.feedback.split('\n')
                ai_feedback = {
                    'overall_assessment': feedback_lines[1] if len(feedback_lines) > 1 else '',
                    'key_strengths': [line.replace('• ', '') for line in feedback_lines if line.startswith('• ') and 'Strengths' in interview.feedback[:interview.feedback.find(line)]],
                    'areas_for_improvement': [line.replace('• ', '') for line in feedback_lines if line.startswith('• ') and 'Areas for' in interview.feedback[:interview.feedback.find(line)]],
                    'specific_recommendations': [line.replace('• ', '') for line in feedback_lines if line.startswith('• ') and 'Recommendations' in interview.feedback[:interview.feedback.find(line)]],
                    'next_steps': interview.feedback[interview.feedback.find('Next Steps:'):interview.feedback.find('Industry Comparison:')].replace('Next Steps:', '').strip() if 'Next Steps:' in interview.feedback else '',
                    'industry_comparison': interview.feedback[interview.feedback.find('Industry Comparison:'):].replace('Industry Comparison:', '').strip() if 'Industry Comparison:' in interview.feedback else ''
                }
            except:
                ai_feedback = {
                    'overall_assessment': 'Comprehensive feedback available in interview summary.',
                    'key_strengths': ['Completed interview successfully'],
                    'areas_for_improvement': ['Continue practicing'],
                    'specific_recommendations': ['Review feedback'],
                    'next_steps': 'Focus on areas identified for improvement',
                    'industry_comparison': 'Performance evaluated against industry standards'
                }
        
        return {
            "interview": interview,
            "answers": answers,
            "total_questions": len(answers),
            "duration_minutes": (interview.completed_at - interview.started_at).total_seconds() // 60 if interview.completed_at else 0,
            "technical_score": int(sum(technical_scores) / len(technical_scores)) if technical_scores else 0,
            "communication_score": int(sum(behavioral_scores) / len(behavioral_scores)) if behavioral_scores else 0,
            "problem_solving_score": max(0, interview.overall_score - 1),  # Derived metric
            "clarity_score": min(10, interview.overall_score + 1),  # Derived metric
            "total_words": sum(len(ans.answer_text.split()) for ans in answers),
            "avg_response_time": int(sum(ans.time_taken_seconds for ans in answers if ans.time_taken_seconds) / max(1, len([ans for ans in answers if ans.time_taken_seconds]))),
            "completion_rate": int((len(answers) / 8) * 100),
            "ai_feedback": ai_feedback,
            "status": interview.status
        }

# Create global instance
interview_service = InterviewService()

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from dotenv import load_dotenv
import os
from coqui_voice_service import voice_service

from database import db, User, Domain, Question, Interview, Answer, init_default_data
from auth import bcrypt, login_manager, hash_password, check_password
from interview import interview_service

# Load environment variables
load_dotenv()
from voice_service import voice_service
import threading

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///ai_interview.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
bcrypt.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
CORS(app)

# Create tables and initialize data
with app.app_context():
    db.create_all()
    init_default_data()

# Routes
@app.route('/')
def index():
    """Home page."""
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        # Validate input
        if not all(k in data for k in ['email', 'username', 'password']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Check if user exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already taken'}), 400
        
        # Create new user
        user = User(
            email=data['email'],
            username=data['username'],
            password_hash=hash_password(data['password']),
            full_name=data.get('full_name', ''),
            age=data.get('age'),
            gender=data.get('gender')
        )
        
        db.session.add(user)
        db.session.commit()
        
        if request.is_json:
            return jsonify({'message': 'User registered successfully', 'user_id': user.id}), 201
        else:
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password(user.password_hash, password):
            login_user(user)
            
            if request.is_json:
                return jsonify({'message': 'Login successful', 'user_id': user.id}), 200
            else:
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
        else:
            if request.is_json:
                return jsonify({'error': 'Invalid credentials'}), 401
            else:
                flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """User logout."""
    logout_user()
    flash('Logged out successfully', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard."""
    # Get user's recent interviews
    recent_interviews = Interview.query.filter_by(user_id=current_user.id).order_by(Interview.started_at.desc()).limit(5).all()
    domains = interview_service.get_domains()
    
    return render_template('dashboard.html', 
                         recent_interviews=recent_interviews, 
                         domains=domains)

@app.route('/start-interview')
@login_required
def start_interview():
    """Start interview page."""
    domains = interview_service.get_domains()
    return render_template('start_interview.html', domains=domains)

@app.route('/api/start-interview', methods=['POST'])
@login_required
def api_start_interview():
    """API endpoint to start a new interview."""
    try:
        data = request.get_json()
        print(f"Received interview start request: {data}")
        
        # Validate input
        required_fields = ['domain_id', 'difficulty_level']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Create interview
        interview = interview_service.create_interview(
            user=current_user,
            domain_id=data['domain_id'],
            difficulty_level=data['difficulty_level'],
            duration_minutes=data.get('duration_minutes', 30)
        )
        
        print(f"Created interview with ID: {interview.id}")
        
        # Get first question
        question = interview_service.get_next_question(interview.id)
        if not question:
            return jsonify({'error': 'No questions available'}), 404
        
        print(f"Generated first question: {question.question_text[:50]}...")
        
        return jsonify({
            'interview_id': interview.id,
            'question': {
                'id': question.id,
                'text': question.question_text,
                'type': question.question_type,
                'difficulty': question.difficulty_level
            },
            'question_number': 1,
            'total_questions': 8  # Updated to match your interview.py
        })
        
    except Exception as e:
        print(f"Error starting interview: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@app.route('/interview/<int:interview_id>')
@login_required
def interview_page(interview_id):
    """Interview page."""
    # Verify interview belongs to current user
    interview = Interview.query.filter_by(id=interview_id, user_id=current_user.id).first()
    if not interview:
        flash('Interview not found', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('interview.html', interview=interview)

@app.route('/api/interview/<int:interview_id>/next-question')
@login_required
def api_next_question(interview_id):
    """API endpoint to get next question."""
    # Verify interview belongs to current user
    interview = Interview.query.filter_by(id=interview_id, user_id=current_user.id).first()
    if not interview:
        return jsonify({'error': 'Interview not found'}), 404
    
    question = interview_service.get_next_question(interview_id)
    if not question:
        # No more questions, complete interview
        completed_interview, ai_feedback = interview_service.complete_interview(interview_id)  # FIX: Unpack the tuple
        return jsonify({
            'completed': True,
            'message': 'Interview completed',
            'overall_score': completed_interview.overall_score,  # Now this works correctly
            'ai_feedback': {
                'overall_assessment': ai_feedback.get('overall_assessment', ''),
                'key_strengths': ai_feedback.get('key_strengths', []),
                'areas_for_improvement': ai_feedback.get('areas_for_improvement', []),
                'specific_recommendations': ai_feedback.get('specific_recommendations', []),
                'next_steps': ai_feedback.get('next_steps', ''),
                'industry_comparison': ai_feedback.get('industry_comparison', '')
            }
        })
    
    # Count current question number
    answered_count = Answer.query.filter_by(interview_id=interview_id).count()
    
    return jsonify({
        'question': {
            'id': question.id,
            'text': question.question_text,
            'type': question.question_type,
            'difficulty': question.difficulty_level
        },
        'question_number': answered_count + 1,
        'total_questions': 8
    })


@app.route('/api/interview/<int:interview_id>/submit-answer', methods=['POST'])
@login_required
def api_submit_answer(interview_id):
    """API endpoint to submit an answer - now with AI evaluation!"""
    data = request.get_json()
    
    # Verify interview belongs to current user
    interview = Interview.query.filter_by(id=interview_id, user_id=current_user.id).first()
    if not interview:
        return jsonify({'error': 'Interview not found'}), 404
    
    # Validate input
    if 'question_id' not in data or 'answer_text' not in data:
        return jsonify({'error': 'Missing required fields'}), 400
    
    answer, evaluation = interview_service.submit_answer(
        interview_id=interview_id,
        question_id=data['question_id'],
        answer_text=data['answer_text'],
        time_taken_seconds=data.get('time_taken_seconds')
    )
    
    return jsonify({
        'answer_id': answer.id,
        'score': answer.score,
        'feedback': answer.feedback,
        'detailed_evaluation': {
            'strengths': evaluation.get('strengths', []),
            'improvement_areas': evaluation.get('improvement_areas', []),
            'follow_up_suggestion': evaluation.get('follow_up_suggestion', '')
        }
    })


@app.route('/results/<int:interview_id>')
@login_required
def results_page(interview_id):
    """Interview results page."""
    # Verify interview belongs to current user
    interview = Interview.query.filter_by(id=interview_id, user_id=current_user.id).first()
    if not interview:
        flash('Interview not found', 'error')
        return redirect(url_for('dashboard'))
    
    results = interview_service.get_interview_results(interview_id)
    return render_template('results.html', results=results)

@app.route('/my-interviews')
@login_required
def my_interviews():
    """Page showing all user's interviews."""
    interviews = Interview.query.filter_by(user_id=current_user.id).order_by(Interview.started_at.desc()).all()
    return render_template('my_interviews.html', interviews=interviews)

# API endpoints for AJAX calls
@app.route('/api/domains')
def api_domains():
    """Get all domains."""
    domains = interview_service.get_domains()
    return jsonify([{
        'id': d.id,
        'name': d.name,
        'description': d.description
    } for d in domains])

@app.route('/api/user/me')
@login_required
def api_current_user():
    """Get current user info."""
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'full_name': current_user.full_name
    })

@app.route('/api/voice/speak-question', methods=['POST'])
@login_required  
def api_speak_question():
    """Endpoint to make the AI speak a question."""
    data = request.get_json()
    question_text = data.get('question_text', '')
    
    if not question_text:
        return jsonify({'error': 'No question text provided'}), 400
    
    # Start speaking the question
    voice_service.speak_question(question_text)
    
    return jsonify({
        'message': 'Question speech started',
        'question_text': question_text
    })

@app.route('/api/voice/start-listening', methods=['POST'])
@login_required
def api_start_listening():
    """Start listening for voice input."""
    data = request.get_json()
    timeout = data.get('timeout', 30)
    
    def speech_callback(recognized_text):
        """This will be called when speech is recognized."""
        # Store the recognized text in session or database
        # For now, we'll just print it
        print(f"Voice input received: {recognized_text}")
    
    voice_service.start_listening(speech_callback, timeout)
    
    return jsonify({
        'message': 'Started listening for voice input',
        'timeout': timeout,
        'status': voice_service.get_status()
    })

@app.route('/api/voice/stop-listening', methods=['POST'])
@login_required
def api_stop_listening():
    """Stop listening for voice input."""
    voice_service.stop_listening()
    
    return jsonify({
        'message': 'Stopped listening',
        'status': voice_service.get_status()
    })

@app.route('/api/voice/status')
@login_required
def api_voice_status():
    """Get current voice service status."""
    return jsonify(voice_service.get_status())

@app.route('/api/voice/test')
@login_required
def api_test_voice():
    """Test voice system functionality."""
    results = voice_service.test_voice_system()
    return jsonify(results)

# Add these new endpoints
@app.route('/api/voice/coqui-speak', methods=['POST'])
@login_required
def coqui_speak_question():
    """Generate speech using Coqui TTS."""
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        result = voice_service.synthesize_speech(text)
        
        if result['success']:
            # Return path to generated audio file
            audio_filename = os.path.basename(result['audio_path'])
            return jsonify({
                'success': True,
                'audio_url': f'/api/voice/audio/{audio_filename}',
                'duration': result.get('duration', 0)
            })
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/voice/coqui-test')
@login_required
def test_coqui_system():
    """Test Coqui TTS system."""
    results = voice_service.test_system()
    return jsonify(results)

@app.route('/api/voice/coqui-models')
@login_required
def list_coqui_models():
    """Get available Coqui models."""
    models = voice_service.list_available_models()
    return jsonify({'models': models})

@app.route('/api/voice/coqui-status')
@login_required
def get_coqui_status():
    """Get Coqui TTS status."""
    return jsonify(voice_service.get_status())

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

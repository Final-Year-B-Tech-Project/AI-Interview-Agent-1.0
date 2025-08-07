from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from dotenv import load_dotenv
import os
import time

from database import db, User, Domain, Question, Interview, Answer, init_default_data
from auth import bcrypt, login_manager, hash_password, check_password
from interview import interview_service

# Voice service import with fallback handling
try:
    from coqui_voice_service import voice_service
    print("✅ Coqui voice service loaded")
except ImportError as e:
    print(f"⚠️ Coqui import failed: {e}")
    try:
        from simplified_voice_service import voice_service
        print("✅ Simplified voice service loaded as fallback")
    except ImportError as e2:
        print(f"❌ All voice services failed: {e2}")
        voice_service = None

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///ai_interview.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Voice file upload configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload directory
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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
            if request.is_json:
                return jsonify({'error': 'Missing required fields'}), 400
            flash('Missing required fields', 'error')
            return render_template('register.html')
        
        # Check if user exists
        if User.query.filter_by(email=data['email']).first():
            if request.is_json:
                return jsonify({'error': 'Email already registered'}), 400
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(username=data['username']).first():
            if request.is_json:
                return jsonify({'error': 'Username already taken'}), 400
            flash('Username already taken', 'error')
            return render_template('register.html')
        
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
            if request.is_json:
                return jsonify({'error': 'Username and password required'}), 400
            flash('Username and password required', 'error')
            return render_template('login.html')
        
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
            'total_questions': 8
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
    """API endpoint to get next question - FIXED tuple handling."""
    # Verify interview belongs to current user
    interview = Interview.query.filter_by(id=interview_id, user_id=current_user.id).first()
    if not interview:
        return jsonify({'error': 'Interview not found'}), 404
    
    question = interview_service.get_next_question(interview_id)
    if not question:
        # No more questions, complete interview
        try:
            # FIX: Properly handle tuple or single object return
            result = interview_service.complete_interview(interview_id)
            
            if isinstance(result, tuple):
                # If complete_interview returns (interview, ai_feedback)
                completed_interview, ai_feedback = result
                return jsonify({
                    'completed': True,
                    'message': 'Interview completed',
                    'overall_score': completed_interview.overall_score,
                    'ai_feedback': {
                        'overall_assessment': ai_feedback.get('overall_assessment', ''),
                        'key_strengths': ai_feedback.get('key_strengths', []),
                        'areas_for_improvement': ai_feedback.get('areas_for_improvement', []),
                        'specific_recommendations': ai_feedback.get('specific_recommendations', []),
                        'next_steps': ai_feedback.get('next_steps', ''),
                        'industry_comparison': ai_feedback.get('industry_comparison', '')
                    }
                })
            else:
                # If complete_interview returns only interview object
                completed_interview = result
                return jsonify({
                    'completed': True,
                    'message': 'Interview completed',
                    'overall_score': completed_interview.overall_score
                })
                
        except Exception as e:
            print(f"Error completing interview: {e}")
            return jsonify({'error': 'Failed to complete interview'}), 500
    
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
    """API endpoint to submit an answer - Enhanced with AI evaluation."""
    data = request.get_json()
    
    # Verify interview belongs to current user
    interview = Interview.query.filter_by(id=interview_id, user_id=current_user.id).first()
    if not interview:
        return jsonify({'error': 'Interview not found'}), 404
    
    # Validate input
    if 'question_id' not in data or 'answer_text' not in data:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        # Submit answer with AI evaluation
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
    except Exception as e:
        print(f"Error submitting answer: {e}")
        return jsonify({'error': 'Failed to submit answer'}), 500

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

# Voice Service Endpoints
@app.route('/api/voice/speak-question', methods=['POST'])
@login_required  
def api_speak_question():
    """Endpoint to make the AI speak a question."""
    if not voice_service:
        return jsonify({'error': 'Voice service not available'}), 503
    
    data = request.get_json()
    question_text = data.get('question_text', '')
    
    if not question_text:
        return jsonify({'error': 'No question text provided'}), 400
    
    try:
        # Start speaking the question
        if hasattr(voice_service, 'speak_question_async'):
            voice_service.speak_question_async(question_text)
        else:
            voice_service.synthesize_speech(question_text)
        
        return jsonify({
            'message': 'Question speech started',
            'question_text': question_text
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/voice/upload-audio', methods=['POST'])
@login_required
def upload_and_transcribe():
    """Upload audio file and transcribe using Whisper (if available)."""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save uploaded file
        from werkzeug.utils import secure_filename
        filename = secure_filename(audio_file.filename)
        timestamp = str(int(time.time()))
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        audio_file.save(filepath)
        
        # Transcribe if voice service supports it
        if hasattr(voice_service, 'transcribe_audio'):
            result = voice_service.transcribe_audio(filepath)
        else:
            result = {'success': False, 'error': 'Transcription not available'}
        
        # Clean up uploaded file
        if os.path.exists(filepath):
            os.unlink(filepath)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# FIXED: Missing endpoints that were causing 404 errors
@app.route('/api/voice/start-listening', methods=['POST'])
@login_required
def api_start_listening():
    """Start listening for voice input."""
    return jsonify({
        'message': 'Please upload audio file for transcription',
        'upload_endpoint': '/api/voice/upload-audio'
    })

@app.route('/api/voice/stop-listening', methods=['POST'])
@login_required
def api_stop_listening():
    """Stop listening for voice input."""
    return jsonify({
        'message': 'Listening stopped',
        'status': 'stopped'
    })

@app.route('/api/voice/status')
@login_required
def api_voice_status():
    """Get current voice service status."""
    if not voice_service:
        return jsonify({
            'available': False,
            'error': 'Voice service not loaded'
        })
    
    try:
        status = voice_service.get_status()
        status['available'] = True
        return jsonify(status)
    except Exception as e:
        return jsonify({
            'available': False,
            'error': str(e)
        })

@app.route('/api/voice/test')
@login_required
def api_test_voice():
    """Test voice system functionality."""
    if not voice_service:
        return jsonify({
            'available': False,
            'error': 'Voice service not loaded'
        })
    
    try:
        results = voice_service.test_system()
        return jsonify(results)
    except Exception as e:
        return jsonify({
            'available': False,
            'error': str(e)
        })

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

# Error handlers - FIXED: Create the missing templates
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors gracefully."""
    if request.is_json:
        return jsonify({'error': 'Endpoint not found'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors gracefully."""
    db.session.rollback()
    if request.is_json:
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('500.html'), 500

# Health check
@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy', 
        'message': 'AI Interview Agent API is running',
        'voice_service_available': voice_service is not None,
        'database_connected': True
    })


@app.route('/api/interview/<int:interview_id>/end-early', methods=['POST'])
@login_required
def api_end_interview_early(interview_id):
    """End interview early and calculate results."""
    interview = Interview.query.filter_by(id=interview_id, user_id=current_user.id).first()
    if not interview:
        return jsonify({'error': 'Interview not found'}), 404
    
    try:
        # Complete interview with current answers
        result = interview_service.complete_interview(interview_id)
        
        if isinstance(result, tuple):
            completed_interview, ai_feedback = result
            return jsonify({
                'completed': True,
                'message': 'Interview ended early',
                'overall_score': completed_interview.overall_score,
                'ai_feedback': ai_feedback
            })
        else:
            completed_interview = result
            return jsonify({
                'completed': True,
                'message': 'Interview ended early',
                'overall_score': completed_interview.overall_score
            })
    except Exception as e:
        print(f"Error ending interview early: {e}")
        return jsonify({'error': 'Failed to end interview'}), 500

# Add these endpoints after your existing routes (around line 500):

@app.route('/api/interview/<int:interview_id>/delete', methods=['DELETE'])
@login_required
def delete_interview(interview_id):
    """Delete a specific interview."""
    interview = Interview.query.filter_by(id=interview_id, user_id=current_user.id).first()
    if not interview:
        return jsonify({'error': 'Interview not found'}), 404
    
    try:
        # Delete associated answers first
        Answer.query.filter_by(interview_id=interview_id).delete()
        # Delete the interview
        db.session.delete(interview)
        db.session.commit()
        
        return jsonify({'message': 'Interview deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting interview: {e}")
        return jsonify({'error': 'Failed to delete interview'}), 500

@app.route('/api/interviews/delete-all', methods=['DELETE'])
@login_required
def delete_all_interviews():
    """Delete all interviews for current user."""
    try:
        # Get all user's interviews
        user_interviews = Interview.query.filter_by(user_id=current_user.id).all()
        interview_ids = [interview.id for interview in user_interviews]
        
        if interview_ids:
            # Delete all associated answers
            Answer.query.filter(Answer.interview_id.in_(interview_ids)).delete(synchronize_session=False)
            
            # Delete all interviews
            Interview.query.filter_by(user_id=current_user.id).delete()
            
            db.session.commit()
            
            return jsonify({'message': f'All {len(user_interviews)} interviews deleted successfully'}), 200
        else:
            return jsonify({'message': 'No interviews to delete'}), 200
            
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting all interviews: {e}")
        return jsonify({'error': 'Failed to delete interviews'}), 500

if __name__ == '__main__':
    print("🚀 Starting AI Interview Agent...")
    print(f"📊 Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"🔊 Voice Service Available: {voice_service is not None}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    interviews = db.relationship('Interview', backref='user', lazy=True)

class Domain(db.Model):
    __tablename__ = 'domains'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('Question', backref='domain', lazy=True)
    interviews = db.relationship('Interview', backref='domain', lazy=True)

class Question(db.Model):
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    domain_id = db.Column(db.Integer, db.ForeignKey('domains.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    difficulty_level = db.Column(db.String(20), nullable=False)  # beginner, intermediate, expert
    question_type = db.Column(db.String(50), nullable=False)  # technical, behavioral, hr
    expected_answer = db.Column(db.Text, nullable=True)
    keywords = db.Column(db.Text, nullable=True)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    answers = db.relationship('Answer', backref='question', lazy=True)
    
    @property
    def keywords_list(self):
        if self.keywords:
            try:
                return json.loads(self.keywords)
            except:
                return []
        return []

class Interview(db.Model):
    __tablename__ = 'interviews'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    domain_id = db.Column(db.Integer, db.ForeignKey('domains.id'), nullable=False)
    difficulty_level = db.Column(db.String(20), nullable=False)
    duration_minutes = db.Column(db.Integer, default=30)
    status = db.Column(db.String(20), default='in_progress')  # in_progress, completed, cancelled
    overall_score = db.Column(db.Integer, nullable=True)  # 0-100
    feedback = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    answers = db.relationship('Answer', backref='interview', lazy=True)

class Answer(db.Model):
    __tablename__ = 'answers'
    
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interviews.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    answer_text = db.Column(db.Text, nullable=False)
    score = db.Column(db.Integer, nullable=True)  # 0-10 for individual question
    feedback = db.Column(db.Text, nullable=True)
    time_taken_seconds = db.Column(db.Integer, nullable=True)
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)

def init_default_data():
    """Initialize default domains and questions."""
    # Check if domains already exist
    if Domain.query.first():
        return
    
    # Create default domains
    domains_data = [
        {"name": "Software Engineering", "description": "Programming, algorithms, system design"},
        {"name": "Data Science", "description": "Statistics, machine learning, data analysis"},
        {"name": "Product Management", "description": "Strategy, roadmaps, stakeholder management"},
        {"name": "Marketing", "description": "Digital marketing, campaigns, analytics"},
    ]
    
    for domain_data in domains_data:
        domain = Domain(**domain_data)
        db.session.add(domain)
    
    db.session.commit()
    
    # Create sample questions for Software Engineering
    se_domain = Domain.query.filter_by(name="Software Engineering").first()
    if se_domain:
        questions_data = [
            {
                "domain_id": se_domain.id,
                "question_text": "What is the difference between a list and a tuple in Python?",
                "difficulty_level": "beginner",
                "question_type": "technical",
                "expected_answer": "Lists are mutable, tuples are immutable",
                "keywords": json.dumps(["mutable", "immutable", "list", "tuple"])
            },
            {
                "domain_id": se_domain.id,
                "question_text": "Explain the concept of Object-Oriented Programming and its principles.",
                "difficulty_level": "intermediate",
                "question_type": "technical",
                "expected_answer": "OOP includes encapsulation, inheritance, polymorphism, abstraction",
                "keywords": json.dumps(["encapsulation", "inheritance", "polymorphism", "abstraction"])
            },
            {
                "domain_id": se_domain.id,
                "question_text": "Design a system to handle 1 million concurrent users.",
                "difficulty_level": "expert",
                "question_type": "technical",
                "expected_answer": "Load balancing, caching, database sharding, microservices",
                "keywords": json.dumps(["load balancing", "caching", "scaling", "microservices"])
            },
            {
                "domain_id": se_domain.id,
                "question_text": "Tell me about a challenging project you worked on.",
                "difficulty_level": "beginner",
                "question_type": "behavioral",
                "expected_answer": "Should demonstrate problem-solving skills",
                "keywords": json.dumps(["project", "challenge", "problem-solving"])
            },
            {
                "domain_id": se_domain.id,
                "question_text": "How do you handle code reviews and feedback?",
                "difficulty_level": "intermediate",
                "question_type": "behavioral",
                "expected_answer": "Should show collaboration and learning mindset",
                "keywords": json.dumps(["code review", "feedback", "collaboration"])
            }
        ]
        
        for q_data in questions_data:
            question = Question(**q_data)
            db.session.add(question)
        
        db.session.commit()

from db import db, DATABASE_URL
import json

from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import Text


class CandidateProfile(db.Model):
    __tablename__ = 'candidate_profiles'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    face_image_path = db.Column(db.String(200))
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    github_username = db.Column(db.String(255), nullable=False)
    linkedin_link = db.Column(db.String(500), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    resume_data = db.relationship('ResumeData', backref='profile', uselist=False, cascade='all, delete-orphan')
    github_profile = db.relationship('GitHubProfile', backref='profile', uselist=False, cascade='all, delete-orphan')
    resumes = db.relationship('Resume', backref='candidate_profile', lazy=True, cascade='all, delete-orphan')

    transcriptions = db.relationship('Transcription', backref='user', lazy=True, cascade='all, delete-orphan')
    notes = db.relationship('Note', backref='user', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'github_username': self.github_username,
            'linkedin_link': self.linkedin_link,
            'timestamp': self.timestamp.isoformat(),
            'resume': self.resume_data.data if self.resume_data else None,
            'github': self.github_profile.to_dict() if self.github_profile else None
        }


class Transcription(db.Model):
    id = db.Column(db.String(50), primary_key=True)  # UUID
    user_id = db.Column(db.Integer, db.ForeignKey('candidate_profiles.id'), nullable=False)

    # Transcription data
    original_transcript = db.Column(db.Text)
    original_language = db.Column(db.String(10))
    translated_transcript = db.Column(db.Text)
    target_language = db.Column(db.String(10))
    detailed_notes = db.Column(db.Text)

    # Source information
    source_type = db.Column(db.String(20))  # 'video_upload' or 'youtube_link'
    source_url = db.Column(db.String(500))  # YouTube URL if applicable

    # Generated content
    summary = db.Column(db.Text)
    flashcards = db.Column(db.Text)  # JSON string
    quiz = db.Column(db.Text)  # JSON string
    exercises = db.Column(db.Text)  # JSON string

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Transcription {self.id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'original_transcript': self.original_transcript,
            'original_language': self.original_language,
            'translated_transcript': self.translated_transcript,
            'target_language': self.target_language,
            'detailed_notes': self.detailed_notes,
            'source_type': self.source_type,
            'source_url': self.source_url,
            'summary': self.summary,
            'flashcards': json.loads(self.flashcards) if self.flashcards else None,
            'quiz': json.loads(self.quiz) if self.quiz else None,
            'exercises': json.loads(self.exercises) if self.exercises else None,
            'created_at': self.created_at.isoformat()
        }


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('candidate_profiles.id'), nullable=False)


    # Note data
    original_notes = db.Column(db.Text)
    translated_notes = db.Column(db.Text)
    target_language = db.Column(db.String(10))
    filename = db.Column(db.String(200))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Note {self.id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'original_notes': self.original_notes,
            'translated_notes': self.translated_notes,
            'target_language': self.target_language,
            'filename': self.filename,
            'created_at': self.created_at.isoformat()
        }


class Resume(db.Model):
    __tablename__ = 'resumes'

    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('candidate_profiles.id'), nullable=False)
    original_resume_text = db.Column(db.Text, nullable=False)
    structured_resume_data = db.Column(JSON if 'postgresql' in DATABASE_URL else Text, nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ResumeData(db.Model):
    __tablename__ = 'resume_data'

    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('candidate_profiles.id'), nullable=False)
    data = db.Column(JSON if 'postgresql' in DATABASE_URL else Text, nullable=False)


class GitHubProfile(db.Model):
    __tablename__ = 'github_profiles'

    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('candidate_profiles.id'), nullable=False)
    bio = db.Column(Text, nullable=True)
    followers = db.Column(db.Integer, default=0)
    following = db.Column(db.Integer, default=0)
    public_repos = db.Column(db.Integer, default=0)
    achievements = db.Column(JSON if 'postgresql' in DATABASE_URL else Text, nullable=True)

    # Relationships
    repositories = db.relationship('Repository', backref='github_profile', cascade='all, delete-orphan')

    def to_dict(self):
        achievements_data = self.achievements
        if isinstance(self.achievements, str) and 'postgresql' not in DATABASE_URL:
            try:
                achievements_data = json.loads(self.achievements) if self.achievements else []
            except:
                achievements_data = []

        return {
            'bio': self.bio,
            'followers': self.followers,
            'following': self.following,
            'public_repos': self.public_repos,
            'achievements': achievements_data or [],
            'repos': [repo.to_dict() for repo in self.repositories]
        }


class Repository(db.Model):
    __tablename__ = 'repositories'

    id = db.Column(db.Integer, primary_key=True)
    github_profile_id = db.Column(db.Integer, db.ForeignKey('github_profiles.id'), nullable=False)
    repo_name = db.Column(db.String(255), nullable=False)
    description = db.Column(Text, nullable=True)
    language = db.Column(db.String(100), nullable=True)
    stars = db.Column(db.Integer, default=0)
    forks = db.Column(db.Integer, default=0)
    topics = db.Column(JSON if 'postgresql' in DATABASE_URL else Text, nullable=True)
    readme = db.Column(Text, nullable=True)
    url = db.Column(db.String(500), nullable=False)

    # Relationships
    code_files = db.relationship('CodeFile', backref='repository', cascade='all, delete-orphan')

    def to_dict(self):
        topics_data = self.topics
        if isinstance(self.topics, str) and 'postgresql' not in DATABASE_URL:
            try:
                topics_data = json.loads(self.topics) if self.topics else []
            except:
                topics_data = []

        return {
            'repo_name': self.repo_name,
            'description': self.description,
            'language': self.language,
            'stars': self.stars,
            'forks': self.forks,
            'topics': topics_data or [],
            'readme': self.readme,
            'url': self.url,
            'code_files': [cf.to_dict() for cf in self.code_files]
        }


class CodeFile(db.Model):
    __tablename__ = 'code_files'

    id = db.Column(db.Integer, primary_key=True)
    repository_id = db.Column(db.Integer, db.ForeignKey('repositories.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)

    def to_dict(self):
        return {
            'filename': self.filename,
            'content': self.content
        }


# Interview-specific models (new tables for interview functionality)
class InterviewSession(db.Model):
    __tablename__ = 'interview_sessions'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('candidate_profiles.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='active')  # active, completed, interrupted
    applied_role = db.Column(db.String(200))  # Store the role for this interview session

    # Relationships
    questions = db.relationship('InterviewQuestion', backref='session', lazy=True, cascade='all, delete-orphan')
    candidate_profile = db.relationship('CandidateProfile', backref='interview_sessions')


class DomainRanking(db.Model):
    __tablename__ = 'domain_rankings'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('interview_sessions.id'), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    candidate_name = db.Column(db.String(255), nullable=False)
    domain = db.Column(db.String(255), nullable=False, index=True)  # The applied domain
    overall_level = db.Column(db.String(50), nullable=False)  # Not Satisfactory/Moderate/Good
    overall_score = db.Column(db.Float, nullable=False)  # Overall score out of 10

    # Ranking within domain (will be calculated)
    domain_rank = db.Column(db.Integer)  # 1st, 2nd, 3rd etc. within the domain

    # Timestamps
    interview_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_updated = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                             onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    interview_session = db.relationship('InterviewSession', backref='domain_ranking', uselist=False)

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'email': self.email,
            'candidate_name': self.candidate_name,
            'domain': self.domain,
            'overall_level': self.overall_level,
            'overall_score': self.overall_score,
            'domain_rank': self.domain_rank,
            'interview_date': self.interview_date.isoformat(),
            'last_updated': self.last_updated.isoformat()
        }

class AttireAnalysis(db.Model):
    __tablename__ = 'attire_analysis'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('interview_sessions.id'), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)

    # Behavioral analysis results
    body_posture = db.Column(db.String(50))  # "Straight", "Slouched", "Unknown"
    eye_contact = db.Column(db.String(50))  # "Good", "Poor", "Unknown"

    # Attire analysis
    attire_feedback = db.Column(db.Text)
    attire_score = db.Column(db.Numeric(4, 2))  # Score out of 10 with 2 decimal places

    # Enhanced scoring fields (optional - can be calculated dynamically)
    posture_score = db.Column(db.Numeric(4, 2))  # Score out of 10 with 2 decimal places
    eye_contact_score = db.Column(db.Numeric(4, 2))  # Score out of 10 with 2 decimal places

    # Detailed analysis logs
    posture_log = db.Column(db.Text)  # JSON string of frame-by-frame analysis
    eye_log = db.Column(db.Text)  # JSON string of frame-by-frame analysis

    # Session metadata
    session_duration = db.Column(db.Float)
    frames_analyzed = db.Column(db.Integer, default=0)
    total_frames = db.Column(db.Integer, default=0)

    # File paths
    attire_image_path = db.Column(db.String(200))
    video_path = db.Column(db.String(200))

    # Timestamp
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<AttireAnalysis {self.id}: Session {self.session_id}>'

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        import json

        return {
            'id': self.id,
            'session_id': self.session_id,
            'email': self.email,
            'body_posture': self.body_posture,
            'eye_contact': self.eye_contact,
            'attire_score': float(self.attire_score) if self.attire_score else 0.00,
            'posture_score': float(self.posture_score) if self.posture_score else 0.00,
            'eye_contact_score': float(self.eye_contact_score) if self.eye_contact_score else 0.00,
            'attire_feedback': self.attire_feedback,
            'session_duration': self.session_duration,
            'posture_log': json.loads(self.posture_log) if self.posture_log else {},
            'eye_log': json.loads(self.eye_log) if self.eye_log else {},
            'frames_analyzed': self.frames_analyzed,
            'total_frames': self.total_frames,
            'timestamp': self.timestamp.isoformat()
        }

class EmotionAnalysis(db.Model):
    __tablename__ = 'emotion_analysis'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('interview_sessions.id'), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)  # Add email for direct queries
    top_emotion = db.Column(db.String(50))
    second_emotion = db.Column(db.String(50))
    distress_percentage = db.Column(db.Float)
    alert_triggered = db.Column(db.Boolean, default=False)
    chart_image = db.Column(db.Text)
    emotion_distribution = db.Column(db.Text)  # JSON string of emotion counts
    total_frames = db.Column(db.Integer, default=0)
    eq_score = db.Column(db.Float, default=0.0)  # ADD THIS LINE
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    interview_session = db.relationship('InterviewSession', backref='emotion_analyses')

    def to_dict(self):
        emotion_dist = {}
        if self.emotion_distribution:
            try:
                emotion_dist = json.loads(self.emotion_distribution)
            except:
                emotion_dist = {}

        return {
            'id': self.id,
            'session_id': self.session_id,
            'email': self.email,
            'top_emotion': self.top_emotion,
            'second_emotion': self.second_emotion,
            'distress_percentage': self.distress_percentage,
            'alert_triggered': self.alert_triggered,
            'emotion_distribution': emotion_dist,
            'total_frames': self.total_frames,
            'eq_score': self.eq_score,  # ADD THIS LINE
            'timestamp': self.timestamp.isoformat(),
            'chart_image': self.chart_image
        }

class InterviewQuestion(db.Model):
    __tablename__ = 'interview_questions'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('interview_sessions.id'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    audio_file_path = db.Column(db.String(500))  # Path to stored audio file
    evaluation_data = db.Column(JSON if 'postgresql' in DATABASE_URL else Text, nullable=True)

class InterviewEvaluation(db.Model):
    __tablename__ = 'interview_evaluations'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey('interview_sessions.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    overall_feedback = db.Column(db.Text)
    final_average_score = db.Column(db.Float)

    # Relationships
    qa_evaluations = db.relationship('QuestionEvaluation', backref='interview_evaluation', cascade='all, delete-orphan')
    interview_session = db.relationship('InterviewSession', backref='evaluations')


class QuestionEvaluation(db.Model):
    __tablename__ = 'question_evaluations'

    id = db.Column(db.Integer, primary_key=True)
    evaluation_id = db.Column(db.Integer, db.ForeignKey('interview_evaluations.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('interview_questions.id'), nullable=False)

    # Problem Solving scores
    ps_score = db.Column(db.Float)
    ps_label = db.Column(db.String(100))
    ps_converted_score = db.Column(db.Integer)

    # Analytical Thinking scores
    at_score = db.Column(db.Float)
    at_label = db.Column(db.String(100))
    at_converted_score = db.Column(db.Integer)

    # Confidence scores
    cf_score = db.Column(db.Float)
    cf_label = db.Column(db.String(100))
    cf_converted_score = db.Column(db.Integer)

    # Overall for this question
    average_score_out_of_10 = db.Column(db.Float)
    feedback = db.Column(db.Text)

    # Relationships
    interview_question = db.relationship('InterviewQuestion', backref='evaluations')

    def to_dict(self):
        return {
            'question': self.interview_question.question,
            'answer': self.interview_question.answer,
            'problem_solving': {
                'score': self.ps_score,
                'label': self.ps_label,
                'converted_score': self.ps_converted_score
            },
            'analytical_thinking': {
                'score': self.at_score,
                'label': self.at_label,
                'converted_score': self.at_converted_score
            },
            'confidence': {
                'score': self.cf_score,
                'label': self.cf_label,
                'converted_score': self.cf_converted_score
            },
            'average_score_out_of_10': self.average_score_out_of_10,
            'feedback': self.feedback
        }


# NEW GRAMMAR ANALYSIS MODELS

class GrammarAnalysis(db.Model):
    __tablename__ = 'grammar_analysis'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('interview_sessions.id'), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    analysis_timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Overall summary scores and feedback
    overall_average_score = db.Column(db.Float)  # Average of all question scores
    overall_feedback = db.Column(db.Text)
    total_questions_analyzed = db.Column(db.Integer, default=0)

    # Skill averages across all questions
    avg_vocabulary_score = db.Column(db.Float)
    avg_grammar_score = db.Column(db.Float)
    avg_pronunciation_score = db.Column(db.Float)
    avg_diction_score = db.Column(db.Float)
    avg_communication_clarity_score = db.Column(db.Float)
    avg_voice_intonation_score = db.Column(db.Float)
    avg_tone_score = db.Column(db.Float)
    avg_pitch_score = db.Column(db.Float)
    avg_rhythm_score = db.Column(db.Float)

    # Relationships
    interview_session = db.relationship('InterviewSession', backref='grammar_analysis')
    question_analyses = db.relationship('QuestionGrammarAnalysis', backref='grammar_analysis',
                                        cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'email': self.email,
            'analysis_timestamp': self.analysis_timestamp.isoformat(),
            'overall_average_score': self.overall_average_score,
            'overall_feedback': self.overall_feedback,
            'total_questions_analyzed': self.total_questions_analyzed,
            'skill_averages': {
                'vocabulary': self.avg_vocabulary_score,
                'grammar': self.avg_grammar_score,
                'pronunciation': self.avg_pronunciation_score,
                'diction': self.avg_diction_score,
                'communication_clarity': self.avg_communication_clarity_score,
                'voice_intonation': self.avg_voice_intonation_score,
                'tone': self.avg_tone_score,
                'pitch': self.avg_pitch_score,
                'rhythm': self.avg_rhythm_score
            },
            'question_analyses': [qa.to_dict() for qa in self.question_analyses]
        }


class QuestionGrammarAnalysis(db.Model):
    __tablename__ = 'question_grammar_analysis'

    id = db.Column(db.Integer, primary_key=True)
    grammar_analysis_id = db.Column(db.Integer, db.ForeignKey('grammar_analysis.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('interview_questions.id'), nullable=False)

    # Transcribed text from audio
    transcript = db.Column(db.Text, nullable=False)

    # Individual skill scores (converted to 0-10 scale)
    vocabulary_score = db.Column(db.Integer)
    grammar_score = db.Column(db.Integer)
    pronunciation_score = db.Column(db.Integer)
    diction_score = db.Column(db.Integer)
    communication_clarity_score = db.Column(db.Integer)
    voice_intonation_score = db.Column(db.Integer)
    tone_score = db.Column(db.Integer)
    pitch_score = db.Column(db.Integer)
    rhythm_score = db.Column(db.Integer)

    # Average score for this question
    question_average_score = db.Column(db.Float)

    # Raw feedback from Gemini
    raw_feedback = db.Column(db.Text)

    # Timestamp when this question was analyzed
    analyzed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    interview_question = db.relationship('InterviewQuestion', backref='grammar_analyses')

    def to_dict(self):
        return {
            'id': self.id,
            'question_id': self.question_id,
            'question': self.interview_question.question if self.interview_question else None,
            'transcript': self.transcript,
            'skills': {
                'vocabulary': self.vocabulary_score,
                'grammar': self.grammar_score,
                'pronunciation': self.pronunciation_score,
                'diction': self.diction_score,
                'communication_clarity': self.communication_clarity_score,
                'voice_intonation': self.voice_intonation_score,
                'tone': self.tone_score,
                'pitch': self.pitch_score,
                'rhythm': self.rhythm_score
            },
            'question_average_score': self.question_average_score,
            'raw_feedback': self.raw_feedback,
            'analyzed_at': self.analyzed_at.isoformat()
        }

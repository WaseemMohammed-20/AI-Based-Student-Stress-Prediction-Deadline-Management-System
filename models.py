"""
Database models and schema for AI-Assisted Assignment Collision Detector.
Uses SQLite with Flask-SQLAlchemy for ORM.
"""

import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Database path (relative to project root)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "database.db")

db = SQLAlchemy()


# ---------------------------------------------------------------------------
# User model: authentication and user-specific learning weights
# ---------------------------------------------------------------------------
class User(db.Model):
    """Stores user credentials and optional learning weight adjustments."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # User-specific weight for difficulty in priority formula (learning component)
    # Default 0.3; can be increased if user consistently overestimates
    difficulty_weight = db.Column(db.Float, default=0.3)
    # Number of completed assignments used to compute this weight
    learning_sample_count = db.Column(db.Integer, default=0)

    # Relationships
    assignments = db.relationship("Assignment", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    exams = db.relationship("Exam", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    completions = db.relationship("AssignmentCompletion", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        """Hash and store password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify password against stored hash."""
        return check_password_hash(self.password_hash, password)


# ---------------------------------------------------------------------------
# Assignment model: subject, title, deadline, effort, difficulty
# ---------------------------------------------------------------------------
class Assignment(db.Model):
    """Single assignment with deadline and effort metadata."""

    __tablename__ = "assignments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    subject = db.Column(db.String(120), nullable=False)
    title = db.Column(db.String(256), nullable=False)
    deadline = db.Column(db.Date, nullable=False)
    estimated_effort_hours = db.Column(db.Float, nullable=False)  # hours
    difficulty = db.Column(db.Integer, nullable=False)  # 1-5 scale
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Optional: mark as completed (for learning component)
    completed = db.Column(db.Boolean, default=False)

    def to_dict(self) -> dict:
        """For JSON/charts: id, subject, title, deadline, effort, difficulty."""
        return {
            "id": self.id,
            "subject": self.subject,
            "title": self.title,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "estimated_effort_hours": self.estimated_effort_hours,
            "difficulty": self.difficulty,
            "completed": self.completed,
        }


# ---------------------------------------------------------------------------
# Exam model: subject and date only
# ---------------------------------------------------------------------------
class Exam(db.Model):
    """Exam date per subject."""

    __tablename__ = "exams"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    subject = db.Column(db.String(120), nullable=False)
    exam_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "subject": self.subject,
            "exam_date": self.exam_date.isoformat() if self.exam_date else None,
        }


# ---------------------------------------------------------------------------
# AssignmentCompletion: for learning component (actual vs estimated time)
# ---------------------------------------------------------------------------
class AssignmentCompletion(db.Model):
    """Records actual time spent when user completes an assignment; used to adjust difficulty weight."""

    __tablename__ = "assignment_completions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    assignment_id = db.Column(db.Integer, nullable=False)  # May reference deleted assignment

    estimated_hours = db.Column(db.Float, nullable=False)
    actual_hours = db.Column(db.Float, nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def over_estimated(self) -> bool:
        """True if user took longer than estimated (we may increase difficulty weight)."""
        return self.actual_hours > self.estimated_hours


# ---------------------------------------------------------------------------
# Database initialization
# ---------------------------------------------------------------------------
def init_db(app):
    """Bind db to app and create all tables."""
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + DATABASE_PATH
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()

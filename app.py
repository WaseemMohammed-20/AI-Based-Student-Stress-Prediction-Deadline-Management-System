"""
AI-Assisted Assignment Collision Detector & Academic Stress Manager.
Flask application: auth, assignments, exams, dashboard, collision alerts, priority order, learning.
"""

import os
from datetime import date, datetime, timedelta
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)
from flask_sqlalchemy import SQLAlchemy

from models import db, init_db, User, Assignment, Exam, AssignmentCompletion
from priority_engine import recommended_order
from stress_analyzer import analyze_stress_weeks
from collision_detector import all_collisions

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
init_db(app)


def login_required(f):
    """Decorator: require logged-in user."""

    @wraps(f)
    def wrapped(*args, **kwargs):
        if session.get("user_id") is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return wrapped


def get_current_user():
    """Return User for session or None."""
    uid = session.get("user_id")
    if uid is None:
        return None
    return User.query.get(uid)


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """Home: redirect to dashboard if logged in, else login."""
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """User registration; store hashed password in SQLite."""
    if request.method == "GET":
        return render_template("register.html")
    username = (request.form.get("username") or "").strip()
    email = (request.form.get("email") or "").strip()
    password = request.form.get("password") or ""
    if not username or not email or not password:
        flash("Username, email and password are required.", "error")
        return render_template("register.html")
    if User.query.filter_by(username=username).first():
        flash("Username already taken.", "error")
        return render_template("register.html")
    if User.query.filter_by(email=email).first():
        flash("Email already registered.", "error")
        return render_template("register.html")
    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    flash("Registration successful. Please log in.", "success")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Simple login: check username + password."""
    if request.method == "GET":
        return render_template("login.html")
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        flash("Invalid username or password.", "error")
        return render_template("login.html")
    session["user_id"] = user.id
    flash("Welcome back!", "success")
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    """Clear session and redirect to login."""
    session.pop("user_id", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Assignment CRUD
# ---------------------------------------------------------------------------
@app.route("/assignments")
@login_required
def assignments_list():
    """List all assignments for current user."""
    user = get_current_user()
    items = Assignment.query.filter_by(user_id=user.id).order_by(Assignment.deadline).all()
    return render_template("assignments.html", assignments=items)


@app.route("/assignments/add", methods=["GET", "POST"])
@login_required
def assignment_add():
    """Add assignment: subject, title, deadline, estimated effort, difficulty 1-5."""
    if request.method == "GET":
        return render_template("assignment_form.html", assignment=None)
    user = get_current_user()
    subject = (request.form.get("subject") or "").strip()
    title = (request.form.get("title") or "").strip()
    deadline_s = request.form.get("deadline") or ""
    try:
        effort = float(request.form.get("estimated_effort") or 0)
    except ValueError:
        effort = 0
    try:
        difficulty = int(request.form.get("difficulty") or 1)
    except ValueError:
        difficulty = 1
    difficulty = max(1, min(5, difficulty))
    if not subject or not title or not deadline_s:
        flash("Subject, title and deadline are required.", "error")
        return render_template("assignment_form.html", assignment=None)
    try:
        deadline = datetime.strptime(deadline_s, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid deadline date.", "error")
        return render_template("assignment_form.html", assignment=None)
    a = Assignment(
        user_id=user.id,
        subject=subject,
        title=title,
        deadline=deadline,
        estimated_effort_hours=effort,
        difficulty=difficulty,
    )
    db.session.add(a)
    db.session.commit()
    flash("Assignment added.", "success")
    return redirect(url_for("assignments_list"))


@app.route("/assignments/<int:aid>/edit", methods=["GET", "POST"])
@login_required
def assignment_edit(aid):
    """Edit assignment by id (must belong to current user)."""
    user = get_current_user()
    a = Assignment.query.filter_by(id=aid, user_id=user.id).first_or_404()
    if request.method == "GET":
        return render_template("assignment_form.html", assignment=a)
    subject = (request.form.get("subject") or "").strip()
    title = (request.form.get("title") or "").strip()
    deadline_s = request.form.get("deadline") or ""
    try:
        effort = float(request.form.get("estimated_effort") or 0)
    except ValueError:
        effort = 0
    try:
        difficulty = int(request.form.get("difficulty") or 1)
    except ValueError:
        difficulty = 1
    difficulty = max(1, min(5, difficulty))
    if not subject or not title or not deadline_s:
        flash("Subject, title and deadline are required.", "error")
        return render_template("assignment_form.html", assignment=a)
    try:
        deadline = datetime.strptime(deadline_s, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid deadline date.", "error")
        return render_template("assignment_form.html", assignment=a)
    a.subject = subject
    a.title = title
    a.deadline = deadline
    a.estimated_effort_hours = effort
    a.difficulty = difficulty
    db.session.commit()
    flash("Assignment updated.", "success")
    return redirect(url_for("assignments_list"))


@app.route("/assignments/<int:aid>/delete", methods=["POST"])
@login_required
def assignment_delete(aid):
    """Delete assignment (must belong to current user)."""
    user = get_current_user()
    a = Assignment.query.filter_by(id=aid, user_id=user.id).first_or_404()
    db.session.delete(a)
    db.session.commit()
    flash("Assignment deleted.", "success")
    return redirect(url_for("assignments_list"))


# ---------------------------------------------------------------------------
# Assignment complete + learning (actual time spent)
# ---------------------------------------------------------------------------
@app.route("/assignments/<int:aid>/complete", methods=["GET", "POST"])
@login_required
def assignment_complete(aid):
    """
    Mark assignment complete and record actual time spent.
    If actualTime > estimatedTime, increase user's difficulty weight slightly (learning).
    """
    user = get_current_user()
    a = Assignment.query.filter_by(id=aid, user_id=user.id).first_or_404()
    if request.method == "GET":
        return render_template("assignment_complete.html", assignment=a)
    try:
        actual_hours = float(request.form.get("actual_hours") or 0)
    except ValueError:
        actual_hours = 0
    if actual_hours <= 0:
        flash("Please enter a positive actual time spent (hours).", "error")
        return render_template("assignment_complete.html", assignment=a)
    # Record completion for learning
    est = a.estimated_effort_hours
    db.session.add(
        AssignmentCompletion(
            user_id=user.id,
            assignment_id=a.id,
            estimated_hours=est,
            actual_hours=actual_hours,
        )
    )
    # Learning: if actual > estimated, increase difficulty weight slightly
    if actual_hours > est:
        # Bump by 0.01, cap at 0.5
        user.difficulty_weight = min(0.5, (user.difficulty_weight or 0.3) + 0.01)
    user.learning_sample_count = (user.learning_sample_count or 0) + 1
    a.completed = True
    db.session.commit()
    flash("Assignment marked complete. Priority model updated from your feedback.", "success")
    return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------------
# Exam CRUD
# ---------------------------------------------------------------------------
@app.route("/exams")
@login_required
def exams_list():
    """List all exams for current user."""
    user = get_current_user()
    items = Exam.query.filter_by(user_id=user.id).order_by(Exam.exam_date).all()
    return render_template("exams.html", exams=items)


@app.route("/exams/add", methods=["GET", "POST"])
@login_required
def exam_add():
    """Add exam: subject and date."""
    if request.method == "GET":
        return render_template("exam_form.html", exam=None)
    user = get_current_user()
    subject = (request.form.get("subject") or "").strip()
    date_s = request.form.get("exam_date") or ""
    if not subject or not date_s:
        flash("Subject and exam date are required.", "error")
        return render_template("exam_form.html", exam=None)
    try:
        exam_date = datetime.strptime(date_s, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid date.", "error")
        return render_template("exam_form.html", exam=None)
    e = Exam(user_id=user.id, subject=subject, exam_date=exam_date)
    db.session.add(e)
    db.session.commit()
    flash("Exam added.", "success")
    return redirect(url_for("exams_list"))


@app.route("/exams/<int:eid>/edit", methods=["GET", "POST"])
@login_required
def exam_edit(eid):
    """Edit exam by id."""
    user = get_current_user()
    e = Exam.query.filter_by(id=eid, user_id=user.id).first_or_404()
    if request.method == "GET":
        return render_template("exam_form.html", exam=e)
    subject = (request.form.get("subject") or "").strip()
    date_s = request.form.get("exam_date") or ""
    if not subject or not date_s:
        flash("Subject and exam date are required.", "error")
        return render_template("exam_form.html", exam=e)
    try:
        exam_date = datetime.strptime(date_s, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid date.", "error")
        return render_template("exam_form.html", exam=e)
    e.subject = subject
    e.exam_date = exam_date
    db.session.commit()
    flash("Exam updated.", "success")
    return redirect(url_for("exams_list"))


@app.route("/exams/<int:eid>/delete", methods=["POST"])
@login_required
def exam_delete(eid):
    """Delete exam."""
    user = get_current_user()
    e = Exam.query.filter_by(id=eid, user_id=user.id).first_or_404()
    db.session.delete(e)
    db.session.commit()
    flash("Exam deleted.", "success")
    return redirect(url_for("exams_list"))


# ---------------------------------------------------------------------------
# Dashboard: assignments, stress weeks, collisions, recommended order, chart
# ---------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    """Dashboard: assignments, stress indicator, collision alerts, recommended order."""
    user = get_current_user()
    today = date.today()
    assignments = Assignment.query.filter_by(user_id=user.id).order_by(Assignment.deadline).all()
    exams = Exam.query.filter_by(user_id=user.id).order_by(Exam.exam_date).all()
    # Incomplete only for priority and collisions
    incomplete = [a for a in assignments if not a.completed]
    collisions = all_collisions(incomplete, exams, today)
    stress_weeks = analyze_stress_weeks(assignments, exams, today)
    dw = getattr(user, "difficulty_weight", None) or 0.3
    recommended = recommended_order(incomplete, today, difficulty_weight=dw)
    # Limit stress weeks for display (next 6 weeks)
    stress_weeks_list = list(stress_weeks.items())[:6]
    # Assignment IDs that appear in collision alerts (for Issue Flag column)
    assignment_ids_in_collision = set()
    for group in collisions.get("seven_day", []):
        for a, _ in group:
            assignment_ids_in_collision.add(a.id)
    for item in collisions.get("near_exam", []):
        assignment_ids_in_collision.add(item["assignment"].id)
    return render_template(
        "dashboard.html",
        assignments=assignments,
        exams=exams,
        collisions=collisions,
        stress_weeks=stress_weeks,
        stress_weeks_list=stress_weeks_list,
        recommended=recommended,
        today=today,
        assignment_ids_in_collision=assignment_ids_in_collision,
    )


# ---------------------------------------------------------------------------
# Chart data (weekly workload) for Chart.js
# ---------------------------------------------------------------------------
@app.route("/api/dashboard/chart")
@login_required
def dashboard_chart():
    """JSON: weekly workload (effort hours per week) for the next 8 weeks."""
    user = get_current_user()
    today = date.today()
    assignments = Assignment.query.filter_by(user_id=user.id).all()
    exams = Exam.query.filter_by(user_id=user.id).all()
    stress = analyze_stress_weeks(assignments, exams, today)
    # Build labels, data, and stress level per week (for color-coded chart bars)
    labels = []
    data = []
    levels = []
    for i in range(8):
        week_start = today + timedelta(days=-today.weekday() + 7 * i)
        key = week_start.isoformat()
        labels.append(week_start.strftime("%b %d"))
        info = stress.get(key, {})
        data.append(info.get("effort", 0))
        levels.append(info.get("level", "Normal"))
    return jsonify({"labels": labels, "data": data, "levels": levels})


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)

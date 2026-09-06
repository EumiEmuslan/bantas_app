from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from init_db import get_db   # ✅ import Supabase client from db.py
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- Login required decorator ---
def login_required(role=None):
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if "user_id" not in session:
                flash("You must log in first.")
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("Unauthorized access.")
                return redirect(url_for("home"))
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

# --- Routes ---
@app.route("/")
def home():
    return render_template("login.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        db = get_db()
        result = db.table("users").select("id, role, password").eq("email", email).execute()

        if result.data and check_password_hash(result.data[0]["password"], password):
            session["user_id"] = result.data[0]["id"]
            session["role"] = result.data[0]["role"]

            if result.data[0]["role"] == "student":
                return redirect(url_for("student_dashboard"))
            elif result.data[0]["role"] == "teacher":
                return redirect(url_for("teacher_dashboard"))
        else:
            flash("Wrong email or password.")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_pw = generate_password_hash(password)
        role = "student"

        db = get_db()
        result = db.table("users").insert({
            "name": name,
            "email": email,
            "password": hashed_pw,
            "role": role
        }).execute()

        if result.data:
            return redirect(url_for("home"))
        else:
            flash("Signup failed. Please try again.")
            return redirect(url_for("signup"))

    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# --- Student routes ---
@app.route("/student/dashboard")
@login_required(role="student")
def student_dashboard():
    quizzes = get_db().table("quizzes").select("id, title").execute().data
    return render_template("student_dashboard.html", quizzes=quizzes)

@app.route("/student/quiz/<int:quiz_id>", methods=["GET", "POST"])
@login_required(role="student")
def student_quiz(quiz_id):
    db = get_db()

    if request.method == "POST":
        user_id = session["user_id"]
        score = 0

        questions = db.table("questions").select("id, correct_option").eq("quiz_id", quiz_id).execute().data

        for q in questions:
            chosen = request.form.get(str(q["id"]))
            db.table("answers").insert({
                "user_id": user_id,
                "question_id": q["id"],
                "chosen_option": chosen
            }).execute()
            if chosen == q["correct_option"]:
                score += 1

        db.table("scores").insert({
            "user_id": user_id,
            "quiz_id": quiz_id,
            "score": score
        }).execute()

        return redirect(url_for("student_result", quiz_id=quiz_id))

    questions = db.table("questions").select("id, question_text, option_a, option_b, option_c, option_d").eq("quiz_id", quiz_id).execute().data
    return render_template("student_quiz.html", quiz_id=quiz_id, questions=questions)

@app.route("/student/result/<int:quiz_id>")
@login_required(role="student")
def student_result(quiz_id):
    db = get_db()
    user_id = session["user_id"]
    result = db.table("scores").select("score").eq("user_id", user_id).eq("quiz_id", quiz_id).execute()

    if result.data:
        return render_template("student_result.html", score=result.data[0]["score"])
    else:
        return "No score found."

@app.route("/student/performance/<int:user_id>")
@login_required(role="student")
def student_performance(user_id):
    db = get_db()
    results = db.table("scores").select("quiz_id, score").eq("user_id", user_id).execute().data
    avg_score = None
    if results:
        total = sum(r["score"] for r in results)
        avg_score = total / len(results)
    return render_template("student_performance.html", results=results, avg_score=avg_score)

# --- Teacher routes ---
@app.route("/teacher/dashboard")
@login_required(role="teacher")
def teacher_dashboard():
    quizzes = get_db().table("quizzes").select("id, title").execute().data
    return render_template("teacher_dashboard.html", quizzes=quizzes)

@app.route("/teacher/quiz/new", methods=["GET", "POST"])
@login_required(role="teacher")
def new_quiz():
    if request.method == "POST":
        title = request.form["title"]
        result = get_db().table("quizzes").insert({
            "title": title,
            "created_by": session["user_id"]
        }).execute()
        quiz_id = result.data[0]["id"]
        return redirect(url_for("manage_questions", quiz_id=quiz_id))
    return render_template("teacher_quiz_create.html")

@app.route("/teacher/quiz/<int:quiz_id>/questions", methods=["GET", "POST"])
@login_required(role="teacher")
def manage_questions(quiz_id):
    db = get_db()
    if request.method == "POST":
        q_text = request.form["question_text"]
        a = request.form["option_a"]
        b = request.form["option_b"]
        c = request.form["option_c"]
        d = request.form["option_d"]
        correct = request.form["correct_option"]

        db.table("questions").insert({
            "quiz_id": quiz_id,
            "question_text": q_text,
            "option_a": a,
            "option_b": b,
            "option_c": c,
            "option_d": d,
            "correct_option": correct
        }).execute()

    questions = db.table("questions").select("id, question_text, option_a, option_b, option_c, option_d, correct_option").eq("quiz_id", quiz_id).execute().data
    return render_template("teacher_quiz_manage.html", quiz_id=quiz_id, questions=questions)

@app.route("/teacher/quiz/<int:quiz_id>/results")
@login_required(role="teacher")
def quiz_results(quiz_id):
    results = get_db().table("scores").select("user_id, score").eq("quiz_id", quiz_id).execute().data
    return render_template("teacher_results.html", results=results)

@app.route("/teacher/quiz/<int:quiz_id>/delete/<int:question_id>", methods=["POST"])
@login_required(role="teacher")
def delete_question(quiz_id, question_id):
    get_db().table("questions").delete().eq("id", question_id).execute()
    return redirect(url_for("manage_questions", quiz_id=quiz_id))

@app.route("/teacher/quiz/<int:quiz_id>/delete/<int:question_id>", methods=["POST"])
@login_required(role="teacher")
def delete_question(quiz_id, question_id):
    get_db().table("questions").delete() \
        .eq("id", question_id) \
        .eq("quiz_id", quiz_id) \
        .eq("created_by", session["user_id"]) \
        .execute()
    return redirect(url_for("manage_questions", quiz_id=quiz_id))

@app.route("/teacher/quiz/<int:quiz_id>/delete", methods=["POST"])
@login_required(role="teacher")
def delete_quiz(quiz_id):
    db = get_db()
    db.table("questions").delete().eq("quiz_id", quiz_id).eq("created_by", session["user_id"]).execute()
    db.table("scores").delete().eq("quiz_id", quiz_id).eq("created_by", session["user_id"]).execute()
    db.table("quizzes").delete().eq("id", quiz_id).eq("created_by", session["user_id"]).execute()
    return redirect(url_for("teacher_dashboard"))


# --- Lessons ---
@app.route("/student/lessons")
@login_required(role="student")
def student_lessons():
    lessons = get_db().table("lessons").select("id, title, description").execute().data
    return render_template("student_lessons.html", lessons=lessons)

@app.route("/student/lessons/bantas")
@login_required(role="student")
def lesson_bantas():
    return render_template("lesson_bantas.html")

@app.route("/student/lessons/halimbawa")
@login_required(role="student")
def lesson_halimbawa():
    return render_template("lesson_halimbawa.html")

@app.route("/teacher/lessons", methods=["GET", "POST"])
@login_required(role="teacher")
def teacher_lessons():
    db = get_db()
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        db.table("lessons").insert({
            "title": title,
            "description": description,
            "created_by": session["user_id"]
        }).execute()

    lessons = db.table("lessons").select("id, title, description").eq("created_by", session["user_id"]).execute().data
    return render_template("teacher_lessons.html", lessons=lessons)

@app.route("/teacher/lessons/delete/<int:lesson_id>", methods=["POST"])
@login_required(role="teacher")
def delete_lesson(lesson_id):
    db = get_db()
    # Only delete if the lesson belongs to the logged-in teacher
    db.table("lessons").delete() \
        .eq("id", lesson_id) \
        .eq("created_by", session["user_id"]) \
        .execute()
    return redirect(url_for("teacher_lessons"))


# --- Run the app ---
if __name__ == "__main__":
    app.run(debug=True)

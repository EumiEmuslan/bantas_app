from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
import psycopg2.extras   # ✅ for RealDictCursor
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)  # ✅ safer than "secret123"

# --- Database helper ---
def get_db():
    conn = psycopg2.connect(os.environ.get("SUPABASE_URL"))
    return conn

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

        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT id, role, password FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["role"] = user["role"]

            if user["role"] == "student":
                return redirect(url_for("student_dashboard"))
            elif user["role"] == "teacher":
                return redirect(url_for("teacher_dashboard"))
        else:
         flash("Wrong email or password.")
         return redirect(url_for("login"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_pw = generate_password_hash(password)

        role = "student"  # ✅ default role

        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (name,email,password,role) VALUES (%s,%s,%s,%s)",
                    (name,email,hashed_pw,role))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("home"))
    return render_template("signup.html")



    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# --- Student routes ---
@app.route("/student/dashboard")
@login_required(role="student")
def student_dashboard():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, title FROM quizzes")
    quizzes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("student_dashboard.html", quizzes=quizzes)

@app.route("/student/quiz/<int:quiz_id>", methods=["GET", "POST"])
@login_required(role="student")
def student_quiz(quiz_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if request.method == "POST":
        user_id = session["user_id"]
        score = 0

        cur.execute("SELECT id, correct_option FROM questions WHERE quiz_id=%s", (quiz_id,))
        questions = cur.fetchall()

        for q in questions:
            chosen = request.form.get(str(q["id"]))
            cur.execute("INSERT INTO answers (user_id, question_id, chosen_option) VALUES (%s,%s,%s)",
                        (user_id, q["id"], chosen))
            if chosen == q["correct_option"]:
                score += 1

        cur.execute("INSERT INTO scores (user_id, quiz_id, score) VALUES (%s,%s,%s)",
                    (user_id, quiz_id, score))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("student_result", quiz_id=quiz_id))

    cur.execute("SELECT id, question_text, option_a, option_b, option_c, option_d FROM questions WHERE quiz_id=%s", (quiz_id,))
    questions = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("student_quiz.html", quiz_id=quiz_id, questions=questions)

@app.route("/student/result/<int:quiz_id>")
@login_required(role="student")
def student_result(quiz_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    user_id = session["user_id"]
    cur.execute("SELECT score FROM scores WHERE user_id=%s AND quiz_id=%s", (user_id, quiz_id))
    score = cur.fetchone()
    cur.close()
    conn.close()
    if score:
        return render_template("student_result.html", score=score["score"])
    else:
        return "No score found."

@app.route("/student/performance/<int:user_id>")
@login_required(role="student")
def student_performance(user_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT q.title, s.score
        FROM scores s
        JOIN quizzes q ON s.quiz_id = q.id
        WHERE s.user_id = %s
    """, (user_id,))
    results = cur.fetchall()

    avg_score = None
    if results:
        total = sum(r["score"] for r in results)
        avg_score = total / len(results)

    cur.close()
    conn.close()
    return render_template("student_performance.html", results=results, avg_score=avg_score)

# --- Teacher routes ---
@app.route("/teacher/dashboard")
@login_required(role="teacher")
def teacher_dashboard():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, title FROM quizzes")
    quizzes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("teacher_dashboard.html", quizzes=quizzes)

@app.route("/teacher/quiz/new", methods=["GET", "POST"])
@login_required(role="teacher")
def new_quiz():
    if request.method == "POST":
        title = request.form["title"]
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO quizzes (title, created_by) VALUES (%s, %s) RETURNING id",
            (title, session["user_id"])
        )
        quiz_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("manage_questions", quiz_id=quiz_id))
    return render_template("teacher_quiz_create.html")

@app.route("/teacher/quiz/<int:quiz_id>/questions", methods=["GET", "POST"])
@login_required(role="teacher")
def manage_questions(quiz_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if request.method == "POST":
        q_text = request.form["question_text"]
        a = request.form["option_a"]
        b = request.form["option_b"]
        c = request.form["option_c"]
        d = request.form["option_d"]
        correct = request.form["correct_option"]

        cur.execute("""INSERT INTO questions 
                       (quiz_id, question_text, option_a, option_b, option_c, option_d, correct_option) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (quiz_id, q_text, a, b, c, d, correct))
        conn.commit()
    cur.execute("SELECT id, question_text, option_a, option_b, option_c, option_d, correct_option FROM questions WHERE quiz_id=%s", (quiz_id,))
    questions = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("teacher_quiz_manage.html", quiz_id=quiz_id, questions=questions)

@app.route("/teacher/quiz/<int:quiz_id>/results")
@login_required(role="teacher")
def quiz_results(quiz_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT u.name, s.score, q.title
        FROM scores s
        JOIN users u ON s.user_id = u.id
        JOIN quizzes q ON s.quiz_id = q.id
        WHERE q.id = %s
    """, (quiz_id,))
    results = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("teacher_results.html", results=results)

@app.route("/teacher/quiz/<int:quiz_id>/delete/<int:question_id>", methods=["POST"])
@login_required(role="teacher")
def delete_question(quiz_id, question_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM questions WHERE id=%s", (question_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("manage_questions", quiz_id=quiz_id))

@app.route("/teacher/quiz/<int:quiz_id>/delete", methods=["POST"])
@login_required(role="teacher")
def delete_quiz(quiz_id):
    conn = get_db()
    cur = conn.cursor()
    # First delete questions linked to the quiz (to avoid foreign key issues)
    cur.execute("DELETE FROM questions WHERE quiz_id=%s", (quiz_id,))
    # Then delete scores linked to the quiz
    cur.execute("DELETE FROM scores WHERE quiz_id=%s", (quiz_id,))
    # Finally delete the quiz itself
    cur.execute("DELETE FROM quizzes WHERE id=%s", (quiz_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("teacher_dashboard"))

# --- Teacher performance route (new) ---
@app.route("/teacher/performance")
@login_required(role="teacher")
def all_students_performance():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Collect each student’s average score
    cur.execute("""
        SELECT u.id, u.name, AVG(s.score) AS avg_score
        FROM scores s
        JOIN users u ON s.user_id = u.id
        WHERE u.role = 'student'
        GROUP BY u.id, u.name
        ORDER BY avg_score DESC
    """)
    performance = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("teacher_performance.html", performance=performance)


@app.route("/student/lessons")
@login_required(role="student")
def student_lessons():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, title, description FROM lessons")
    lessons = cur.fetchall()
    cur.close()
    conn.close()
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
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        cur.execute(
            "INSERT INTO lessons (title, description, created_by) VALUES (%s, %s, %s)",
            (title, description, session["user_id"])
        )
        conn.commit()

    cur.execute("SELECT id, title, description FROM lessons WHERE created_by=%s", (session["user_id"],))
    lessons = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("teacher_lessons.html", lessons=lessons)
@app.route("/teacher/lessons/delete/<int:lesson_id>", methods=["POST"])
@login_required(role="teacher")
def delete_lesson(lesson_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM lessons WHERE id=%s", (lesson_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("teacher_lessons"))



# --- Run the app ---
if __name__ == "__main__":
    app.run(debug=True)

import sqlite3
import jwt
import datetime
import json
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from functools import wraps

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'super-secret-exam-key'
DB_NAME = 'exam_system.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Admin table
    c.execute('''CREATE TABLE IF NOT EXISTS admins
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)''')
    # Exam table
    c.execute('''CREATE TABLE IF NOT EXISTS exams
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT)''')
    # Questions table - ADDED marks
    c.execute('''CREATE TABLE IF NOT EXISTS questions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, exam_id INTEGER, 
                  question_text TEXT, options TEXT, correct_answer TEXT, 
                  solving_time INTEGER, marks INTEGER DEFAULT 1, 
                  FOREIGN KEY(exam_id) REFERENCES exams(id))''')
    # Student passwords per exam
    c.execute('''CREATE TABLE IF NOT EXISTS student_credentials
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, exam_id INTEGER, 
                  username TEXT, password TEXT, UNIQUE(exam_id, username),
                  FOREIGN KEY(exam_id) REFERENCES exams(id))''')
    # Student progress - ADDED evaluation_pending
    c.execute('''CREATE TABLE IF NOT EXISTS student_progress
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, exam_id INTEGER, username TEXT,
                  current_q_index INTEGER DEFAULT 0, score INTEGER DEFAULT 0,
                  q_start_time TIMESTAMP, finished BOOLEAN DEFAULT 0,
                  evaluation_pending BOOLEAN DEFAULT 0,
                  FOREIGN KEY(exam_id) REFERENCES exams(id))''')
    # Student individual answers
    c.execute('''CREATE TABLE IF NOT EXISTS student_answers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, exam_id INTEGER, username TEXT,
                  question_id INTEGER, submitted_text TEXT, marks_awarded INTEGER, 
                  evaluated BOOLEAN DEFAULT 0,
                  FOREIGN KEY(exam_id) REFERENCES exams(id),
                  FOREIGN KEY(question_id) REFERENCES questions(id))''')
    
    # Insert default admin if none exists
    c.execute("SELECT * FROM admins WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO admins (username, password) VALUES ('admin', 'admin')")
    
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# --- Authentication Decorators ---

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            token = token.split(" ")[1] # Bearer Token
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            if data['role'] != 'admin':
                return jsonify({'message': 'Admin privilege required!'}), 403
        except Exception as e:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(*args, **kwargs)
    return decorated

def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            token = token.split(" ")[1]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            if data['role'] != 'student':
                return jsonify({'message': 'Student privilege required!'}), 403
            request.student_data = data
        except Exception as e:
            return jsonify({'message': 'Token is invalid or expired!'}), 401
        return f(*args, **kwargs)
    return decorated


# --- Auth Endpoints ---

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    conn = get_db_connection()
    admin = conn.execute("SELECT * FROM admins WHERE username=? AND password=?", 
                         (data.get('username'), data.get('password'))).fetchone()
    conn.close()
    
    if admin:
        token = jwt.encode({
            'user': admin['username'],
            'role': 'admin',
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm="HS256")
        return jsonify({'token': token})
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/api/student/login', methods=['POST'])
def student_login():
    data = request.json
    exam_id = data.get('exam_id')
    username = data.get('username')
    password = data.get('password')
    
    conn = get_db_connection()
    cred = conn.execute("SELECT * FROM student_credentials WHERE exam_id=? AND username=? AND password=?", 
                        (exam_id, username, password)).fetchone()
    
    if cred:
        questions = conn.execute("SELECT solving_time FROM questions WHERE exam_id=?", (exam_id,)).fetchall()
        total_time_seconds = sum(q['solving_time'] for q in questions)
        expiry_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=total_time_seconds + 300)
        
        prog = conn.execute("SELECT * FROM student_progress WHERE exam_id=? AND username=?", (exam_id, username)).fetchone()
        if not prog:
            conn.execute("INSERT INTO student_progress (exam_id, username) VALUES (?, ?)", (exam_id, username))
            conn.commit()
            
        token = jwt.encode({
            'username': username,
            'exam_id': exam_id,
            'role': 'student',
            'exp': expiry_time
        }, app.config['SECRET_KEY'], algorithm="HS256")
        conn.close()
        return jsonify({'token': token})
    
    conn.close()
    return jsonify({'message': 'Invalid credentials or exam ID'}), 401


# --- Admin Endpoints ---

@app.route('/api/admin/exams', methods=['GET', 'POST'])
@admin_required
def handle_exams():
    conn = get_db_connection()
    if request.method == 'GET':
        exams = conn.execute("SELECT * FROM exams").fetchall()
        conn.close()
        return jsonify([dict(ix) for ix in exams])
    elif request.method == 'POST':
        data = request.json
        cur = conn.execute("INSERT INTO exams (title) VALUES (?)", (data.get('title'),))
        conn.commit()
        exam_id = cur.lastrowid
        conn.close()
        return jsonify({'id': exam_id, 'message': 'Exam created successfully'})

@app.route('/api/admin/exams/<int:exam_id>/questions', methods=['GET', 'POST'])
@admin_required
def handle_questions(exam_id):
    conn = get_db_connection()
    if request.method == 'GET':
        questions = conn.execute("SELECT * FROM questions WHERE exam_id=? ORDER BY id", (exam_id,)).fetchall()
        conn.close()
        return jsonify([dict(q) for q in questions])
    elif request.method == 'POST':
        data = request.json
        marks = int(data.get('marks', 1))
        conn.execute('''INSERT INTO questions 
                        (exam_id, question_text, options, correct_answer, solving_time, marks) 
                        VALUES (?, ?, ?, ?, ?, ?)''',
                     (exam_id, data['question_text'], data['options'], 
                      data['correct_answer'], data['solving_time'], marks))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Question added successfully'})

@app.route('/api/admin/exams/<int:exam_id>/questions/<int:q_id>', methods=['PUT', 'DELETE'])
@admin_required
def update_question(exam_id, q_id):
    conn = get_db_connection()
    if request.method == 'PUT':
        data = request.json
        if 'marks' in data:
            conn.execute("UPDATE questions SET marks=? WHERE id=? AND exam_id=?", 
                         (int(data['marks']), q_id, exam_id))
        if 'question_text' in data:
             conn.execute("UPDATE questions SET question_text=?, options=?, correct_answer=?, solving_time=? WHERE id=? AND exam_id=?",
                          (data['question_text'], data['options'], data['correct_answer'], data['solving_time'], q_id, exam_id))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Question updated successfully'})
    elif request.method == 'DELETE':
        conn.execute("DELETE FROM questions WHERE id=? AND exam_id=?", (q_id, exam_id))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Question deleted successfully'})

@app.route('/api/admin/exams/<int:exam_id>/students', methods=['POST'])
@admin_required
def add_student_credentials(exam_id):
    data = request.json
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO student_credentials (exam_id, username, password) VALUES (?, ?, ?)",
                     (exam_id, data['username'], data['password']))
        conn.commit()
        msg = 'Student added to exam'
    except sqlite3.IntegrityError:
        msg = 'Student already exists for this exam'
    conn.close()
    return jsonify({'message': msg})

@app.route('/api/admin/exams/<int:exam_id>/results', methods=['GET'])
@admin_required
def get_exam_results(exam_id):
    conn = get_db_connection()
    results = conn.execute("SELECT username, score, finished, evaluation_pending FROM student_progress WHERE exam_id=?", (exam_id,)).fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in results])

@app.route('/api/admin/exams/<int:exam_id>/evaluation/<string:username>', methods=['GET'])
@admin_required
def get_student_evaluation(exam_id, username):
    conn = get_db_connection()
    # Fetch all questions and student's answers
    questions = conn.execute("SELECT * FROM questions WHERE exam_id=? ORDER BY id", (exam_id,)).fetchall()
    answers = conn.execute("SELECT * FROM student_answers WHERE exam_id=? AND username=?", (exam_id, username)).fetchall()
    conn.close()
    
    answer_dict = {a['question_id']: dict(a) for a in answers}
    
    paper = []
    for q in questions:
        q_dict = dict(q)
        ans = answer_dict.get(q['id'])
        if ans:
             q_dict['student_answer'] = ans['submitted_text']
             q_dict['marks_awarded'] = ans['marks_awarded']
             q_dict['evaluated'] = ans['evaluated']
             q_dict['answer_id'] = ans['id']
        else:
             q_dict['student_answer'] = None
             q_dict['marks_awarded'] = 0
             q_dict['evaluated'] = False
             q_dict['answer_id'] = None
        paper.append(q_dict)
        
    return jsonify(paper)

@app.route('/api/admin/exams/<int:exam_id>/evaluation/<string:username>', methods=['POST'])
@admin_required
def submit_student_evaluation(exam_id, username):
    data = request.json # Expected format: { answer_id: marks_awarded, ... }
    conn = get_db_connection()
    
    # Update individual answers
    for ans_id, marks in data.items():
        conn.execute("UPDATE student_answers SET marks_awarded=?, evaluated=1 WHERE id=? AND exam_id=? AND username=?", 
                     (int(marks), int(ans_id), exam_id, username))
    
    # Recalculate total score
    total_score = conn.execute("SELECT SUM(marks_awarded) as total FROM student_answers WHERE exam_id=? AND username=?", 
                               (exam_id, username)).fetchone()['total']
    if total_score is None: 
        total_score = 0
        
    # Check if all questions are evaluated
    total_q = conn.execute("SELECT COUNT(*) as t FROM questions WHERE exam_id=?", (exam_id,)).fetchone()['t']
    eval_q = conn.execute("SELECT COUNT(*) as t FROM student_answers WHERE exam_id=? AND username=? AND evaluated=1", 
                          (exam_id, username)).fetchone()['t']
                          
    is_pending = (eval_q < total_q)
    
    conn.execute("UPDATE student_progress SET score=?, evaluation_pending=? WHERE exam_id=? AND username=?", 
                 (total_score, 1 if is_pending else 0, exam_id, username))
                 
    conn.commit()
    conn.close()
    return jsonify({'message': 'Evaluation saved successfully', 'score': total_score})


# --- Student Endpoints ---

@app.route('/api/student/question', methods=['GET'])
@student_required
def get_current_question():
    student = request.student_data
    exam_id = student['exam_id']
    username = student['username']
    
    conn = get_db_connection()
    prog = conn.execute("SELECT * FROM student_progress WHERE exam_id=? AND username=?", (exam_id, username)).fetchone()
    
    if prog['finished']:
        conn.close()
        return jsonify({'message': 'Exam finished', 'finished': True})
        
    questions = conn.execute("SELECT * FROM questions WHERE exam_id=? ORDER BY id", (exam_id,)).fetchall()
    
    if prog['current_q_index'] >= len(questions):
        conn.execute("UPDATE student_progress SET finished=1 WHERE exam_id=? AND username=?", (exam_id, username))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Exam finished', 'finished': True})
        
    current_q = dict(questions[prog['current_q_index']])
    
    if not prog['q_start_time']:
        now = datetime.datetime.utcnow().isoformat()
        conn.execute("UPDATE student_progress SET q_start_time=? WHERE exam_id=? AND username=?", 
                     (now, exam_id, username))
        conn.commit()
        q_start = datetime.datetime.fromisoformat(now)
    else:
        q_start = datetime.datetime.fromisoformat(prog['q_start_time'])
        
    conn.close()
    
    current_q.pop('correct_answer', None) # Hide from student
    
    elapsed = (datetime.datetime.utcnow() - q_start).total_seconds()
    time_remaining = max(0, current_q['solving_time'] - int(elapsed))
    
    current_q['time_remaining'] = time_remaining
    current_q['total_questions'] = len(questions)
    current_q['current_index'] = prog['current_q_index']
    
    return jsonify(current_q)

@app.route('/api/student/answer', methods=['POST'])
@student_required
def submit_answer():
    student = request.student_data
    exam_id = student['exam_id']
    username = student['username']
    data = request.json
    submitted_answer = data.get('answer', '')
    
    conn = get_db_connection()
    prog = conn.execute("SELECT * FROM student_progress WHERE exam_id=? AND username=?", (exam_id, username)).fetchone()
    
    if prog['finished']:
        conn.close()
        return jsonify({'message': 'Exam already finished'}), 400
        
    questions = conn.execute("SELECT * FROM questions WHERE exam_id=? ORDER BY id", (exam_id,)).fetchall()
    if prog['current_q_index'] >= len(questions):
        conn.close()
        return jsonify({'message': 'No more questions'}), 400
        
    current_q = questions[prog['current_q_index']]
    
    # Enforce time limits
    if prog['q_start_time']:
        q_start = datetime.datetime.fromisoformat(prog['q_start_time'])
        elapsed = (datetime.datetime.utcnow() - q_start).total_seconds()
        if elapsed > current_q['solving_time'] + 5:
            submitted_answer = '' # Timed out
            
    # Check if short answer or MCQ
    # A question is short answer if options is empty array '[]' or empty string
    is_short_answer = False
    try:
        opts = json.loads(current_q['options'])
        if not opts or len(opts) == 0:
            is_short_answer = True
    except:
        if not current_q['options'] or current_q['options'].strip() == '':
            is_short_answer = True

    marks_awarded = 0
    evaluated = 0
    requires_eval = False

    if is_short_answer:
        # short answer -> manual evaluation needed
        marks_awarded = 0
        evaluated = 0
        requires_eval = True
    else:
        # MCQ -> auto evaluation
        if submitted_answer and submitted_answer.strip() == current_q['correct_answer'].strip():
            marks_awarded = current_q['marks']
        evaluated = 1
        
    # Save the individual answer
    conn.execute('''INSERT INTO student_answers 
                    (exam_id, username, question_id, submitted_text, marks_awarded, evaluated) 
                    VALUES (?, ?, ?, ?, ?, ?)''',
                 (exam_id, username, current_q['id'], submitted_answer, marks_awarded, evaluated))
                 
    new_score = prog['score'] + marks_awarded
    new_index = prog['current_q_index'] + 1
    finished = 1 if new_index >= len(questions) else 0
    
    # Has pending evaluations if it required eval for this question OR it already had pending
    is_pending = 1 if (requires_eval or prog['evaluation_pending']) else 0
    
    conn.execute('''UPDATE student_progress 
                    SET current_q_index=?, score=?, q_start_time=NULL, finished=?, evaluation_pending=? 
                    WHERE exam_id=? AND username=?''', 
                 (new_index, new_score, finished, is_pending, exam_id, username))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'finished': bool(finished)})

@app.route('/api/student/result', methods=['GET'])
@student_required
def get_result():
    student = request.student_data
    conn = get_db_connection()
    prog = conn.execute("SELECT score, finished, evaluation_pending FROM student_progress WHERE exam_id=? AND username=?", 
                        (student['exam_id'], student['username'])).fetchone()
                        
    # Total possible marks
    total_marks_row = conn.execute("SELECT SUM(marks) as total FROM questions WHERE exam_id=?", 
                             (student['exam_id'],)).fetchone()
    total_marks = total_marks_row['total'] if (total_marks_row and total_marks_row['total']) else 0

    if not prog['finished']:
        conn.close()
        return jsonify({'message': 'Exam not finished yet'}), 400
        
    if prog['evaluation_pending']:
        conn.close()
        return jsonify({
            'finished': True,
            'evaluation_pending': True,
            'message': 'Evaluation is currently pending from the teacher.'
        })

    # Fetch evaluated paper
    questions = conn.execute("SELECT * FROM questions WHERE exam_id=? ORDER BY id", (student['exam_id'],)).fetchall()
    answers = conn.execute("SELECT * FROM student_answers WHERE exam_id=? AND username=?", 
                           (student['exam_id'], student['username'])).fetchall()
    conn.close()
    
    answer_dict = {a['question_id']: dict(a) for a in answers}
    
    evaluated_paper = []
    for q in questions:
        q_dict = dict(q)
        ans = answer_dict.get(q['id'])
        if ans:
             q_dict['student_answer'] = ans['submitted_text']
             q_dict['marks_awarded'] = ans['marks_awarded']
        else:
             q_dict['student_answer'] = None
             q_dict['marks_awarded'] = 0
        evaluated_paper.append(q_dict)

    return jsonify({
        'finished': True,
        'evaluation_pending': False,
        'score': prog['score'],
        'total': total_marks,
        'paper': evaluated_paper
    })

if __name__ == '__main__':
    init_db()
    # Restart the server loop automatically picks up changes with debug=True
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

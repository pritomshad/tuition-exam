import jwt
import datetime
import json
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from functools import wraps
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=False)
app.config['SECRET_KEY'] = 'super-secret-exam-key'

MONGO_URI = os.environ.get('MONGO_URI', 'mongodb+srv://pritomd678_db_user:<db_password>@tuition-exam.zw8hih5.mongodb.net/?appName=tuition-exam')
client = MongoClient(MONGO_URI)
db = client['exam_system']

def init_db():
    # Insert default admin if none exists
    admin = db.admins.find_one({"username": "admin"})
    if not admin:
        db.admins.insert_one({"username": "admin", "password": "admin"})
        
    # We can create indexes here if necessary
    db.student_credentials.create_index([("exam_id", 1), ("username", 1)], unique=True)
    db.admins.create_index("username", unique=True)

# Helper function to convert ObjectId to string in documents
def serialize_doc(doc):
    if doc and '_id' in doc:
        doc['id'] = str(doc.pop('_id'))
    return doc

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
    admin = db.admins.find_one({"username": data.get('username'), "password": data.get('password')})
    
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
    
    cred = db.student_credentials.find_one({"exam_id": exam_id, "username": username, "password": password})
    
    if cred:
        questions = list(db.questions.find({"exam_id": exam_id}))
        total_time_seconds = sum(q.get('solving_time', 0) for q in questions)
        expiry_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=total_time_seconds + 300)
        
        prog = db.student_progress.find_one({"exam_id": exam_id, "username": username})
        if not prog:
            db.student_progress.insert_one({
                "exam_id": exam_id, 
                "username": username,
                "current_q_index": 0,
                "score": 0,
                "q_start_time": None,
                "finished": False,
                "evaluation_pending": False
            })
            
        token = jwt.encode({
            'username': username,
            'exam_id': exam_id,
            'role': 'student',
            'exp': expiry_time
        }, app.config['SECRET_KEY'], algorithm="HS256")
        return jsonify({'token': token})
    
    return jsonify({'message': 'Invalid credentials or exam ID'}), 401


# --- Admin Endpoints ---

@app.route('/api/admin/exams', methods=['GET', 'POST'])
@admin_required
def handle_exams():
    if request.method == 'GET':
        exams = list(db.exams.find())
        return jsonify([serialize_doc(e) for e in exams])
    elif request.method == 'POST':
        data = request.json
        res = db.exams.insert_one({"title": data.get('title')})
        return jsonify({'id': str(res.inserted_id), 'message': 'Exam created successfully'})

@app.route('/api/admin/exams/<string:exam_id>/questions', methods=['GET', 'POST'])
@admin_required
def handle_questions(exam_id):
    if request.method == 'GET':
        questions = list(db.questions.find({"exam_id": exam_id}))
        # Sort questions by _id to keep consistent order
        questions.sort(key=lambda x: str(x['_id']))
        return jsonify([serialize_doc(q) for q in questions])
    elif request.method == 'POST':
        data = request.json
        marks = int(data.get('marks', 1))
        db.questions.insert_one({
            "exam_id": exam_id,
            "question_text": data.get('question_text'),
            "options": data.get('options'),
            "correct_answer": data.get('correct_answer'),
            "solving_time": data.get('solving_time'),
            "marks": marks
        })
        return jsonify({'message': 'Question added successfully'})

@app.route('/api/admin/exams/<string:exam_id>/questions/<string:q_id>', methods=['PUT', 'DELETE'])
@admin_required
def update_question(exam_id, q_id):
    if request.method == 'PUT':
        data = request.json
        update_data = {}
        if 'marks' in data:
            update_data['marks'] = int(data['marks'])
        if 'question_text' in data:
            update_data['question_text'] = data['question_text']
            update_data['options'] = data['options']
            update_data['correct_answer'] = data['correct_answer']
            update_data['solving_time'] = data['solving_time']
            
        if update_data:
            db.questions.update_one({"_id": ObjectId(q_id), "exam_id": exam_id}, {"$set": update_data})
        return jsonify({'message': 'Question updated successfully'})
    
    elif request.method == 'DELETE':
        db.questions.delete_one({"_id": ObjectId(q_id), "exam_id": exam_id})
        return jsonify({'message': 'Question deleted successfully'})

@app.route('/api/admin/exams/<string:exam_id>/students', methods=['POST'])
@admin_required
def add_student_credentials(exam_id):
    data = request.json
    try:
        db.student_credentials.insert_one({
            "exam_id": exam_id,
            "username": data['username'],
            "password": data['password']
        })
        msg = 'Student added to exam'
    except Exception as e:
        # duplicate key error
        if 'duplicate key error' in str(e).lower() or 'e11000' in str(e).lower():
            msg = 'Student already exists for this exam'
        else:
            msg = str(e)
            
    return jsonify({'message': msg})

@app.route('/api/admin/exams/<string:exam_id>/results', methods=['GET'])
@admin_required
def get_exam_results(exam_id):
    results = list(db.student_progress.find(
        {"exam_id": exam_id},
        {"_id": 0, "username": 1, "score": 1, "finished": 1, "evaluation_pending": 1}
    ))
    return jsonify(results)

@app.route('/api/admin/exams/<string:exam_id>/evaluation/<string:username>', methods=['GET'])
@admin_required
def get_student_evaluation(exam_id, username):
    questions = list(db.questions.find({"exam_id": exam_id}))
    questions.sort(key=lambda x: str(x['_id']))
    
    answers = list(db.student_answers.find({"exam_id": exam_id, "username": username}))
    
    answer_dict = {str(a['question_id']): a for a in answers}
    
    paper = []
    for q in questions:
        q_dict = serialize_doc(q)
        ans = answer_dict.get(q_dict['id'])
        if ans:
             q_dict['student_answer'] = ans.get('submitted_text')
             q_dict['marks_awarded'] = ans.get('marks_awarded', 0)
             q_dict['evaluated'] = bool(ans.get('evaluated', False))
             q_dict['answer_id'] = str(ans['_id'])
        else:
             q_dict['student_answer'] = None
             q_dict['marks_awarded'] = 0
             q_dict['evaluated'] = False
             q_dict['answer_id'] = None
        paper.append(q_dict)
        
    return jsonify(paper)

@app.route('/api/admin/exams/<string:exam_id>/evaluation/<string:username>', methods=['POST'])
@admin_required
def submit_student_evaluation(exam_id, username):
    data = request.json # Expected format: { answer_id: marks_awarded, ... }
    
    # Update individual answers
    for ans_id, marks in data.items():
        db.student_answers.update_one(
            {"_id": ObjectId(ans_id), "exam_id": exam_id, "username": username},
            {"$set": {"marks_awarded": int(marks), "evaluated": True}}
        )
    
    # Recalculate total score
    all_answers = list(db.student_answers.find({"exam_id": exam_id, "username": username}))
    total_score = sum(ans.get('marks_awarded', 0) for ans in all_answers)
        
    # Check if all questions are evaluated
    total_q = db.questions.count_documents({"exam_id": exam_id})
    eval_q = len([a for a in all_answers if a.get('evaluated', False)])
                          
    is_pending = (eval_q < total_q)
    
    db.student_progress.update_one(
        {"exam_id": exam_id, "username": username},
        {"$set": {"score": total_score, "evaluation_pending": is_pending}}
    )
                 
    return jsonify({'message': 'Evaluation saved successfully', 'score': total_score})


# --- Student Endpoints ---

@app.route('/api/student/question', methods=['GET'])
@student_required
def get_current_question():
    student = request.student_data
    exam_id = student['exam_id']
    username = student['username']
    
    prog = db.student_progress.find_one({"exam_id": exam_id, "username": username})
    
    if prog.get('finished'):
        return jsonify({'message': 'Exam finished', 'finished': True})
        
    questions = list(db.questions.find({"exam_id": exam_id}))
    questions.sort(key=lambda x: str(x['_id']))
    
    current_index = prog.get('current_q_index', 0)
    
    if current_index >= len(questions):
        db.student_progress.update_one(
            {"exam_id": exam_id, "username": username},
            {"$set": {"finished": True}}
        )
        return jsonify({'message': 'Exam finished', 'finished': True})
        
    current_q = serialize_doc(questions[current_index])
    
    q_start_time_iso = prog.get('q_start_time')
    if not q_start_time_iso:
        now = datetime.datetime.utcnow().isoformat()
        db.student_progress.update_one(
            {"exam_id": exam_id, "username": username},
            {"$set": {"q_start_time": now}}
        )
        q_start = datetime.datetime.fromisoformat(now)
    else:
        q_start = datetime.datetime.fromisoformat(q_start_time_iso)
    
    current_q.pop('correct_answer', None) # Hide from student
    
    elapsed = (datetime.datetime.utcnow() - q_start).total_seconds()
    time_remaining = max(0, current_q.get('solving_time', 0) - int(elapsed))
    
    current_q['time_remaining'] = time_remaining
    current_q['total_questions'] = len(questions)
    current_q['current_index'] = current_index
    
    return jsonify(current_q)

@app.route('/api/student/answer', methods=['POST'])
@student_required
def submit_answer():
    student = request.student_data
    exam_id = student['exam_id']
    username = student['username']
    data = request.json
    submitted_answer = data.get('answer', '')
    
    prog = db.student_progress.find_one({"exam_id": exam_id, "username": username})
    
    if prog.get('finished'):
        return jsonify({'message': 'Exam already finished'}), 400
        
    questions = list(db.questions.find({"exam_id": exam_id}))
    questions.sort(key=lambda x: str(x['_id']))
    
    current_index = prog.get('current_q_index', 0)
    
    if current_index >= len(questions):
        return jsonify({'message': 'No more questions'}), 400
        
    current_q = serialize_doc(questions[current_index])
    
    # Enforce time limits
    q_start_time_iso = prog.get('q_start_time')
    if q_start_time_iso:
        q_start = datetime.datetime.fromisoformat(q_start_time_iso)
        elapsed = (datetime.datetime.utcnow() - q_start).total_seconds()
        if elapsed > current_q.get('solving_time', 0) + 5:
            submitted_answer = '' # Timed out
            
    # Check if short answer or MCQ
    is_short_answer = False
    try:
        opts = json.loads(current_q.get('options', '[]'))
        if not opts or len(opts) == 0:
            is_short_answer = True
    except:
        if not current_q.get('options') or current_q['options'].strip() == '':
            is_short_answer = True

    marks_awarded = 0
    evaluated = False
    requires_eval = False

    if is_short_answer:
        # short answer -> manual evaluation needed
        marks_awarded = 0
        evaluated = False
        requires_eval = True
    else:
        # MCQ -> auto evaluation
        correct_answ = current_q.get('correct_answer', '')
        if submitted_answer and submitted_answer.strip() == correct_answ.strip():
            marks_awarded = current_q.get('marks', 1)
        evaluated = True
        
    # Save the individual answer
    db.student_answers.insert_one({
        "exam_id": exam_id,
        "username": username,
        "question_id": current_q['id'],
        "submitted_text": submitted_answer,
        "marks_awarded": marks_awarded,
        "evaluated": evaluated
    })
                 
    new_score = prog.get('score', 0) + marks_awarded
    new_index = current_index + 1
    finished = True if new_index >= len(questions) else False
    
    # Has pending evaluations if it required eval for this question OR it already had pending
    is_pending = True if (requires_eval or prog.get('evaluation_pending', False)) else False
    
    db.student_progress.update_one(
        {"exam_id": exam_id, "username": username},
        {"$set": {
            "current_q_index": new_index,
            "score": new_score,
            "q_start_time": None,
            "finished": finished,
            "evaluation_pending": is_pending
        }}
    )
    
    return jsonify({'success': True, 'finished': finished})

@app.route('/api/student/result', methods=['GET'])
@student_required
def get_result():
    student = request.student_data
    exam_id = student['exam_id']
    username = student['username']
    
    prog = db.student_progress.find_one({"exam_id": exam_id, "username": username})
    
    if not prog or not prog.get('finished'):
        return jsonify({'message': 'Exam not finished yet'}), 400
        
    if prog.get('evaluation_pending'):
        return jsonify({
            'finished': True,
            'evaluation_pending': True,
            'message': 'Evaluation is currently pending from the teacher.'
        })

    # Total possible marks
    questions = list(db.questions.find({"exam_id": exam_id}))
    questions.sort(key=lambda x: str(x['_id']))
    total_marks = sum(q.get('marks', 1) for q in questions)

    # Fetch evaluated paper
    answers = list(db.student_answers.find({"exam_id": exam_id, "username": username}))
    
    answer_dict = {str(a['question_id']): a for a in answers}
    
    evaluated_paper = []
    for q in questions:
        q_dict = serialize_doc(q)
        ans = answer_dict.get(q_dict['id'])
        if ans:
             q_dict['student_answer'] = ans.get('submitted_text')
             q_dict['marks_awarded'] = ans.get('marks_awarded', 0)
        else:
             q_dict['student_answer'] = None
             q_dict['marks_awarded'] = 0
        evaluated_paper.append(q_dict)

    return jsonify({
        'finished': True,
        'evaluation_pending': False,
        'score': prog.get('score', 0),
        'total': total_marks,
        'paper': evaluated_paper
    })

init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)


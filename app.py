import os
import json
import uuid

# pyrefly: ignore [missing-import]
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename

from agents.tracker_agent import TrackerAgent
from agents.resume_agent import ResumeAgent
from agents.dsa_agent import DSACoachAgent
from agents.interview_agent import InterviewAgent
from dotenv import load_dotenv
load_dotenv()
# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "campuspilot_secret_hackathon_2026")

# Configure upload settings (Max 5MB, PDF only)
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB limit
ALLOWED_EXTENSIONS = {'pdf'}

# Initialize Agents
tracker_agent = TrackerAgent()
resume_agent = ResumeAgent()
dsa_agent = DSACoachAgent()
interview_agent = InterviewAgent()

# Default Student ID for single-user hackathon app
STUDENT_ID = "fresher_2026"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_seed_questions():
    seed_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'seed_questions.json')
    try:
        with open(seed_path, 'r') as f:
            return json.load(f)
    except Exception:
        return {"aptitude": [], "gd_topics": [], "hr_questions": []}

@app.route('/')
def index():
    """
    Dashboard route. Displays student profile, recommended focus,
    weak areas, and session history from the Tracker Agent.
    """
    profile = tracker_agent.get_profile(STUDENT_ID)
    return render_template('index.html', profile=profile)

@app.route('/resume', methods=['GET', 'POST'])
def resume():
    """
    Resume Upload and ATS Matching route.
    Supports file validation, local PII redaction log, and scoring.
    """
    if request.method == 'POST':
        # Check if file part is present
        if 'resume_file' not in request.files:
            flash("No file part in request.", "danger")
            return redirect(request.url)
            
        file = request.files['resume_file']
        target_role = request.form.get('target_role', 'Software Engineer')
        
        if file.filename == '':
            flash("No file selected.", "danger")
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            try:
                # 1. Parse PDF
                resume_text = resume_agent.parse_resume(file_path)
                
                # 2. Score resume (Internally redacts PII before calling Gemini)
                score_data = resume_agent.score_against_jd(resume_text, target_role)
                
                # 3. Log results to Tracker
                feedback_summary = f"ATS Score: {score_data['ats_score']}. Weak sections: {', '.join(score_data['weak_sections'][:3])}."
                tracker_agent.log_session_result(
                    student_id=STUDENT_ID,
                    stage="resume",
                    score=score_data['ats_score'],
                    feedback=feedback_summary,
                    topic=f"Resume vs {target_role}"
                )
                
                # Clean up uploaded file for security
                os.remove(file_path)
                
                # Save review results in session for display
                session['latest_resume_score'] = score_data
                session['latest_target_role'] = target_role
                flash("Resume parsed and evaluated successfully!", "success")
                
            except Exception as e:
                flash(f"Error evaluating resume: {str(e)}", "danger")
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            return redirect(url_for('resume'))
        else:
            flash("Invalid file format. Only PDF files are allowed.", "danger")
            return redirect(request.url)

    # GET request
    latest_score = session.get('latest_resume_score', None)
    target_role = session.get('latest_target_role', '')
    return render_template('resume.html', latest_score=latest_score, target_role=target_role)

@app.route('/resume/rewrite', methods=['POST'])
def resume_rewrite():
    """
    AJAX endpoint to get rewrite suggestions for a specific weak section.
    """
    data = request.json or {}
    weak_section = data.get('section', '')
    if not weak_section:
        return jsonify({"error": "No section provided"}), 400
        
    suggestion = resume_agent.suggest_rewrite(weak_section)
    return jsonify({"suggestion": suggestion})

@app.route('/dsa', methods=['GET', 'POST'])
def dsa():
    """
    DSA Playground route. Handles problem generation, hints, and code submission evaluation.
    """
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'generate':
            topic = request.form.get('topic', 'Arrays')
            difficulty = request.form.get('difficulty', 'Easy')
            
            problem = dsa_agent.generate_problem(topic, difficulty)
            session['active_dsa_problem'] = problem
            session.pop('dsa_eval_result', None)
            session.pop('dsa_hint', None)
            return redirect(url_for('dsa'))
            
        elif action == 'hint':
            problem = session.get('active_dsa_problem')
            if problem:
                hint = dsa_agent.give_hint(problem['problem_id'])
                session['dsa_hint'] = hint
            return redirect(url_for('dsa'))
            
        elif action == 'submit':
            problem = session.get('active_dsa_problem')
            student_code = request.form.get('student_code', '')
            
            if problem and student_code.strip():
                # Evaluate solution
                eval_result = dsa_agent.evaluate_solution(problem['problem_id'], student_code)
                
                # Log score to Tracker Agent
                tracker_agent.log_session_result(
                    student_id=STUDENT_ID,
                    stage="dsa",
                    score=eval_result['score'],
                    feedback=f"Verdict: {eval_result['verdict']}. Time: {eval_result.get('time_complexity')}. feedback: {eval_result['detailed_feedback'][:100]}...",
                    topic=problem['topic']
                )
                
                session['dsa_eval_result'] = eval_result
                session['submitted_code'] = student_code
                flash(f"Code evaluated! Verdict: {eval_result['verdict']}, Score: {eval_result['score']}/100", "info")
                
            return redirect(url_for('dsa'))

    # GET Request
    active_problem = session.get('active_dsa_problem', None)
    dsa_hint = session.get('dsa_hint', None)
    eval_result = session.get('dsa_eval_result', None)
    submitted_code = session.get('submitted_code', '')
    
    return render_template('dsa.html', problem=active_problem, hint=dsa_hint, eval_result=eval_result, submitted_code=submitted_code)

@app.route('/interview', methods=['GET', 'POST'])
def interview():
    """
    Interview and GD simulator view.
    Manages conversational turns and triggers final scoring.
    """
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'start':
            mode = request.form.get('mode', 'HR') # 'GD' or 'HR'
            topic = request.form.get('topic', '')
            
            session['interview_mode'] = mode
            session['interview_topic'] = topic
            session['chat_history'] = []
            
            if mode == 'GD':
                # Start GD with opening statement from co-candidate
                opening = interview_agent.start_gd_round(topic)
                session['chat_history'] = [{"sender": "Rohan (Co-candidate)", "text": opening}]
            else:
                # Start HR with the first question
                session['chat_history'] = [{"sender": "HR Manager", "text": f"Welcome to your HR Round. Let's begin. {topic}"}]
                
            return redirect(url_for('interview'))
            
        elif action == 'message':
            user_message = request.form.get('user_message', '')
            history = session.get('chat_history', [])
            mode = session.get('interview_mode', 'HR')
            
            if user_message.strip():
                # Add user response to history
                history.append({"sender": "Student", "text": user_message})
                
                # Ask agent for followup
                followup = interview_agent.ask_followup(user_message, mode, history)
                sender_name = "Rohan (Co-candidate)" if mode == 'GD' else "HR Manager"
                history.append({"sender": sender_name, "text": followup})
                
                session['chat_history'] = history
            return redirect(url_for('interview'))
            
        elif action == 'submit':
            history = session.get('chat_history', [])
            mode = session.get('interview_mode', 'HR')
            topic = session.get('interview_topic', 'HR Interview')
            
            if history:
                # Filter down to just student and agent/co-candidate messages
                eval_result = interview_agent.score_response(history)
                
                # Log score to Tracker Agent
                tracker_agent.log_session_result(
                    student_id=STUDENT_ID,
                    stage=mode.lower(),
                    score=eval_result['score'],
                    feedback=f"Interview {mode} on '{topic}'. Score: {eval_result['score']}. Feedback: {eval_result['feedback'][:100]}...",
                    topic=topic
                )
                
                # Reset chat, save evaluation results
                session['latest_interview_eval'] = eval_result
                session.pop('chat_history', None)
                flash(f"Session ended. Evaluation complete! Score: {eval_result['score']}/100", "success")
                
            return redirect(url_for('interview'))
            
    # GET Request
    seed_data = load_seed_questions()
    active_history = session.get('chat_history', None)
    interview_mode = session.get('interview_mode', '')
    interview_topic = session.get('interview_topic', '')
    latest_eval = session.get('latest_interview_eval', None)
    
    return render_template('interview.html', 
                           seed_questions=seed_data['hr_questions'], 
                           gd_topics=seed_data['gd_topics'],
                           history=active_history, 
                           mode=interview_mode, 
                           topic=interview_topic,
                           eval_result=latest_eval)

@app.route('/aptitude', methods=['GET', 'POST'])
def aptitude():
    """
    Extra Aptitude Practice module.
    Draws questions from the Indian campus seed database.
    """
    seed_data = load_seed_questions()
    questions = seed_data.get('aptitude', [])
    
    if request.method == 'POST':
        q_id = request.form.get('q_id')
        selected_option = request.form.get('option')
        
        # Find question
        question = next((q for q in questions if q['id'] == q_id), None)
        
        if question and selected_option:
            is_correct = selected_option.strip() == question['answer'].strip()
            score = 100 if is_correct else 0
            
            # Log progress with Tracker
            tracker_agent.log_session_result(
                student_id=STUDENT_ID,
                stage="aptitude",
                score=score,
                feedback=f"Aptitude Question {q_id}. Correct: {is_correct}.",
                topic=question['category']
            )
            
            eval_data = {
                "question": question,
                "selected": selected_option,
                "is_correct": is_correct,
                "explanation": question['explanation']
            }
            session['latest_aptitude_eval'] = eval_data
            flash("Answer submitted!", "info")
            
        return redirect(url_for('aptitude'))
        
    # GET Request
    latest_eval = session.get('latest_aptitude_eval', None)
    
    # Pick a random question that isn't the same as latest if possible
    import random
    selected_question = None
    if questions:
        # If we have a previous run, pop it from session after displaying
        session.pop('latest_aptitude_eval', None)
        selected_question = random.choice(questions)
        
    return render_template('aptitude.html', question=selected_question, eval_result=latest_eval)

if __name__ == '__main__':
    # Launch Flask local dev server
    app.run(debug=True, host='127.0.0.1', port=5000)

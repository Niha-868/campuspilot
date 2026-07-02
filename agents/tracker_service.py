import os
import json
import threading
import logging
from typing import Dict, List, Any, Optional

# Set up logging for the service layer
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'student_profiles.json')
db_lock = threading.Lock()

class TrackerService:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        with db_lock:
            if not os.path.exists(self.db_path):
                os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
                with open(self.db_path, 'w') as f:
                    json.dump({}, f)

    def _read_db(self) -> Dict[str, Any]:
        with db_lock:
            try:
                with open(self.db_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}

    def _write_db(self, data: Dict[str, Any]):
        with db_lock:
            with open(self.db_path, 'w') as f:
                json.dump(data, f, indent=2)

    def get_profile(self, student_id: str) -> Dict[str, Any]:
        db = self._read_db()
        if student_id not in db:
            # Initialize default student profile
            db[student_id] = {
                "student_id": student_id,
                "weak_areas": {},  # Format: { topic: score/severity }
                "session_history": [],  # List of dicts containing session details
                "current_focus": "Resume Prep"  # Default starting point
            }
            self._write_db(db)
        return db[student_id]

    def save_profile(self, student_id: str, profile: Dict[str, Any]):
        db = self._read_db()
        db[student_id] = profile
        self._write_db(db)

    def log_session_result(self, student_id: str, stage: str, score: float, feedback: str, topic: Optional[str] = None) -> Dict[str, Any]:
        """
        Logs a training session result and recalculates the weak areas and next focus.
        stage can be: 'resume', 'dsa', 'gd', 'hr', 'aptitude'
        """
        profile = self.get_profile(student_id)
        
        # Add to session history
        session_entry = {
            "stage": stage,
            "score": score,
            "feedback": feedback,
            "topic": topic,
        }
        import datetime
        session_entry["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        profile["session_history"].append(session_entry)
        
        # Update weak areas based on the score
        # If score is low (< 75), increment the weakness severity for that topic
        # If score is high (>= 75), reduce the weakness severity or resolve it
        key = topic if topic else stage.upper()
        
        if score < 75:
            # Add or increase weakness severity
            current_severity = profile["weak_areas"].get(key, 0)
            profile["weak_areas"][key] = min(current_severity + (80 - score) / 10.0, 10.0) # Scale up to 10 max severity
        else:
            # Decrease weakness severity
            if key in profile["weak_areas"]:
                current_severity = profile["weak_areas"][key]
                new_severity = current_severity - (score - 70) / 10.0
                if new_severity <= 0:
                    del profile["weak_areas"][key]
                else:
                    profile["weak_areas"][key] = new_severity

        # Determine next focus based on performance
        profile["current_focus"] = self._compute_next_focus(profile)
        
        self.save_profile(student_id, profile)
        return profile

    def _compute_next_focus(self, profile: Dict[str, Any]) -> str:
        """
        Orchestration rule engine:
        1. If resume score is low (< 75) or resume prep hasn't occurred yet, keep focus on Resume Prep.
        2. If resume is good, check DSA performance. If there are weak areas in DSA or average DSA score is low, focus is DSA.
        3. If DSA is good, check GD and HR.
        """
        history = profile["session_history"]
        weak_areas = profile["weak_areas"]
        student_id = profile["student_id"]
        
        logging.info(f"[Tracker Decision Logic] Computing next focus for student: {student_id}")

        # Check Resume status
        resume_sessions = [s for s in history if s["stage"] == "resume"]
        if not resume_sessions:
            next_focus = "Resume Prep (Review and align your resume with JD)"
            logging.info(f"[Tracker Decision Logic] Decision: {next_focus} Reason: No resume session history found.")
            return next_focus
        latest_resume = resume_sessions[-1]
        if latest_resume["score"] < 75:
            next_focus = f"Resume Prep (Current score {latest_resume['score']}/100 is low. Focus on suggestions: {latest_resume['feedback'][:60]}...)"
            logging.info(f"[Tracker Decision Logic] Decision: {next_focus} Reason: Latest resume score {latest_resume['score']} is < 75.")
            return next_focus
            
        # Check Aptitude status
        apt_sessions = [s for s in history if s["stage"] == "aptitude"]
        if not apt_sessions:
            next_focus = "Aptitude Training (Practice Quant & Logical Reasoning, latest: no attempts)"
            logging.info(f"[Tracker Decision Logic] Decision: {next_focus} Reason: No aptitude attempts found in history.")
            return next_focus
        if apt_sessions[-1]["score"] < 75:
            next_focus = f"Aptitude Training (Practice Quant & Logical Reasoning, latest: score {apt_sessions[-1]['score']})"
            logging.info(f"[Tracker Decision Logic] Decision: {next_focus} Reason: Latest aptitude score {apt_sessions[-1]['score']} is < 75.")
            return next_focus

        # Check DSA status
        dsa_sessions = [s for s in history if s["stage"] == "dsa"]
        if not dsa_sessions:
            next_focus = "DSA Coach (Generate and solve a basic problem to start)"
            logging.info(f"[Tracker Decision Logic] Decision: {next_focus} Reason: No DSA session history found.")
            return next_focus
        
        # Look at weak DSA areas
        dsa_weak = [w for w in weak_areas if w in ["Arrays", "Linked Lists", "Stacks", "Queues", "Trees", "Graphs", "Dynamic Programming", "Recursion", "Searching & Sorting", "Strings", "Stacks & Queues", "Trees & Graphs", "Recursion & Backtracking"]]
        if dsa_weak:
            # Focus on the most severe weak topic
            sorted_weak = sorted(dsa_weak, key=lambda k: weak_areas[k], reverse=True)
            next_focus = f"DSA Coach (Practice easy-medium questions on: {sorted_weak[0]})"
            logging.info(f"[Tracker Decision Logic] Decision: {next_focus} Reason: Identified DSA weak areas: {dsa_weak}. Selecting highest severity: {sorted_weak[0]}.")
            return next_focus
            
        # Check GD & HR Interview status
        gd_sessions = [s for s in history if s["stage"] == "gd"]
        hr_sessions = [s for s in history if s["stage"] == "hr"]
        
        if not gd_sessions:
            next_focus = "Interview Simulator (Start Group Discussion round to practice structure and delivery)"
            logging.info(f"[Tracker Decision Logic] Decision: {next_focus} Reason: No GD rounds found in history.")
            return next_focus
        if not hr_sessions:
            next_focus = "Interview Simulator (Start HR Interview round to practice behavioral and fresher-specific answers)"
            logging.info(f"[Tracker Decision Logic] Decision: {next_focus} Reason: No HR interview rounds found in history.")
            return next_focus
            
        latest_gd = gd_sessions[-1]
        latest_hr = hr_sessions[-1]
        
        if latest_gd["score"] < 75:
            next_focus = f"Interview Simulator (Practice GD topic, latest GD score: {latest_gd['score']})"
            logging.info(f"[Tracker Decision Logic] Decision: {next_focus} Reason: Latest GD score {latest_gd['score']} is < 75.")
            return next_focus
        if latest_hr["score"] < 75:
            next_focus = f"Interview Simulator (Refine HR responses, latest HR score: {latest_hr['score']})"
            logging.info(f"[Tracker Decision Logic] Decision: {next_focus} Reason: Latest HR score {latest_hr['score']} is < 75.")
            return next_focus
            
        next_focus = "Placement Ready! (Conduct mock mixed interviews or advanced DSA questions)"
        logging.info(f"[Tracker Decision Logic] Decision: {next_focus} Reason: Resume, Aptitude, DSA, GD, and HR metrics are all above 75.")
        return next_focus

    def get_weak_areas(self, student_id: str) -> Dict[str, float]:
        profile = self.get_profile(student_id)
        return profile.get("weak_areas", {})

    def get_next_focus(self, student_id: str) -> str:
        profile = self.get_profile(student_id)
        return profile.get("current_focus", "Resume Prep")

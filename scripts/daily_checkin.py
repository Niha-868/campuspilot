import os
import sys

# Add parent directory to path so we can import from agents
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.tracker_agent import TrackerAgent

def main():
    tracker = TrackerAgent()
    student_id = "fresher_2026"
    profile = tracker.get_profile(student_id)
    
    # ANSI escape characters for color terminal printout
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    
    print("\n" + "="*60)
    print(f"   {HEADER}{BOLD}CampusPilot Daily Check-in Dashboard{END}   ")
    print("="*60)
    print(f"Student ID: {BOLD}{profile['student_id']}{END}")
    print(f"Current Status: {GREEN}Active{END}")
    print("-"*60)
    
    # Current Focus Recommendation
    print(f"{BOLD}Daily Focus Recommendation:{END}")
    print(f"  -> {BLUE}{BOLD}{profile['current_focus']}{END}")
    print("-"*60)
    
    # Weak Areas
    print(f"{BOLD}Identified Target Areas (Weaknesses):{END}")
    weak_areas = profile.get("weak_areas", {})
    if weak_areas:
        for topic, severity in weak_areas.items():
            bar_len = int(severity)
            bar = "#" * bar_len + "-" * (10 - bar_len)
            color = WARNING if severity < 5 else FAIL
            print(f"  - {topic:<25} [{color}{bar}{END}] Severity: {severity:.1f}/10")
    else:
        print(f"  {GREEN}No active weak areas! Excellent work. Keep practicing!{END}")
    print("-"*60)
    
    # History Summary
    print(f"{BOLD}Recent Activity Log (Last 3 sessions):{END}")
    history = profile.get("session_history", [])
    if history:
        for session in history[-3:]:
            score = session["score"]
            color = GREEN if score >= 75 else FAIL
            print(f"  [{session['timestamp']}] {session['stage'].upper():<8} - Score: {color}{score}/100{END}")
            print(f"    Feedback: {session['feedback']}")
    else:
        print("  No sessions completed yet. Open the Flask Web UI to start practicing!")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()

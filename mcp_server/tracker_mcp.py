import os
import sys
import json

# Ensure parent directory is in python path for absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP
from agents.tracker_service import TrackerService

mcp = FastMCP("CampusPilotTracker")
tracker = TrackerService()

@mcp.tool()
def get_profile(student_id: str) -> str:
    """
    Retrieves the complete profile of a student.
    """
    profile = tracker.get_profile(student_id)
    return json.dumps(profile, indent=2)

@mcp.tool()
def get_weak_areas(student_id: str) -> str:
    """
    Retrieves the identified weak areas of a student with their severity scores.
    """
    weak_areas = tracker.get_weak_areas(student_id)
    return json.dumps(weak_areas, indent=2)

@mcp.tool()
def log_session_result(student_id: str, stage: str, score: float, feedback: str = "", topic: str = None) -> str:
    """
    Logs the outcome of a training session and returns the updated student profile.
    - student_id: Unique student identifier.
    - stage: The training module ('resume', 'dsa', 'gd', 'hr', 'aptitude').
    - score: Score between 0 and 100.
    - feedback: Summary of the reviewer agent's critique.
    - topic: Subject/Topic of the session (e.g. 'Dynamic Programming' or 'Quant').
    """
    try:
        score_val = float(score)
    except ValueError:
        return "Error: Score must be a valid number."
        
    profile = tracker.log_session_result(student_id, stage, score_val, feedback, topic)
    return json.dumps(profile, indent=2)

@mcp.tool()
def get_next_focus(student_id: str) -> str:
    """
    Calculates the recommended next training focus area for the student.
    """
    return tracker.get_next_focus(student_id)

if __name__ == "__main__":
    # Runs the MCP server in stdio mode
    mcp.run()


import os
import json
import logging
from typing import Dict, Any, List
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class InterviewAgent:
    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            logging.warning("GROQ_API_KEY environment variable is not set. Interview Agent calls will fail.")
        else:
            logging.info("[Interview Agent] GROQ_API_KEY found. Agent ready.")

    def get_client(self):
        if not self.api_key:
            self.api_key = os.environ.get("GROQ_API_KEY")
            if not self.api_key:
                raise ValueError("GROQ_API_KEY environment variable is missing. Please set it in .env file.")
        return Groq(api_key=self.api_key)

    def start_gd_round(self, topic: str) -> str:
        """
        Starts a Group Discussion round by presenting an opening argument
        from a simulated co-candidate. Student must respond to this.
        """
        logging.info(f"[Interview Agent] Starting GD round on topic: {topic}")

        prompt = f"""
You are "Rohan", a confident and articulate engineering student participating in a Group Discussion (GD) round during an Indian campus placement drive.

The GD topic is: "{topic}"

Give a strong, structured opening statement (4-6 sentences) to start the discussion.
Take a clear position on the topic.
Use language appropriate for an Indian campus placement GD — formal but natural.
End your statement in a way that invites others to respond or share their views.
Return ONLY your spoken statement, no labels or prefixes.
"""
        client = self.get_client()
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}]
            )
            opening = response.choices[0].message.content.strip()
            logging.info(f"[Interview Agent] GD opening statement generated for topic: {topic}")
            return opening
        except Exception as e:
            logging.error(f"[Interview Agent] Error starting GD round: {str(e)}")
            return f"Error starting GD round: {str(e)}"

    def ask_followup(self, previous_answer: str, mode: str, history: List[Dict] = None) -> str:
        """
        Generates a contextual follow-up question/response based on
        the student's last answer. Mode is 'GD' or 'HR'.
        """
        logging.info(f"[Interview Agent] Generating {mode} follow-up based on student's answer.")

        if mode == "GD":
            prompt = f"""
You are "Rohan", a fellow student in a Group Discussion during an Indian campus placement drive.
The student just said: "{previous_answer}"

Respond naturally as a GD co-participant:
- Either challenge their point with a counter-argument, OR
- Build on their point and extend it further.
Keep your response to 3-5 sentences.
Be assertive but respectful — typical GD style.
Return ONLY your spoken response, no labels or prefixes.
"""
        else:  # HR mode
            # Build context from history
            history_text = ""
            if history:
                recent = history[-4:] if len(history) > 4 else history
                for msg in recent:
                    history_text += f"{msg['sender']}: {msg['text']}\n"

            prompt = f"""
You are a senior HR Manager conducting a campus placement interview for a top Indian company.
You are interviewing a fresher engineering student.

Recent conversation:
{history_text}

The student just answered: "{previous_answer}"

Ask ONE sharp follow-up question based specifically on what they just said.
Do not ask a generic question — dig deeper into their specific answer.
Keep it to 1-2 sentences.
Return ONLY your question, no labels or prefixes.
"""

        client = self.get_client()
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}]
            )
            followup = response.choices[0].message.content.strip()
            logging.info(f"[Interview Agent] {mode} follow-up generated.")
            return followup
        except Exception as e:
            logging.error(f"[Interview Agent] Error generating follow-up: {str(e)}")
            return f"Error generating follow-up: {str(e)}"

    def score_response(self, transcript: List[Dict]) -> Dict[str, Any]:
        """
        Evaluates the full conversation transcript and returns structured feedback.
        Scores on structure, clarity, and confidence signals.
        """
        logging.info("[Interview Agent] Scoring interview/GD transcript.")

        # Format transcript for the prompt
        formatted = ""
        for msg in transcript:
            formatted += f"{msg['sender']}: {msg['text']}\n\n"

        prompt = f"""
You are an expert placement trainer evaluating a student's performance in an interview or Group Discussion round for Indian campus placements.

Here is the full conversation transcript:
---
{formatted}
---

Evaluate ONLY the "Student" responses (not the HR/co-candidate responses).

Return ONLY a valid JSON object with exactly these keys:
{{
  "score": 78,
  "verdict": "Good",
  "feedback": "The student demonstrated clear structure and good use of examples. However, they could improve by being more assertive in the GD.",
  "strengths": ["Clear articulation", "Used relevant examples", "Maintained composure"],
  "improvements": ["Be more assertive", "Use more data/statistics to support points", "Avoid repeating the same point"],
  "clarity_score": 80,
  "structure_score": 75,
  "confidence_score": 70
}}

score must be integer between 0 and 100.
verdict must be one of: "Excellent", "Good", "Average", "Needs Improvement".
Return ONLY the JSON object, no extra text.
"""
        client = self.get_client()
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            # Ensure all keys exist
            result.setdefault("score", 0)
            result.setdefault("verdict", "Needs Improvement")
            result.setdefault("feedback", "Could not evaluate transcript.")
            result.setdefault("strengths", [])
            result.setdefault("improvements", [])
            result.setdefault("clarity_score", 0)
            result.setdefault("structure_score", 0)
            result.setdefault("confidence_score", 0)

            logging.info(f"[Interview Agent] Transcript scored: {result['score']}/100, Verdict: {result['verdict']}")
            return result

        except Exception as e:
            logging.error(f"[Interview Agent] Error scoring transcript: {str(e)}")
            return {
                "score": 0,
                "verdict": "Error",
                "feedback": f"Error scoring response: {str(e)}",
                "strengths": [],
                "improvements": [],
                "clarity_score": 0,
                "structure_score": 0,
                "confidence_score": 0
            }

import os
import json
import logging
import uuid
from typing import Dict, Any
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DSACoachAgent:
    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            logging.warning("GROQ_API_KEY environment variable is not set. DSA Agent calls will fail.")
        else:
            logging.info("[DSA Agent] GROQ_API_KEY found. Agent ready.")

        # In-memory problem store for this session
        self.problems = {}

    def get_client(self):
        if not self.api_key:
            self.api_key = os.environ.get("GROQ_API_KEY")
            if not self.api_key:
                raise ValueError("GROQ_API_KEY environment variable is missing. Please set it in .env file.")
        return Groq(api_key=self.api_key)

    def generate_problem(self, topic: str, difficulty: str) -> Dict[str, Any]:
        """
        Generates a DSA practice problem at a given difficulty level.
        No solution is included — only the problem statement.
        """
        logging.info(f"[DSA Agent] Generating {difficulty} problem on topic: {topic}")

        prompt = f"""
You are an expert DSA (Data Structures and Algorithms) coach preparing Indian engineering students for campus placements at companies like TCS, Infosys, Wipro, Zoho, Flipkart, and JP Morgan.

Generate ONE coding problem on the topic "{topic}" at "{difficulty}" difficulty level.

Return ONLY a valid JSON object with exactly these keys:
{{
  "title": "Two Sum",
  "topic": "Arrays",
  "difficulty": "Easy",
  "description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
  "input_format": "First line: array of integers. Second line: target integer.",
  "output_format": "Return indices of the two numbers as an array.",
  "constraints": ["2 <= nums.length <= 10^4", "-10^9 <= nums[i] <= 10^9"],
  "sample_input": "nums = [2, 7, 11, 15], target = 9",
  "sample_output": "[0, 1]",
  "hint_level_1": "Think about what complement you need for each number.",
  "hint_level_2": "A HashMap can store numbers you have already seen."
}}

Do NOT include any solution or code. Return ONLY the JSON object.
"""
        client = self.get_client()
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            problem = json.loads(response.choices[0].message.content)
            problem_id = str(uuid.uuid4())[:8]
            problem["problem_id"] = problem_id
            problem["topic"] = topic
            problem["difficulty"] = difficulty

            # Store in memory for hints/evaluation
            self.problems[problem_id] = problem
            logging.info(f"[DSA Agent] Problem generated with ID: {problem_id}")
            return problem

        except Exception as e:
            logging.error(f"[DSA Agent] Error generating problem: {str(e)}")
            return {
                "problem_id": "error",
                "title": "Error generating problem",
                "topic": topic,
                "difficulty": difficulty,
                "description": f"Error: {str(e)}",
                "input_format": "",
                "output_format": "",
                "constraints": [],
                "sample_input": "",
                "sample_output": "",
                "hint_level_1": "",
                "hint_level_2": ""
            }

    def give_hint(self, problem_id: str) -> str:
        """
        Gives a contextual hint for the problem — never the full solution.
        """
        logging.info(f"[DSA Agent] Generating hint for problem ID: {problem_id}")

        problem = self.problems.get(problem_id)
        if not problem:
            return "Problem not found. Please generate a new problem first."

        prompt = f"""
You are a DSA coaching assistant. A student is solving this problem:

Title: {problem.get('title', '')}
Description: {problem.get('description', '')}
Topic: {problem.get('topic', '')}
Difficulty: {problem.get('difficulty', '')}

Give ONE helpful hint that guides the student toward the solution without revealing the actual code or complete approach.
Keep it concise (2-3 sentences max).
Focus on the key insight or data structure they should think about.
"""
        client = self.get_client()
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}]
            )
            hint = response.choices[0].message.content.strip()
            logging.info(f"[DSA Agent] Hint generated for problem: {problem_id}")
            return hint
        except Exception as e:
            logging.error(f"[DSA Agent] Error generating hint: {str(e)}")
            hint1 = problem.get("hint_level_1", "")
            return hint1 if hint1 else f"Error generating hint: {str(e)}"

    def evaluate_solution(self, problem_id: str, student_code: str) -> Dict[str, Any]:
        """
        Evaluates student's submitted code for correctness, complexity, and structure.
        Returns a score (0-100) and detailed feedback.
        """
        logging.info(f"[DSA Agent] Evaluating solution for problem ID: {problem_id}")

        problem = self.problems.get(problem_id)
        if not problem:
            return {
                "score": 0,
                "verdict": "Error",
                "time_complexity": "Unknown",
                "space_complexity": "Unknown",
                "detailed_feedback": "Problem not found. Please generate a new problem first.",
                "improvements": []
            }

        prompt = f"""
You are an expert DSA evaluator for Indian campus placement preparation.

Problem: {problem.get('title', '')}
Description: {problem.get('description', '')}
Topic: {problem.get('topic', '')}
Difficulty: {problem.get('difficulty', '')}
Sample Input: {problem.get('sample_input', '')}
Expected Output: {problem.get('sample_output', '')}

Student's Submitted Code:
```
{student_code}
```

Evaluate this code and return ONLY a valid JSON object with exactly these keys:
{{
  "score": 85,
  "verdict": "Accepted",
  "time_complexity": "O(n)",
  "space_complexity": "O(n)",
  "detailed_feedback": "Good solution using HashMap. Handles edge cases well.",
  "improvements": ["Consider handling duplicate elements", "Variable names could be more descriptive"]
}}

verdict must be one of: "Accepted", "Partially Correct", "Wrong Answer", "Needs Improvement".
score must be integer between 0 and 100.
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

            # Ensure all required keys
            result.setdefault("score", 0)
            result.setdefault("verdict", "Needs Improvement")
            result.setdefault("time_complexity", "Unknown")
            result.setdefault("space_complexity", "Unknown")
            result.setdefault("detailed_feedback", "Could not evaluate solution.")
            result.setdefault("improvements", [])

            logging.info(f"[DSA Agent] Evaluation complete. Score: {result['score']}/100, Verdict: {result['verdict']}")
            return result

        except Exception as e:
            logging.error(f"[DSA Agent] Error evaluating solution: {str(e)}")
            return {
                "score": 0,
                "verdict": "Error",
                "time_complexity": "Unknown",
                "space_complexity": "Unknown",
                "detailed_feedback": f"Error evaluating solution: {str(e)}",
                "improvements": []
            }

import os
import re
import json
import logging
from typing import Dict, Any, Tuple
from pypdf import PdfReader
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ResumeAgent:
    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            logging.warning("GROQ_API_KEY environment variable is not set. Resume Agent calls will fail.")
        else:
            logging.info("[Resume Agent] GROQ_API_KEY found. Agent ready.")

    def get_client(self):
        if not self.api_key:
            self.api_key = os.environ.get("GROQ_API_KEY")
            if not self.api_key:
                raise ValueError("GROQ_API_KEY environment variable is missing. Please set it in .env file.")
        return Groq(api_key=self.api_key)

    def parse_resume(self, file_path: str) -> str:
        """
        Parses text from a local PDF resume file using pypdf.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Resume file not found at {file_path}")

        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text.strip()
        except Exception as e:
            logging.error(f"Error parsing PDF file {file_path}: {str(e)}")
            raise

    def redact_pii(self, text: str) -> Tuple[str, bool]:
        """
        Redacts PII (emails, phone numbers, full names) via regex locally.
        Logs that redaction occurred.
        """
        redacted = False
        redacted_fields = []

        # Email Redaction
        email_regex = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
        if re.search(email_regex, text):
            text = re.sub(email_regex, '[REDACTED_EMAIL]', text)
            redacted = True
            redacted_fields.append("Email")

        # Phone Redaction (Indian & Generic international)
        phone_regex = r'(?:\+?91[ -\.\/]?)?[6-9]\d{9}|(?:\+?\d{1,3}[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}'
        if re.search(phone_regex, text):
            text = re.sub(phone_regex, '[REDACTED_PHONE]', text)
            redacted = True
            redacted_fields.append("Phone")

        # Name Redaction - Label based
        name_label_regex = r'(?i)(?:name|full\s*name)\s*:\s*([^\n\r]+)'
        if re.search(name_label_regex, text):
            text = re.sub(name_label_regex, 'Name: [REDACTED_NAME]', text)
            redacted = True
            redacted_fields.append("Name (labeled)")

        # First non-empty line (usually candidate name)
        lines = text.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped:
                if len(stripped) < 40 and not any(kw in stripped.lower() for kw in ['resume', 'curriculum', 'cv', 'profile', 'experience', 'education']):
                    lines[i] = '[REDACTED_NAME]'
                    redacted = True
                    redacted_fields.append("Name (first line)")
                break
        text = '\n'.join(lines)

        if redacted:
            logging.info(f"SECURITY ALERT: PII Redaction occurred. Stripped: {', '.join(redacted_fields)}")

        return text, redacted

    def score_against_jd(self, resume_text: str, target_role: str) -> Dict[str, Any]:
        """
        Redacts PII locally, then sends resume text and target role to Groq.
        Returns: {ats_score: int, weak_sections: List[str], missing_keywords: List[str]}
        """
        # Redact PII first — before any LLM call
        logging.info("[PII Redaction Engine] Starting PII check on resume text before calling Groq API...")
        clean_text, was_redacted = self.redact_pii(resume_text)
        if was_redacted:
            logging.info("[PII Redaction Engine] PII checks completed: sensitive fields were successfully redacted.")
        else:
            logging.info("[PII Redaction Engine] PII checks completed: no sensitive information required redaction.")

        logging.info(f"[Resume Agent] Dispatching ATS evaluation request to Groq API for target role: '{target_role}'...")

        prompt = f"""
You are an expert technical recruiter and ATS (Applicant Tracking System) reviewer for top-tier Indian companies (like TCS, Infosys, Wipro, Zoho, Flipkart, JP Morgan, and global captives in India).
Evaluate the candidate's resume (supplied below) against the target role: "{target_role}".

Resume Text:
---
{clean_text}
---

Your evaluation should assess:
1. Relevance of projects and experience to the target role.
2. Structure and presentation quality.
3. Presence of key technical skills expected for this role.

Return ONLY a valid JSON object with exactly these keys:
{{
  "ats_score": 75,
  "weak_sections": ["Project 2 description lacks detail on tech stack", "Education section missing CGPA"],
  "missing_keywords": ["Spring Boot", "Docker"]
}}

ats_score must be an integer between 0 and 100.
weak_sections must be an array of actionable strings.
missing_keywords must be an array of skill/keyword strings.
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
            if "ats_score" not in result:
                result["ats_score"] = 50
            if "weak_sections" not in result:
                result["weak_sections"] = ["Could not extract weak sections."]
            if "missing_keywords" not in result:
                result["missing_keywords"] = []

            logging.info(f"[Resume Agent] ATS Score received: {result['ats_score']}/100")
            return result

        except Exception as e:
            logging.error(f"Error during Groq call in Resume Agent: {str(e)}")
            return {
                "ats_score": 0,
                "weak_sections": [f"Error calling Resume Agent: {str(e)}"],
                "missing_keywords": []
            }

    def suggest_rewrite(self, weak_section: str) -> str:
        """
        Suggests an improved rewrite of a flagged resume section.
        """
        logging.info("[Resume Agent] Dispatching rewrite suggestion request to Groq API...")
        prompt = f"""
You are a professional resume writer specializing in helping Indian engineering freshers secure roles in product and service companies.
Rewrite the following weak or poorly formatted section of a student's resume:

Weak Section:
"{weak_section}"

Provide an improved, high-impact version using action verbs, structural bullet points, and standard industry phrasing.
Ensure it is professional and directly ready to be copied into a resume.
Return your suggestions in markdown format, highlighting the revised text clearly.
"""
        client = self.get_client()
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"Error during Groq call in Resume Agent suggest_rewrite: {str(e)}")
            return f"Unable to generate rewrite: {str(e)}"

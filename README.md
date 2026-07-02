# CampusPilot 🎓✈️

CampusPilot is an AI-powered coach for the Indian college campus placement pipeline, designed for students preparing for Aptitude Tests, Resume Reviews, Data Structures & Algorithms (DSA), and Group Discussions (GD) / HR Interview Rounds.

Built with Python, Flask, and the Google Gemini API, CampusPilot implements a multi-agent orchestration pattern where specialized agents work together to target a student's weak areas.

## Features & Architecture

```
                       +-------------------+
                       |    Flask Web UI   |
                       +---------+---------+
                                 |
                                 v
                       +---------+---------+
                       |   Tracker Agent   | <--- (MCP Server)
                       +----+----+----+----+
                            |    |    |
         +------------------+    |    +-------------------+
         |                       v                        |
+--------+-------+       +-------+-------+       +--------+-------+
|  Resume Agent  |       |   DSA Agent   |       |Interview Agent |
| (JD Matching,  |       |  (Interactive |       |   (GD & HR     |
| PII Redact)    |       |  DSA Coach)   |       |  Simulations)  |
+----------------+       +---------------+       +----------------+
```

1. **Tracker/Orchestrator Agent**: Maintains the student profile and coordinates learning progression across all agents. Exposes data via a local MCP server.
2. **Resume Agent**: Scores resumes against Job Descriptions (JDs), suggests rewrites, and redacts PII before sending data to Gemini.
3. **DSA Coach Agent**: Generates coding problems, provides hints without giving solutions, and evaluates student code submissions.
4. **GD/HR Simulator Agent**: Conducts interactive mock group discussions and HR interviews, offering detailed scoring and structural feedback.

## Tech Stack

- **Backend**: Flask (Python)
- **AI Engine**: Google Gemini API via `google-genai` SDK
- **Data Sharing**: Model Context Protocol (MCP) using the Python `mcp` SDK
- **Storage**: Local JSON databases (no external DB setups required)
- **Frontend**: Custom premium Dark-Themed CSS layout

## Installation & Running

1. **Clone/Move to the project directory**:
   ```bash
   cd campuspilot
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set the Gemini API Key**:
   Create a `.env` file or export the key in your terminal:
   ```bash
   # Windows (PowerShell)
   $env:GEMINI_API_KEY="your-api-key-here"

   # Linux/macOS
   export GEMINI_API_KEY="your-api-key-here"
   ```

4. **Run the Flask Web App**:
   ```bash
   python app.py
   ```
   Open `http://127.0.0.1:5000` in your web browser.

5. **Run the Tracker MCP Server**:
   ```bash
   mcp dev mcp_server/tracker_mcp.py
   # Or run directly
   python mcp_server/tracker_mcp.py
   ```

## Security

Please refer to [SECURITY.md](SECURITY.md) for details on local PII redaction and secure file upload limits.

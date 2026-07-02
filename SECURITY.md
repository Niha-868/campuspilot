# Security Policy - CampusPilot

CampusPilot takes the privacy of student data and API key management seriously. This document describes the security controls built into the application.

## 1. Local PII Redaction

Before any resume text is analyzed by the **Resume Agent** using the Gemini API, a local PII redaction pass is executed:
- **Full Names**: Simple heuristics and labeling markers are used to remove name occurrences.
- **Email Addresses**: Checked via regular expressions and replaced with `[REDACTED_EMAIL]`.
- **Phone Numbers**: Filtered using regexes targeting standard Indian and international formats and replaced with `[REDACTED_PHONE]`.

This ensures that personally identifiable information (PII) is not transmitted to external LLM endpoints.

## 2. API Key Management

- **No Hardcoded Keys**: The Gemini API key must be supplied via the `GEMINI_API_KEY` environment variable.
- **Zero Log Rule**: The application does not write the API key to any console output, logs, or JSON files.
- **Git Exclusions**: The `.gitignore` file is explicitly configured to ignore `.env` files and any `*.key` or key configuration files.

## 3. Upload File Validation

The Flask backend validates any uploaded file before it is parsed or processed:
- **Allowed Extensions**: Only PDF files (`.pdf`) are accepted.
- **Size Limits**: The server rejects file uploads larger than 5 MB to prevent Denial of Service (DoS) attacks and excessive processing overhead.

## 4. Reporting Vulnerabilities

If you discover any security issues or vulnerabilities in CampusPilot, please report them locally to the hackathon project maintainers. Do not open public issues.

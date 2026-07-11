# AI Email Generator

AI Email Generator is a beginner-friendly Python Flask project that creates professional emails based on email type, tone, receiver name, sender name, and purpose.

## Features

- Generate job application, internship request, leave, apology, complaint, follow-up, thank-you, and meeting request emails
- Select tone: professional, formal, polite, friendly, short, or detailed
- Save generated emails in SQLite
- View recent email history
- Copy generated email
- Download generated email as `.txt`
- Works in demo mode without an API key
- Optional Gemini API or OpenAI API support

## Tools Used

- Python
- Flask
- SQLite
- HTML
- CSS
- Bootstrap
- JavaScript
- Gemini API or OpenAI API optional

## Setup

1. Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Optional: create a `.env` file from `.env.example` and add your API key.

```bash
copy .env.example .env
```

For demo mode, keep:

```env
AI_PROVIDER=fallback
```

4. Run the project:

```bash
python app.py
```

5. Open:

```text
http://127.0.0.1:5000
```

## Resume Description

**AI Email Generator | Python, Flask, SQLite, Bootstrap, Generative AI**

Developed a Flask-based AI Email Generator that creates professional emails based on selected type, tone, receiver details, sender name, and purpose. Implemented email history using SQLite, copy/download features, responsive Bootstrap UI, and optional Gemini/OpenAI API integration with local demo fallback.

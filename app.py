import os
import sqlite3
from datetime import datetime

import requests
from flask import Flask, jsonify, redirect, render_template, request, send_file, url_for
from dotenv import load_dotenv


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "instance", "emails.db")

load_dotenv(os.path.join(BASE_DIR, ".env"))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")


EMAIL_TYPES = [
    "Job Application",
    "Internship Request",
    "Leave Application",
    "Apology Email",
    "Complaint Email",
    "Follow-up Email",
    "Thank You Email",
    "Meeting Request",
]

TONES = ["Professional", "Formal", "Polite", "Friendly", "Short", "Detailed"]


def init_db():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    with sqlite3.connect(DATABASE) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS generated_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_type TEXT NOT NULL,
                tone TEXT NOT NULL,
                receiver_name TEXT,
                sender_name TEXT,
                purpose TEXT NOT NULL,
                output TEXT NOT NULL,
                provider TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def save_email(data, output, provider):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.execute(
            """
            INSERT INTO generated_emails
            (email_type, tone, receiver_name, sender_name, purpose, output, provider, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["email_type"],
                data["tone"],
                data.get("receiver_name", ""),
                data.get("sender_name", ""),
                data["purpose"],
                output,
                provider,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        return cursor.lastrowid


def build_prompt(data):
    return f"""
Write a clear, ready-to-send email.

Email type: {data['email_type']}
Tone: {data['tone']}
Receiver name: {data.get('receiver_name') or 'Not provided'}
Sender name: {data.get('sender_name') or 'Not provided'}
Main purpose/details: {data['purpose']}

Rules:
- Include a useful subject line.
- Use simple professional English.
- Keep the email practical and natural.
- Do not add placeholders unless a required detail is missing.
- End with the sender name if provided.
""".strip()


def generate_with_gemini(prompt):
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    if not api_key:
        return None

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    result = response.json()
    return result["candidates"][0]["content"]["parts"][0]["text"].strip()


def generate_with_openai(prompt):
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
    if not api_key:
        return None

    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={"model": model, "input": prompt},
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()

    if result.get("output_text"):
        return result["output_text"].strip()

    text_parts = []
    for item in result.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                text_parts.append(content.get("text", ""))
    return "\n".join(text_parts).strip()


def generate_fallback_email(data):
    receiver = data.get("receiver_name", "").strip() or "Sir/Madam"
    sender = data.get("sender_name", "").strip() or "Your Name"
    purpose = data["purpose"].strip()
    email_type = data["email_type"]
    tone = data["tone"].lower()

    subject_map = {
        "Job Application": "Application for Job Opportunity",
        "Internship Request": "Request for Internship Opportunity",
        "Leave Application": "Leave Application Request",
        "Apology Email": "Apology Regarding Recent Matter",
        "Complaint Email": "Complaint Regarding Service Issue",
        "Follow-up Email": "Follow-up Regarding Previous Communication",
        "Thank You Email": "Thank You",
        "Meeting Request": "Request for Meeting",
    }
    subject = subject_map.get(email_type, email_type)

    if tone == "short":
        body = (
            f"Subject: {subject}\n\n"
            f"Dear {receiver},\n\n"
            f"I am writing regarding {purpose}. Kindly consider my request and let me know if any "
            f"additional information is required.\n\n"
            f"Thank you.\n\n"
            f"Regards,\n{sender}"
        )
    else:
        body = (
            f"Subject: {subject}\n\n"
            f"Dear {receiver},\n\n"
            f"I hope you are doing well. I am writing to you regarding {purpose}.\n\n"
            f"I would be grateful if you could consider this request and guide me on the next steps. "
            f"Please let me know if any further details or documents are required from my side.\n\n"
            f"Thank you for your time and consideration.\n\n"
            f"Regards,\n{sender}"
        )
    return body


def generate_email(data):
    prompt = build_prompt(data)
    preferred = os.environ.get("AI_PROVIDER", "fallback").lower()

    providers = []
    if preferred == "gemini":
        providers = [("Gemini", generate_with_gemini), ("OpenAI", generate_with_openai)]
    elif preferred == "openai":
        providers = [("OpenAI", generate_with_openai), ("Gemini", generate_with_gemini)]
    else:
        providers = [("Gemini", generate_with_gemini), ("OpenAI", generate_with_openai)]

    for name, generator in providers:
        try:
            output = generator(prompt)
            if output:
                return output, name
        except Exception as exc:
            print(f"{name} generation failed: {exc}")

    return generate_fallback_email(data), "Local Demo Generator"


def get_history():
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            """
            SELECT id, email_type, tone, receiver_name, sender_name, provider, created_at
            FROM generated_emails
            ORDER BY id DESC
            LIMIT 10
            """
        ).fetchall()


def get_email(email_id):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            "SELECT * FROM generated_emails WHERE id = ?", (email_id,)
        ).fetchone()


@app.route("/")
def index():
    return render_template(
        "index.html",
        email_types=EMAIL_TYPES,
        tones=TONES,
        history=get_history(),
        generated=None,
        form={},
    )


@app.route("/generate", methods=["POST"])
def generate():
    data = {
        "email_type": request.form.get("email_type", "").strip(),
        "tone": request.form.get("tone", "").strip(),
        "receiver_name": request.form.get("receiver_name", "").strip(),
        "sender_name": request.form.get("sender_name", "").strip(),
        "purpose": request.form.get("purpose", "").strip(),
    }

    errors = []
    if data["email_type"] not in EMAIL_TYPES:
        errors.append("Please select a valid email type.")
    if data["tone"] not in TONES:
        errors.append("Please select a valid tone.")
    if not data["purpose"]:
        errors.append("Please enter the email purpose/details.")

    if errors:
        return render_template(
            "index.html",
            email_types=EMAIL_TYPES,
            tones=TONES,
            history=get_history(),
            generated=None,
            form=data,
            errors=errors,
        )

    output, provider = generate_email(data)
    email_id = save_email(data, output, provider)

    return render_template(
        "index.html",
        email_types=EMAIL_TYPES,
        tones=TONES,
        history=get_history(),
        generated={"id": email_id, "output": output, "provider": provider},
        form=data,
    )


@app.route("/history/<int:email_id>")
def history_detail(email_id):
    email = get_email(email_id)
    if not email:
        return redirect(url_for("index"))
    return render_template("detail.html", email=email)


@app.route("/download/<int:email_id>")
def download_email(email_id):
    email = get_email(email_id)
    if not email:
        return jsonify({"error": "Email not found"}), 404

    filename = os.path.join(BASE_DIR, "instance", f"email_{email_id}.txt")
    with open(filename, "w", encoding="utf-8") as file:
        file.write(email["output"])
    return send_file(filename, as_attachment=True, download_name=f"email_{email_id}.txt")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)

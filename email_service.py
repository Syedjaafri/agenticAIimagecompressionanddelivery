from __future__ import annotations
import os
import smtplib
import ssl
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()


def send_image_email(
    recipient: str,
    subject: str,
    message: str,
    attachment_bytes: bytes,
    attachment_name: str = "optimized_image.jpg",
) -> dict:
    sender = os.getenv("SENDER_EMAIL", "").strip()
    app_password = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.getenv("SMTP_PORT", "465"))

    if not sender or not app_password:
        return {"success": False, "status": "configuration_error", "message": "Sender Gmail or App Password is missing."}

    email = EmailMessage()
    email["From"] = sender
    email["To"] = recipient
    email["Subject"] = subject or "Optimized Image"
    email.set_content(message or "Please find the optimized image attached.")
    email.add_attachment(attachment_bytes, maintype="image", subtype="jpeg", filename=attachment_name)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as smtp:
            smtp.login(sender, app_password)
            smtp.send_message(email)
        return {
            "success": True,
            "status": "accepted_by_smtp_server",
            "message": "Email was accepted by the Gmail SMTP server.",
        }
    except Exception as exc:
        return {"success": False, "status": "send_error", "message": str(exc)}

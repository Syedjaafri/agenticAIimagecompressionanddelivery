from __future__ import annotations
import os
import smtplib
import ssl
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()


def _get_credential(key: str, override: str | None = None) -> str:
    if override and override.strip():
        return override.strip()
    try:
        import streamlit as st
        if key in st.secrets:
            return str(st.secrets[key]).strip()
    except Exception:
        pass
    return os.getenv(key, "").strip()


def send_image_email(
    recipient: str,
    subject: str,
    message: str,
    attachment_bytes: bytes,
    attachment_name: str = "optimized_image.jpg",
    sender: str | None = None,
    app_password: str | None = None,
    user_sender_email: str | None = None,
) -> dict:
    # 1. Determine active sender credentials and SMTP host
    is_direct_user_send = False
    if user_sender_email and user_sender_email.strip() and app_password and app_password.strip():
        active_sender = user_sender_email.strip()
        active_pass = app_password.replace(" ", "").strip()
        is_direct_user_send = True
    else:
        active_sender = _get_credential("SENDER_EMAIL", sender)
        active_pass = _get_credential("GMAIL_APP_PASSWORD", app_password).replace(" ", "")

    if not active_sender or not active_pass:
        return {
            "success": False,
            "status": "configuration_error",
            "message": "Sender Email or App Password is missing. Please enter your email and password to send directly.",
        }

    # Auto-detect SMTP host based on sender email domain
    domain = active_sender.split("@")[-1].lower() if "@" in active_sender else ""
    if "outlook" in domain or "hotmail" in domain or "office365" in domain or "annauniv" in domain or "microsoft" in domain:
        host = "smtp.office365.com"
        port = 587
    else:
        host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
        port = int(os.getenv("SMTP_PORT", "465"))

    email = EmailMessage()
    email["From"] = active_sender  # 100% Direct Sender address (No 'via' tag!)
    email["Reply-To"] = active_sender
    email["To"] = recipient
    email["Subject"] = subject or "Optimized Image"
    email.set_content(message or "Please find the optimized image attached.")
    email.add_attachment(attachment_bytes, maintype="image", subtype="jpeg", filename=attachment_name)

    try:
        context = ssl.create_default_context()
        if port == 465:
            try:
                with smtplib.SMTP_SSL(host, 465, context=context, timeout=15) as smtp:
                    smtp.login(active_sender, active_pass)
                    smtp.send_message(email)
            except Exception:
                with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as smtp:
                    smtp.starttls(context=context)
                    smtp.login(active_sender, active_pass)
                    smtp.send_message(email)
        else:
            with smtplib.SMTP(host, port, timeout=15) as smtp:
                smtp.starttls(context=context)
                smtp.login(active_sender, active_pass)
                smtp.send_message(email)

        mode_desc = "Directly from sender account" if is_direct_user_send else "Central delivery service"
        return {
            "success": True,
            "status": "accepted_by_smtp_server",
            "message": f"Email successfully sent directly from {active_sender} ({mode_desc}) to {recipient}.",
        }
    except Exception as exc:
        return {"success": False, "status": "send_error", "message": str(exc)}


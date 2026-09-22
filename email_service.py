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


from oauth_service import send_email_via_gmail_api

def send_image_email(
    recipient: str,
    subject: str,
    message: str,
    attachment_bytes: bytes,
    attachment_name: str = "optimized_image.jpg",
    sender: str | None = None,
    app_password: str | None = None,
    user_sender_email: str | None = None,
    oauth_token: dict | None = None,
) -> dict:
    # 0. If user authenticated via Google OAuth 2.0, send 100% directly via Gmail API!
    if oauth_token:
        return send_email_via_gmail_api(
            token_dict=oauth_token,
            recipient=recipient,
            subject=subject,
            message=message,
            attachment_bytes=attachment_bytes,
            attachment_name=attachment_name,
        )
    # 1. Determine active sender credentials and SMTP host
    is_direct_user_send = False
    if user_sender_email and user_sender_email.strip() and app_password and app_password.strip():
        active_sender = user_sender_email.strip()
        active_pass = app_password.replace(" ", "").strip()
        is_direct_user_send = True
    server_email = _get_credential("SENDER_EMAIL", sender)
    app_pass = _get_credential("GMAIL_APP_PASSWORD", app_password).replace(" ", "")
    host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.getenv("SMTP_PORT", "465"))

    if not server_email or not app_pass:
        return {
            "success": False,
            "status": "configuration_error",
            "message": "Sender Gmail or App Password is missing. Please configure Streamlit Secrets.",
        }

    email = EmailMessage()
    if user_sender_email and user_sender_email.strip():
        sender_identity = user_sender_email.strip()
        email["From"] = f"Image Delivery Service <{server_email}>"
        email["Reply-To"] = sender_identity
    else:
        email["From"] = f"Image Delivery Service <{server_email}>"
    email["To"] = recipient
    email["Subject"] = subject or "Optimized Image"
    email.set_content(message or "Please find the optimized image attached.")
    email.add_attachment(attachment_bytes, maintype="image", subtype="jpeg", filename=attachment_name)

    try:
        context = ssl.create_default_context()
        if port == 465:
            try:
                with smtplib.SMTP_SSL(host, 465, context=context, timeout=15) as smtp:
                    smtp.login(server_email, app_pass)
                    smtp.send_message(email)
            except Exception:
                with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as smtp:
                    smtp.starttls(context=context)
                    smtp.login(server_email, app_pass)
                    smtp.send_message(email)
        else:
            with smtplib.SMTP(host, port, timeout=15) as smtp:
                smtp.starttls(context=context)
                smtp.login(server_email, app_pass)
                smtp.send_message(email)

        return {
            "success": True,
            "status": "accepted_by_smtp_server",
            "message": f"Email successfully sent from {email['From']} to {recipient}.",
        }
    except Exception as exc:
        return {"success": False, "status": "send_error", "message": str(exc)}


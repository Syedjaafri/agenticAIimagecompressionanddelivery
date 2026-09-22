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
    server_email = _get_credential("SENDER_EMAIL", sender)
    app_pass = _get_credential("GMAIL_APP_PASSWORD", app_password).replace(" ", "")
    host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.getenv("SMTP_PORT", "465"))

    if not server_email or not app_pass:
        return {
            "success": False,
            "status": "configuration_error",
            "message": "Sender Gmail or App Password is missing. Please configure Streamlit Secrets or enter Sender Credentials in the app settings.",
        }

    email = EmailMessage()
    if user_sender_email and user_sender_email.strip():
        display_sender = user_sender_email.strip()
        email["From"] = f"{display_sender} via Image Delivery Service <{server_email}>"
        email["Reply-To"] = display_sender
    else:
        email["From"] = server_email

    email["To"] = recipient
    email["Subject"] = subject or "Optimized Image"
    email.set_content(message or "Please find the optimized image attached.")
    email.add_attachment(attachment_bytes, maintype="image", subtype="jpeg", filename=attachment_name)

    try:
        context = ssl.create_default_context()
        if port == 465:
            try:
                with smtplib.SMTP_SSL(host, 465, context=context, timeout=15) as smtp:
                    smtp.login(sender_email, app_pass)
                    smtp.send_message(email)
            except Exception:
                # Fallback to Port 587 TLS if Port 465 is blocked by network firewall
                with smtplib.SMTP(host, 587, timeout=15) as smtp:
                    smtp.starttls(context=context)
                    smtp.login(sender_email, app_pass)
                    smtp.send_message(email)
        else:
            with smtplib.SMTP(host, port, timeout=15) as smtp:
                smtp.starttls(context=context)
                smtp.login(sender_email, app_pass)
                smtp.send_message(email)

        return {
            "success": True,
            "status": "accepted_by_smtp_server",
            "message": f"Email successfully sent from {sender_email} and accepted by the Gmail SMTP server.",
        }
    except Exception as exc:
        return {"success": False, "status": "send_error", "message": str(exc)}


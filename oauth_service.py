from __future__ import annotations
import os
import base64
from email.message import EmailMessage
import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
]


def _get_oauth_config() -> dict:
    """Retrieve Google OAuth Client ID & Secret from secrets or env."""
    client_id = ""
    client_secret = ""
    try:
        if "google_oauth" in st.secrets:
            client_id = str(st.secrets["google_oauth"].get("client_id", "")).strip()
            client_secret = str(st.secrets["google_oauth"].get("client_secret", "")).strip()
    except Exception:
        pass

    if "YOUR_CLIENT_ID" in client_id:
        client_id = ""
    if "YOUR_CLIENT_SECRET" in client_secret:
        client_secret = ""

    return {"client_id": client_id, "client_secret": client_secret}


def get_oauth_flow(redirect_uri: str) -> Flow:
    config = _get_oauth_config()
    client_config = {
        "web": {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = redirect_uri
    return flow


def exchange_code_for_token(code: str, redirect_uri: str) -> dict:
    """Exchange authorization code directly via Google OAuth REST API to avoid state mismatch."""
    import requests
    config = _get_oauth_config()
    payload = {
        "code": code,
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    resp = requests.post("https://oauth2.googleapis.com/token", data=payload, timeout=15)
    data = resp.json()
    if "access_token" in data:
        return {
            "token": data["access_token"],
            "refresh_token": data.get("refresh_token", ""),
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "scopes": SCOPES,
        }
    else:
        err_msg = data.get("error_description", data.get("error", "OAuth exchange failed"))
        raise Exception(f"Google Token Exchange Error: {err_msg}")


def send_email_via_gmail_api(
    token_dict: dict,
    recipient: str,
    subject: str,
    message: str,
    attachment_bytes: bytes,
    attachment_name: str = "optimized_image.jpg",
) -> dict:
    """Send email directly from authenticated user's account using Google Gmail API."""
    try:
        creds = Credentials.from_authorized_user_info(token_dict, SCOPES)
        service = build("gmail", "v1", credentials=creds)

        email = EmailMessage()
        email["To"] = recipient
        email["Subject"] = subject or "Optimized Image"
        email.set_content(message or "Please find the optimized image attached.")
        email.add_attachment(attachment_bytes, maintype="image", subtype="jpeg", filename=attachment_name)

        raw_message = base64.urlsafe_b64encode(email.as_bytes()).decode()
        sent_msg = service.users().messages().send(userId="me", body={"raw": raw_message}).execute()

        return {
            "success": True,
            "status": "sent_via_gmail_api",
            "message": f"Email sent 100% directly from your Google Account to {recipient}! (Message ID: {sent_msg.get('id')})",
        }
    except Exception as exc:
        return {"success": False, "status": "oauth_send_error", "message": f"Gmail API delivery failed: {str(exc)}"}

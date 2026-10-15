from __future__ import annotations
import os
import base64
from email.message import EmailMessage
import streamlit as st
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
]


def _get_oauth_config() -> dict:
    """Retrieve Google OAuth Client ID & Secret from secrets or env across all schema formats."""
    client_id = ""
    client_secret = ""

    # 1. Check top-level secrets
    try:
        if "client_id" in st.secrets:
            client_id = str(st.secrets["client_id"]).strip()
        if "client_secret" in st.secrets:
            client_secret = str(st.secrets["client_secret"]).strip()
        if "GOOGLE_CLIENT_ID" in st.secrets:
            client_id = str(st.secrets["GOOGLE_CLIENT_ID"]).strip()
        if "GOOGLE_CLIENT_SECRET" in st.secrets:
            client_secret = str(st.secrets["GOOGLE_CLIENT_SECRET"]).strip()
    except Exception:
        pass

    # 2. Check google_oauth section in secrets
    try:
        if (not client_id or not client_secret) and "google_oauth" in st.secrets:
            sec = st.secrets["google_oauth"]
            if hasattr(sec, "get"):
                client_id = str(sec.get("client_id", sec.get("GOOGLE_CLIENT_ID", client_id))).strip()
                client_secret = str(sec.get("client_secret", sec.get("GOOGLE_CLIENT_SECRET", client_secret))).strip()
    except Exception:
        pass

    # 3. Check env variables
    if not client_id:
        client_id = os.getenv("GOOGLE_CLIENT_ID", os.getenv("CLIENT_ID", "")).strip()
    if not client_secret:
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET", os.getenv("CLIENT_SECRET", "")).strip()

    if "YOUR_CLIENT_ID" in client_id:
        client_id = ""
    if "YOUR_CLIENT_SECRET" in client_secret:
        client_secret = ""

    return {"client_id": client_id, "client_secret": client_secret}


def get_authorization_url(redirect_uri: str) -> str:
    """Construct standard OAuth 2.0 authorization URL requesting offline access and refresh consent."""
    import urllib.parse
    config = _get_oauth_config()
    params = {
        "client_id": config["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"


def exchange_code_for_token(code: str, redirect_uri: str) -> dict:
    """Exchange authorization code directly via Google OAuth REST API and fetch user profile."""
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
        user_email = ""
        try:
            user_resp = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {data['access_token']}"},
                timeout=10,
            )
            if user_resp.status_code == 200:
                user_email = user_resp.json().get("email", "")
        except Exception:
            pass

        # If Google omitted refresh_token on re-auth, preserve existing valid refresh_token
        existing_refresh = ""
        try:
            if "google_user_token" in st.session_state and isinstance(st.session_state.google_user_token, dict):
                existing_refresh = st.session_state.google_user_token.get("refresh_token", "")
        except Exception:
            pass

        refresh_token = data.get("refresh_token") or existing_refresh

        return {
            "token": data["access_token"],
            "refresh_token": refresh_token,
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "scopes": SCOPES,
            "user_email": user_email,
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
    """Send email directly from authenticated user's account using Google Gmail API with auto-refresh."""
    if not isinstance(token_dict, dict) or not token_dict.get("token"):
        return {
            "success": False,
            "status": "missing_token",
            "message": "Direct Google connection token is missing. Please sign in again.",
            "token_expired": True,
        }

    config = _get_oauth_config()
    client_id = token_dict.get("client_id") or config.get("client_id", "")
    client_secret = token_dict.get("client_secret") or config.get("client_secret", "")
    refresh_token = str(token_dict.get("refresh_token", "")).strip()
    token_uri = token_dict.get("token_uri") or "https://oauth2.googleapis.com/token"

    try:
        # Construct Credentials with full refresh configuration
        creds = Credentials(
            token=token_dict.get("token", ""),
            refresh_token=refresh_token if refresh_token else None,
            token_uri=token_uri,
            client_id=client_id if client_id else None,
            client_secret=client_secret if client_secret else None,
            scopes=SCOPES,
        )

        # Proactively refresh token if expired and refresh_token is present
        if creds.refresh_token:
            from google.auth.transport.requests import Request
            try:
                if creds.expired or not creds.valid:
                    creds.refresh(Request())
                    if creds.token:
                        token_dict["token"] = creds.token
            except Exception:
                pass

        service = build("gmail", "v1", credentials=creds)

        email = EmailMessage()
        email["To"] = recipient
        email["Subject"] = subject or "Optimized Image"
        email.set_content(message or "Please find the optimized image attached.")
        email.add_attachment(attachment_bytes, maintype="image", subtype="jpeg", filename=attachment_name)

        raw_message = base64.urlsafe_b64encode(email.as_bytes()).decode()
        sent_msg = service.users().messages().send(userId="me", body={"raw": raw_message}).execute()

        # Update in-memory token if auto-refreshed during execute()
        if creds.token:
            token_dict["token"] = creds.token

        return {
            "success": True,
            "status": "sent_via_gmail_api",
            "message": f"Email sent directly from your Google Account to {recipient}! (Message ID: {sent_msg.get('id')})",
        }
    except Exception as exc:
        err_str = str(exc)
        is_token_issue = any(k in err_str.lower() for k in ["refresh", "invalid_grant", "credentials", "token", "unauthorized", "401"])
        return {
            "success": False,
            "status": "oauth_token_expired" if is_token_issue else "oauth_send_error",
            "message": f"Gmail API delivery failed: {err_str}",
            "token_expired": is_token_issue,
        }

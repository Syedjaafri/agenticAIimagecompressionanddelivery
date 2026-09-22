import os
from pathlib import Path
import json
import joblib
import pandas as pd
import streamlit as st

from image_features import extract_image_features
from compression_agent import generate_candidates, choose_best_candidate, transmission_seconds
from delivery_workflow import deliver_optimized_image
from train_model import train_and_save

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "models" / "compression_model.joblib"
METRICS_PATH = ROOT / "models" / "model_metrics.json"
SUPPORTED_QUALITIES = [30, 40, 50, 60, 70, 80, 90]

st.set_page_config(page_title="Agentic AI Image Delivery", page_icon="📨", layout="wide")


def get_secret(key: str) -> str:
    try:
        if key in st.secrets:
            return str(st.secrets[key]).strip()
    except Exception:
        pass
    return os.getenv(key, "").strip()


def nearest_quality(value: float) -> int:
    return min(SUPPORTED_QUALITIES, key=lambda q: abs(q - value))


@st.cache_resource
def load_model():
    if not MODEL_PATH.exists():
        train_and_save()
    return joblib.load(MODEL_PATH)


def build_model_row(features, intended_use, minimum_similarity, network_mbps, max_attachment_kb):
    return pd.DataFrame([{
        **features,
        "intended_use": intended_use,
        "minimum_similarity": minimum_similarity,
        "network_mbps": network_mbps,
        "max_attachment_kb": max_attachment_kb,
    }])


st.title("Agentic AI-Assisted Adaptive Image Compression and Intelligent Email Delivery")
st.caption("Optimize an image, verify its quality, and deliver it through an AI Agent-controlled email workflow.")

with st.sidebar:
    st.header("Compression Settings")
    intended_use = st.selectbox("Intended use", ["Mobile sharing", "Website", "Email", "Cloud storage", "High-quality archive"], index=2)
    defaults = {"Mobile sharing": 0.88, "Website": 0.90, "Email": 0.91, "Cloud storage": 0.92, "High-quality archive": 0.96}
    minimum_similarity = st.slider("Minimum visual similarity", 0.80, 0.99, defaults[intended_use], 0.01)
    network_label = st.selectbox("Network condition", ["Slow rural link (0.256 Mbps)", "Basic mobile link (1 Mbps)", "Moderate connection (5 Mbps)", "Fast connection (10 Mbps)"])
    network_map = {"Slow rural link (0.256 Mbps)": 0.256, "Basic mobile link (1 Mbps)": 1.0, "Moderate connection (5 Mbps)": 5.0, "Fast connection (10 Mbps)": 10.0}
    network_mbps = network_map[network_label]
    max_attachment_kb = st.number_input("Maximum attachment size (KB)", min_value=50, max_value=25_000, value=1024, step=50)

    st.divider()
    st.header("Sender Email Setup")
    configured_sender = get_secret("SENDER_EMAIL")
    configured_pass = get_secret("GMAIL_APP_PASSWORD")

    if configured_sender and configured_pass:
        st.success(f"Configured Sender: `{configured_sender}`")
        sender_email_val = configured_sender
        sender_app_pass_val = configured_pass
    else:
        st.info("ℹ️ **Chrome Login vs Python SMTP**\nBeing logged into Chrome does not grant this hosted Python web app access to your Gmail account. Configure credentials below or set Streamlit Cloud Secrets.")
        sender_email_val = st.text_input("Sender Gmail Address", value=configured_sender or "", placeholder="e.g. jaafri474@gmail.com")
        sender_app_pass_val = st.text_input("Google App Password (16 chars)", type="password", value=configured_pass or "", placeholder="e.g. abcd efgh ijkl mnop")
        with st.expander("🔑 How to get a 16-char App Password"):
            st.markdown("""
            1. Go to your **[Google Account Security](https://myaccount.google.com/security)**.
            2. Ensure **2-Step Verification** is turned ON.
            3. Search for **App passwords** in the top search bar.
            4. Create an App password (name it 'Streamlit App') and copy the 16-character code.
            5. Paste it above or add it to **Streamlit Cloud Secrets** (`SENDER_EMAIL` and `GMAIL_APP_PASSWORD`).
            """)

uploaded = st.file_uploader("Upload a JPG, JPEG, or PNG image", type=["jpg", "jpeg", "png"])

current_settings = (intended_use, minimum_similarity, network_mbps, max_attachment_kb)

if "best" not in st.session_state:
    st.session_state.best = None
    st.session_state.original_bytes = None
    st.session_state.candidates = None
    st.session_state.ml_quality = None
    st.session_state.last_settings = None

if uploaded:
    original_bytes = uploaded.getvalue()
    
    # Reset state if uploaded file or settings change
    if st.session_state.original_bytes != original_bytes or st.session_state.last_settings != current_settings:
        st.session_state.best = None
        st.session_state.candidates = None
        st.session_state.ml_quality = None
        st.session_state.original_bytes = original_bytes
        st.session_state.last_settings = current_settings

    features = extract_image_features(original_bytes)
    model = load_model()

    if st.button("Optimize and Preview", type="primary", use_container_width=True):
        row = build_model_row(features, intended_use, minimum_similarity, network_mbps, max_attachment_kb)
        prediction = float(model.predict(row)[0])
        ml_quality = nearest_quality(prediction)
        candidates = generate_candidates(original_bytes, minimum_similarity, network_mbps, max_attachment_kb)
        best = choose_best_candidate(candidates)

        st.session_state.best = best
        st.session_state.candidates = candidates
        st.session_state.ml_quality = ml_quality

    if st.session_state.candidates:
        best = st.session_state.best
        
        if best is None:
            st.error("No candidate satisfies both the visual-quality and attachment-size requirements. Increase the attachment limit or reduce the similarity requirement.")
        else:
            left, right = st.columns(2)
            with left:
                st.image(original_bytes, caption=f"Original: {len(original_bytes)/1024:.1f} KB", use_container_width=True)
            with right:
                st.image(best["image_bytes"], caption=f"Optimized Q{best['quality']}: {best['size_kb']:.1f} KB", use_container_width=True)

            a, b, c, d, e = st.columns(5)
            a.metric("ML recommendation", f"Q{st.session_state.ml_quality}")
            b.metric("Final quality", f"Q{best['quality']}")
            c.metric("Size reduction", f"{best['reduction_percent']:.1f}%")
            d.metric("Similarity", f"{best['similarity']:.3f}")
            original_time = transmission_seconds(len(original_bytes), network_mbps)
            e.metric("Estimated time saved", f"{original_time-best['transmission_seconds']:.3f} s")

            # Clean dataframe formatting for visual clarity
            formatted_list = []
            for c_item in st.session_state.candidates:
                row_dict = {
                    "Quality": f"Q{c_item['quality']}",
                    "Scale": f"{int(c_item.get('scale', 1.0)*100)}%",
                    "Size (KB)": round(c_item["size_kb"], 1),
                    "Reduction": f"{c_item['reduction_percent']:.1f}%",
                    "Similarity": round(c_item["similarity"], 3),
                    "PSNR (dB)": round(c_item["psnr_db"], 1),
                    "Time (s)": round(c_item["transmission_seconds"], 3),
                    "Quality OK": "✅" if c_item["quality_ok"] else "❌",
                    "Size OK": "✅" if c_item["attachment_ok"] else "❌",
                    "Acceptable": "✅" if c_item["acceptable"] else "❌",
                }
                formatted_list.append(row_dict)
            table_df = pd.DataFrame(formatted_list)
            st.dataframe(table_df, use_container_width=True, hide_index=True)
            st.download_button("Download Optimized Image", best["image_bytes"], "optimized_image.jpg", "image/jpeg", use_container_width=True)

            st.divider()
            st.subheader("AI Agent Email Delivery")

            if not sender_email_val or not sender_app_pass_val:
                st.warning("⚠️ Sender Gmail or App Password is not configured. Please enter your Sender Gmail and App Password in the sidebar or set Streamlit Cloud Secrets.")

            recipient = st.text_input("Recipient email")
            subject = st.text_input("Subject", value="Optimized Image")
            message = st.text_area("Message", value="Please find the optimized image attached.")

            if st.button("Send Optimized Image", type="primary", use_container_width=True):
                with st.status("AI Agent is processing the delivery task...", expanded=True) as status:
                    st.write("Validating recipient and attachment")
                    st.write("Preparing the optimized image attachment")
                    st.write(f"Sending through Gmail account ({sender_email_val or 'unconfigured'})")
                    result = deliver_optimized_image(
                        recipient=recipient,
                        subject=subject,
                        message=message,
                        attachment_bytes=best["image_bytes"],
                        attachment_name="optimized_image.jpg",
                        original_kb=len(original_bytes)/1024,
                        compressed_kb=best["size_kb"],
                        selected_quality=best["quality"],
                        similarity=best["similarity"],
                        max_attempts=2,
                        sender=sender_email_val,
                        app_password=sender_app_pass_val,
                    )
                    if result.get("success"):
                        status.update(label="Email accepted by Gmail SMTP server", state="complete")
                        st.success(result.get("result_message"))
                    else:
                        status.update(label="Delivery failed; download fallback remains available", state="error")
                        st.error(result.get("result_message"))
                        st.info(f"Attempts made: {result.get('attempts', 0)}")

with st.expander("Machine Learning model information"):
    if METRICS_PATH.exists():
        st.json(json.loads(METRICS_PATH.read_text()))
    st.warning("The starter model uses synthetic demonstration data. Replace it with measured real-image records for stronger research evaluation.")


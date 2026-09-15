# Agentic AI Image Compression and Intelligent Email Delivery

## Run

1. Create and activate a virtual environment.
2. Install requirements.
3. Copy `.env.example` to `.env` and add Gmail credentials.
4. Train the starter model.
5. Start Streamlit.

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
python train_model.py
python -m streamlit run app.py
```

## Security

- Never commit `.env`.
- Use a separate project Gmail account where possible.
- Use a Google App Password, not the normal Gmail password.
- SMTP success means the server accepted the message; it does not guarantee inbox placement.

## AI Agent

The AI Agent is implemented in `delivery_workflow.py` using LangGraph. The workflow validates the delivery task, calls the Gmail email tool, observes the result, retries once if required, and logs the final outcome.

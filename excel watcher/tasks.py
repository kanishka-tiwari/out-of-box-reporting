import os
import json
import requests
from celery import Celery
from app.database import SessionLocal
from app.models import Transaction

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6339/0")
celery_app = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)

# External Cloud Inference configurations for Render production
LLM_API_KEY = os.getenv("LLM_API_KEY", "your_api_key_here")
LLM_URL = "https://api.groq.com/openai/v1/chat/completions" # Or OpenAI endpoint

@celery_app.task
def analyze_transaction_async(transaction_id: str):
    db = SessionLocal()
    txn = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if not txn:
        db.close()
        return

    prompt = f"""
    Analyze this expense transaction for corporate compliance, policy breaches or financial fraud:
    - Vendor: {txn.vendor}
    - Amount: ${txn.amount}
    - Business Justification: "{txn.justification}"
    
    Respond strictly in JSON format with keys "risk_score" (integer 0-100) and "flags" (brief description string).
    """
    
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }

    try:
        res = requests.post(LLM_URL, json=payload, headers=headers, timeout=10)
        res_data = res.json()
        raw_content = res_data['choices'][0]['message']['content']
        parsed = json.loads(raw_content)
        
        txn.risk_score = parsed.get("risk_score", 10)
        txn.ai_flags = parsed.get("flags", "Passed Verification")
    except Exception as e:
        txn.risk_score = 0
        txn.ai_flags = f"AI processing temporarily offline: {str(e)}"
    
    db.commit()
    db.close()
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, SessionLocal
from app.models import ExcelSource, Transaction
from app.excel_watcher import check_and_sync_excel

# Initialize database schemes seamlessly inside modern engines
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Real-Time AI Enterprise Financial Audit Portal")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/v1/source/register")
def register_excel_source(file_url: str, background_tasks: BackgroundTasks):
    db = SessionLocal()
    existing = db.query(ExcelSource).filter(ExcelSource.file_url == file_url).first()
    if existing:
        db.close()
        raise HTTPException(status_code=400, detail="Excel tracking registry string already verified.")
    
    new_source = ExcelSource(file_url=file_url)
    db.add(new_source)
    db.commit()
    
    # Process initial sync instantly
    background_tasks.add_task(check_and_sync_excel, new_source.id)
    db.close()
    return {"status": "success", "message": "Excel link tracking registered successfully."}

@app.post("/api/v1/source/poll")
def poll_all_sources(background_tasks: BackgroundTasks):
    """
    Trigger this path via any external cron job utility (like cron-job.org) 
    every minute to check for updates.
    """
    db = SessionLocal()
    sources = db.query(ExcelSource).all()
    for source in sources:
        background_tasks.add_task(check_and_sync_excel, source.id)
    db.close()
    return {"status": "success", "message": "Polled changes check pipeline queued."}

@app.get("/reporting/dataset")
def get_dashboard_dataset():
    db = SessionLocal()
    transactions = db.query(Transaction).order_by(Transaction.id.desc()).all()
    db.close()
    return [{
        "id": t.transaction_id,
        "employee": t.employee_id,
        "amount": t.amount,
        "vendor": t.vendor,
        "category": t.category,
        "justification": t.justification,
        "risk": t.risk_score,
        "flags": t.ai_flags
    } for t in transactions]
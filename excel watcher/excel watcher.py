import requests
import pandas as pd
from io import BytesIO
from app.database import SessionLocal
from app.models import ExcelSource, Transaction
from app.tasks import analyze_transaction_async

def check_and_sync_excel(source_id: int):
    db = SessionLocal()
    source = db.query(ExcelSource).filter(ExcelSource.id == source_id).first()
    if not source:
        db.close()
        return

    try:
        # Check HTTP headers to evaluate structural modifications prior to processing files
        headers = requests.head(source.file_url, timeout=10).headers
        current_etag = headers.get("ETag")
        current_mod = headers.get("Last-Modified")
        
        # Avoid computational waste if file properties match perfectly
        if current_etag and current_etag == source.last_etag:
            db.close()
            return
        if current_mod and current_mod == source.last_modified:
            db.close()
            return

        # Fetch contents if modified
        response = requests.get(source.file_url, timeout=10)
        df = pd.read_excel(BytesIO(response.content)) if "xls" in source.file_url else pd.read_csv(BytesIO(response.content))
        
        # Clean structural data frames
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        for _, row in df.iterrows():
            txn_id = str(row['transaction_id'])
            
            # Check for existing items to prevent redundancy
            existing = db.query(Transaction).filter(Transaction.transaction_id == txn_id).first()
            if not existing:
                new_txn = Transaction(
                    transaction_id=txn_id,
                    employee_id=str(row['employee_id']),
                    amount=float(row['amount']),
                    vendor=str(row['vendor']),
                    category=str(row['category']),
                    justification=str(row['justification'])
                )
                db.add(new_txn)
                db.commit() # Save row first
                
                # Hand over time-consuming analytics computational threads to background queues
                analyze_transaction_async.delay(txn_id)

        # Cache modifications parameters 
        source.last_etag = current_etag
        source.last_modified = current_mod
        db.commit()

    except Exception as e:
        print(f"Error syncing excel dataset tracking engine: {e}")
    finally:
        db.close()
import csv
import io
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

router = APIRouter()

class UploadResponse(BaseModel):
    filename: str
    rows_processed: int
    status: str

@router.post("/upload", response_model=UploadResponse)
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    try:
        contents = await file.read()
        decoded = contents.decode('utf-8')
        
        reader = csv.reader(io.StringIO(decoded))
        rows = list(reader)
        
        if len(rows) < 2:
            raise HTTPException(status_code=400, detail="CSV is empty or missing headers")
            
        data_rows = len(rows) - 1
        
        return UploadResponse(
            filename=file.filename,
            rows_processed=data_rows,
            status="success"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
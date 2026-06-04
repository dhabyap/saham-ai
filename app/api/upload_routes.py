"""API routes for daily Excel uploads and analysis"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
import shutil
from pathlib import Path
from datetime import datetime

from app.database.database import get_db
from app.services.daily_upload_service import DailyUploadService

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

# Ensure upload folder exists
UPLOAD_FOLDER = Path("uploads/daily_uploads")
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


@router.post("/excel")
async def upload_excel(file: UploadFile = File(...)):
    """
    Upload daily Excel file for analysis
    
    Expected columns in Excel:
    - Kode: Stock code (e.g., BBCA, BMRI)
    - Tanggal: Date
    - Open, High, Low, Close: Price data
    - Volume: Trading volume
    - SMA_20, SMA_50: Moving averages (optional)
    - RSI, MACD: Technical indicators (optional)
    """
    try:
        original_filename = Path(file.filename or "upload.xlsx").name
        if not original_filename.lower().endswith(".xlsx"):
            raise HTTPException(status_code=400, detail="Only .xlsx files are supported")
        
        # Save uploaded file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = UPLOAD_FOLDER / f"{timestamp}_{original_filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process upload
        with get_db() as db:
            upload_service = DailyUploadService(db)
            result = upload_service.process_excel_upload(str(file_path), original_filename)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest_upload():
    """Get latest upload summary"""
    try:
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("""
                SELECT * FROM daily_uploads 
                ORDER BY upload_date DESC, uploaded_at DESC LIMIT 1
            """)
            upload = cursor.fetchone()
            
            if not upload:
                return {"message": "No uploads found"}
            
            cursor.execute("""
                SELECT * FROM upload_analysis_results 
                WHERE upload_id = ? LIMIT 1
            """, (upload[0],))
            analysis = cursor.fetchone()
            
            return {
                "id": upload[0],
                "upload_date": upload[1],
                "filename": upload[2],
                "total_stocks": upload[3],
                "uploaded_at": upload[4],
                "buy_signals": analysis[3] if analysis else 0,
                "sell_signals": analysis[4] if analysis else 0,
                "hold_signals": analysis[5] if analysis else 0,
                "confidence_score": analysis[7] if analysis else 0
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list/all")
async def list_all_uploads():
    """Get list of all uploads"""
    try:
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("""
                SELECT * FROM daily_uploads 
                ORDER BY upload_date DESC, uploaded_at DESC
            """)
            uploads = cursor.fetchall()
            
            return {
                "total": len(uploads),
                "uploads": [
                    {
                        "id": u[0],
                        "upload_date": u[1],
                        "filename": u[2],
                        "total_stocks": u[3],
                        "uploaded_at": u[4]
                    }
                    for u in uploads
                ]
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/training/summary")
async def get_training_summary():
    """Get AI training data summary"""
    try:
        with get_db() as db:
            cursor = db.cursor()
            
            cursor.execute("SELECT label, COUNT(*) FROM ai_training_data GROUP BY label")
            rows = cursor.fetchall()
            
            if not rows:
                return {
                    "total_records": 0,
                    "success_rate": 0,
                    "labels_distribution": {},
                    "message": "No training data collected yet"
                }
            
            # Calculate statistics
            labels = {row[0]: row[1] for row in rows}
            total = sum(labels.values())
            correct_predictions = sum(count for label, count in labels.items() if 'PROFIT' in label)
            
            success_rate = (correct_predictions / total * 100) if total > 0 else 0
            
            # Get unique stocks trained
            cursor.execute("SELECT COUNT(DISTINCT stock_code) FROM ai_training_data")
            stocks_trained = cursor.fetchone()[0]
            
            # Get average return
            cursor.execute("SELECT AVG(actual_return) FROM ai_training_data")
            avg_return = cursor.fetchone()[0] or 0
            
            return {
                "total_records": total,
                "success_rate": round(success_rate, 2),
                "labels_distribution": labels,
                "stocks_trained": stocks_trained,
                "avg_profit_percentage": round(avg_return, 2)
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{prediction_id}/actual-result")
async def record_actual_result(
    prediction_id: int,
    actual_profit: float = Query(...),
    was_correct: bool = Query(...)
):
    """
    Record actual market result for a prediction (for AI training)
    
    This endpoint is called after market close to record whether
    the prediction was correct and what the actual profit/loss was.
    """
    try:
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("SELECT * FROM day_trade_predictions WHERE id = ?", (prediction_id,))
            prediction = cursor.fetchone()
            
            if not prediction:
                raise HTTPException(status_code=404, detail="Prediction not found")
            
            upload_service = DailyUploadService(db)
            success = upload_service.add_actual_result(prediction_id, actual_profit, was_correct)
            
            if not success:
                raise HTTPException(status_code=400, detail="Failed to record result")
            
            return {
                "success": True,
                "message": "Actual result recorded successfully",
                "stock_code": prediction[2],
                "actual_profit": actual_profit,
                "was_correct": was_correct
            }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{upload_id}")
async def get_upload_details(upload_id: int):
    """Get detailed analysis of a specific upload"""
    try:
        with get_db() as db:
            cursor = db.cursor()
            
            cursor.execute("SELECT * FROM daily_uploads WHERE id = ?", (upload_id,))
            upload = cursor.fetchone()
            
            if not upload:
                raise HTTPException(status_code=404, detail="Upload not found")
            
            cursor.execute("""
                SELECT * FROM day_trade_predictions WHERE stock_data_id IN
                (SELECT id FROM daily_stock_data WHERE upload_id = ?)
                ORDER BY stock_code
            """, (upload_id,))
            predictions = cursor.fetchall()
            
            # Parse predictions
            buy_stocks = [p for p in predictions if p[4] == 'BUY']
            sell_stocks = [p for p in predictions if p[4] == 'SELL']
            hold_stocks = [p for p in predictions if p[4] == 'HOLD']
            
            # Get analysis summary
            cursor.execute("""
                SELECT * FROM upload_analysis_results 
                WHERE upload_id = ? LIMIT 1
            """, (upload_id,))
            analysis = cursor.fetchone()
            
            def format_prediction(p, include_reasoning=True):
                data = {
                    "code": p[2],
                    "confidence": p[5],
                    "expected_profit": p[6],
                    "risk_level": p[7],
                }
                if include_reasoning:
                    data["reasoning"] = p[8]
                return data
            
            return {
                "id": upload[0],
                "upload_date": upload[1],
                "filename": upload[2],
                "total_stocks": upload[3],
                "buy_recommendations": [format_prediction(p) for p in buy_stocks],
                "sell_recommendations": [format_prediction(p) for p in sell_stocks],
                "hold_recommendations": [format_prediction(p, include_reasoning=False) for p in hold_stocks],
                "summary": {
                    "total_buy": len(buy_stocks),
                    "total_sell": len(sell_stocks),
                    "total_hold": len(hold_stocks),
                    "average_confidence": analysis[7] if analysis else 0
                }
            }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

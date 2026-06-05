"""Service for handling daily Excel uploads and analysis"""
import os
import json
import pandas as pd
from datetime import date
from pathlib import Path

from app.ai.ai_analyzer import AIAnalyzer


class DailyUploadService:
    """Handle daily Excel uploads and generate analysis"""
    
    UPLOAD_FOLDER = "uploads/daily_uploads"
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.ai_analyzer = AIAnalyzer()
        
        # Ensure upload folder exists
        Path(self.UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
    
    def process_excel_upload(self, file_path: str, upload_filename: str) -> dict:
        """
        Process Excel file upload and perform analysis
        
        Args:
            file_path: Temporary file path of uploaded Excel
            upload_filename: Original filename
            
        Returns:
            Analysis results dictionary
        """
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Validate required columns
            required_columns = ['Kode', 'Tanggal', 'Open', 'High', 'Low', 'Close', 'Volume']
            missing = [col for col in required_columns if col not in df.columns]
            if missing:
                return {"error": f"Missing columns: {', '.join(missing)}"}
            
            # Save upload record
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO daily_uploads (filename, total_stocks, file_path)
                VALUES (?, ?, ?)
            """, (upload_filename, len(df), file_path))
            upload_id = cursor.lastrowid
            self.db.commit()
            
            # Process each stock
            stock_data_list = []
            predictions = []
            
            for idx, row in df.iterrows():
                stock_data = self._save_stock_data(upload_id, row)
                stock_data_list.append(stock_data)
                
                # Generate AI prediction for day trading
                prediction = self._generate_prediction(upload_id, stock_data, row)
                predictions.append(prediction)
            
            # Create analysis summary
            analysis_result = self._create_analysis_summary(upload_id, predictions)
            
            return {
                "success": True,
                "upload_id": upload_id,
                "total_stocks": len(df),
                "buy_signals": sum(1 for p in predictions if p['signal'] == 'BUY'),
                "sell_signals": sum(1 for p in predictions if p['signal'] == 'SELL'),
                "hold_signals": sum(1 for p in predictions if p['signal'] == 'HOLD'),
                "predictions": predictions,
                "analysis_result": analysis_result
            }
        
        except Exception as e:
            return {"error": str(e)}
    
    def _save_stock_data(self, upload_id: int, row) -> dict:
        """Save individual stock data — includes Money Flow columns"""
        
        stock_date = self._parse_date(row['Tanggal'])
        stock_code = self._normalize_stock_code(row['Kode'])
        
        # Prepare additional data (columns not in standard or money flow sets)
        standard_columns = {'Kode', 'Tanggal', 'Open', 'High', 'Low', 'Close', 'Volume', 
                           'SMA_20', 'SMA_50', 'RSI', 'MACD', 'MACD_Signal',
                           'Foreign_Net_Buy', 'Foreign_Accumulation_Days',
                           'Broker_Buy', 'Broker_Sell', 'IHSG_Change', 'Sector'}
        additional = {col: str(row[col]) for col in row.index if col not in standard_columns and pd.notna(row[col])}
        
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO daily_stock_data 
            (upload_id, stock_code, date, open_price, high_price, low_price, close_price, 
             volume, sma_20, sma_50, rsi, macd, macd_signal,
             foreign_net_buy, foreign_accumulation_days, broker_buy, broker_sell,
             ihsg_change, sector, additional_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            upload_id,
            stock_code,
            str(stock_date),
            self._required_float(row, 'Open'),
            self._required_float(row, 'High'),
            self._required_float(row, 'Low'),
            self._required_float(row, 'Close'),
            self._required_int(row, 'Volume'),
            self._optional_float(row, 'SMA_20'),
            self._optional_float(row, 'SMA_50'),
            self._optional_float(row, 'RSI'),
            self._optional_float(row, 'MACD'),
            self._optional_float(row, 'MACD_Signal'),
            # Money Flow columns
            self._optional_float(row, 'Foreign_Net_Buy', 0),
            self._optional_int(row, 'Foreign_Accumulation_Days', 0),
            self._optional_float(row, 'Broker_Buy', 0),
            self._optional_float(row, 'Broker_Sell', 0),
            self._optional_float(row, 'IHSG_Change', 0),
            str(row.get('Sector', '')),
            json.dumps(additional) if additional else None
        ))
        
        stock_data_id = cursor.lastrowid
        self.db.commit()
        
        return {
            'id': stock_data_id,
            'code': stock_code,
            'date': stock_date
        }
    
    def _generate_prediction(self, upload_id: int, stock_data: dict, row) -> dict:
        """
        Generate AI prediction for day trading (buy morning, sell evening)
        """
        try:
            # Prepare features — Money Flow methodology
            features = {
                'open': self._required_float(row, 'Open'),
                'high': self._required_float(row, 'High'),
                'low': self._required_float(row, 'Low'),
                'close': self._required_float(row, 'Close'),
                'volume': self._required_int(row, 'Volume'),
                'sma_20': self._optional_float(row, 'SMA_20', 0),
                'rsi': self._optional_float(row, 'RSI', 50),
                'macd': self._optional_float(row, 'MACD', 0),
                # Money Flow columns (optional — from enriched Excel)
                'foreign_net_buy': self._optional_float(row, 'Foreign_Net_Buy', 0),
                'foreign_accumulation_days': self._optional_int(row, 'Foreign_Accumulation_Days', 0),
                'broker_buy': self._optional_float(row, 'Broker_Buy', 0),
                'broker_sell': self._optional_float(row, 'Broker_Sell', 0),
                'ihsg_change': self._optional_float(row, 'IHSG_Change', 0),
                'sector': str(row.get('Sector', '')),
                'range_pct': ((self._required_float(row, 'High') - self._required_float(row, 'Low')) / self._required_float(row, 'Open')) * 100 if self._required_float(row, 'Open') > 0 else 0,
            }
            stock_code = self._normalize_stock_code(row['Kode'])
            
            # Get AI analysis
            analysis = self.ai_analyzer.analyze_for_day_trading(
                stock_code=stock_code,
                features=features,
                context={'price': row['Close'], 'sma20': features['sma_20']}
            )
            
            # Extract signal and confidence
            signal = analysis.get('signal', 'HOLD')
            confidence = float(analysis.get('confidence', 0.5))
            
            # Save prediction to database
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO day_trade_predictions
                (stock_data_id, stock_code, prediction_date, signal, confidence, 
                 expected_profit_percentage, risk_level, reasoning, features_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                stock_data['id'],
                stock_code,
                str(stock_data['date']),
                signal,
                confidence,
                float(analysis.get('expected_profit', 0)),
                analysis.get('risk_level', 'MEDIUM'),
                analysis.get('reasoning', ''),
                json.dumps(features)
            ))
            self.db.commit()
            
            return {
                'stock_code': stock_code,
                'signal': signal,
                'confidence': round(confidence, 2),
                'expected_profit': round(float(analysis.get('expected_profit', 0)), 2),
                'risk_level': analysis.get('risk_level', 'MEDIUM'),
                'reasoning': analysis.get('reasoning', ''),
                'price': features['close'],
                'volume': features['volume'],
                'money_flow': {
                    'foreign_net_buy': features.get('foreign_net_buy', 0),
                    'accumulation_days': features.get('foreign_accumulation_days', 0),
                    'sector': features.get('sector', ''),
                    'ihsg_change': features.get('ihsg_change', 0),
                },
                'opening_drive': analysis.get('opening_drive', ''),
                'volume_confirmation': analysis.get('volume_confirmation', ''),
                'foreign_flow_note': analysis.get('foreign_flow_note', ''),
                'tick_index_note': analysis.get('tick_index_note', ''),
            }
        
        except Exception as e:
            stock_code = self._normalize_stock_code(row.get('Kode', 'UNKNOWN'))
            print(f"Error generating prediction for {stock_code}: {e}")
            return {
                'stock_code': stock_code,
                'signal': 'HOLD',
                'confidence': 0.5,
                'expected_profit': 0,
                'risk_level': 'HIGH',
                'reasoning': f'Error in analysis: {str(e)}',
                'price': self._optional_float(row, 'Close', 0),
                'volume': self._optional_int(row, 'Volume', 0)
            }
    
    def _create_analysis_summary(self, upload_id: int, predictions: list) -> dict:
        """Create analysis summary of the upload"""
        
        buy_count = sum(1 for p in predictions if p['signal'] == 'BUY')
        sell_count = sum(1 for p in predictions if p['signal'] == 'SELL')
        hold_count = sum(1 for p in predictions if p['signal'] == 'HOLD')
        
        avg_confidence = sum(p['confidence'] for p in predictions) / len(predictions) if predictions else 0
        
        results_data = [
            {
                'stock_code': p['stock_code'],
                'signal': p['signal'],
                'confidence': p['confidence'],
                'expected_profit': p['expected_profit'],
                'risk_level': p['risk_level']
            }
            for p in predictions
        ]
        
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO upload_analysis_results
            (upload_id, analysis_date, total_buy_signals, total_sell_signals, 
             total_hold_signals, confidence_score, results_data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            upload_id,
            str(date.today()),
            buy_count,
            sell_count,
            hold_count,
            round(avg_confidence, 2),
            json.dumps(results_data)
        ))
        self.db.commit()
        
        return {
            'buy_signals': buy_count,
            'sell_signals': sell_count,
            'hold_signals': hold_count,
            'average_confidence': round(avg_confidence, 2)
        }
    
    def get_latest_upload(self) -> dict:
        """Get latest upload with results"""
        cursor = self.db.cursor()
        
        cursor.execute("""
            SELECT * FROM daily_uploads 
            ORDER BY upload_date DESC, uploaded_at DESC LIMIT 1
        """)
        upload = cursor.fetchone()
        
        if not upload:
            return None
        
        cursor.execute("""
            SELECT * FROM upload_analysis_results 
            WHERE upload_id = ? LIMIT 1
        """, (upload['id'],))
        analysis = cursor.fetchone()
        
        return {
            'id': upload['id'],
            'upload_date': upload['upload_date'],
            'filename': upload['filename'],
            'total_stocks': upload['total_stocks'],
            'buy_signals': analysis['total_buy_signals'] if analysis else 0,
            'sell_signals': analysis['total_sell_signals'] if analysis else 0,
            'hold_signals': analysis['total_hold_signals'] if analysis else 0,
            'confidence_score': analysis['confidence_score'] if analysis else 0
        }
    
    def get_upload_details(self, upload_id: int) -> dict:
        """Get detailed information about an upload"""
        cursor = self.db.cursor()
        
        cursor.execute("SELECT * FROM daily_uploads WHERE id = ?", (upload_id,))
        upload = cursor.fetchone()
        
        if not upload:
            return None
        
        cursor.execute("""
            SELECT * FROM day_trade_predictions WHERE stock_data_id IN
            (SELECT id FROM daily_stock_data WHERE upload_id = ?)
        """, (upload_id,))
        predictions = cursor.fetchall()
        
        return {
            'id': upload['id'],
            'upload_date': upload['upload_date'],
            'filename': upload['filename'],
            'total_stocks': upload['total_stocks'],
            'predictions': [
                {
                    'stock_code': p['stock_code'],
                    'signal': p['trade_signal'],
                    'confidence': p['confidence'],
                    'expected_profit': p['expected_profit_percentage'],
                    'risk_level': p['risk_level'],
                    'reasoning': p['reasoning']
                }
                for p in predictions
            ]
        }
    
    def add_actual_result(self, prediction_id: int, actual_profit: float, was_correct: bool) -> bool:
        """
        Record actual market result for a prediction (used for training)
        """
        try:
            cursor = self.db.cursor()
            
            cursor.execute("SELECT * FROM day_trade_predictions WHERE id = ?", (prediction_id,))
            prediction = cursor.fetchone()
            
            if not prediction:
                return False
            
            # Update prediction with actual result
            cursor.execute("""
                UPDATE day_trade_predictions
                SET actual_profit = ?, was_correct = ?
                WHERE id = ?
            """, (actual_profit, 1 if was_correct else 0, prediction_id))
            
            # Add to training data
            label = self._determine_training_label(prediction['trade_signal'], was_correct, actual_profit)
            
            features = json.loads(prediction['features_used']) if prediction['features_used'] else {}
            
            cursor.execute("""
                INSERT INTO ai_training_data
                (prediction_id, stock_code, training_date, features, label, 
                 actual_return, provider_used, is_validated)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                prediction_id,
                prediction['stock_code'],
                prediction['prediction_date'],
                json.dumps(features),
            label,
            actual_profit,
            self.ai_analyzer.current_provider or 'rule_based'
            ))
            
            self.db.commit()
            return True
        
        except Exception as e:
            print(f"Error adding actual result: {e}")
            return False
    
    def _determine_training_label(self, signal: str, was_correct: bool, profit: float) -> str:
        """Determine training label based on signal and outcome"""
        if signal == 'BUY':
            return 'BUY_PROFIT' if was_correct and profit > 0 else 'BUY_LOSS'
        elif signal == 'SELL':
            return 'SELL_PROFIT' if was_correct and profit > 0 else 'SELL_LOSS'
        else:
            return 'HOLD'
    
    def get_training_data_summary(self) -> dict:
        """Get summary of training data collected"""
        cursor = self.db.cursor()
        
        cursor.execute("SELECT COUNT(*), label FROM ai_training_data GROUP BY label")
        rows = cursor.fetchall()
        
        if not rows:
            return {
                'total_records': 0,
                'success_rate': 0,
                'labels_distribution': {}
            }
        
        labels = {row[1]: row[0] for row in rows}
        total = sum(labels.values())
        correct = sum(count for label, count in labels.items() if 'PROFIT' in label)
        success_rate = (correct / total * 100) if total > 0 else 0
        
        return {
            'total_records': total,
            'success_rate': round(success_rate, 2),
            'labels_distribution': labels
        }

    def _normalize_stock_code(self, value):
        return str(value).strip().upper()

    def _parse_date(self, value):
        parsed = pd.to_datetime(value, errors='coerce')
        if pd.isna(parsed):
            raise ValueError(f"Invalid Tanggal value: {value}")
        return parsed.date()

    def _required_float(self, row, column):
        value = row[column]
        if pd.isna(value):
            raise ValueError(f"Missing value for {column}")
        return float(value)

    def _required_int(self, row, column):
        value = row[column]
        if pd.isna(value):
            raise ValueError(f"Missing value for {column}")
        return int(value)

    def _optional_float(self, row, column, default=None):
        if column not in row or pd.isna(row[column]):
            return default
        return float(row[column])

    def _optional_int(self, row, column, default=0):
        if column not in row or pd.isna(row[column]):
            return default
        return int(row[column])

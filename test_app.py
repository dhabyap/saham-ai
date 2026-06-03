"""Quick test script for AI Stock Analyzer"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import Config
from app.database.database import init_db, get_db

# Test 1: Database
print("Test 1: Database init...")
init_db()
with get_db() as conn:
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    print(f"  Tables: {[t['name'] for t in tables]}")
print("  PASS")

# Test 2: Stock Service
print("\nTest 2: Stock service (BBCA)...")
from app.services.stock_service import get_latest_data, get_top_gainers
data = get_latest_data('BBCA', period='1mo')
if data:
    print(f"  Stock: {data['stock_code']}")
    print(f"  Price: {data['price']}")
    print(f"  RSI: {data['rsi']}")
    print(f"  Trend: {data['trend']}")
    print(f"  MACD: {data['macd_status']}")
    print(f"  Recommendation (rule): {data['trend']}")
    print("  PASS")
else:
    print("  SKIP (no internet connection)")

# Test 3: Analysis Service
print("\nTest 3: Analysis service...")
from app.services.analysis_service import AnalysisService
service = AnalysisService()
result = service.analyze_stock('BBCA', use_ai=False)
if "error" not in result:
    print(f"  Rec: {result['recommendation']} ({result['confidence']}%)")
    print(f"  Reason: {result['reason']}")
    print("  PASS")
else:
    print(f"  SKIP: {result['error']}")

# Test 4: Market Service
print("\nTest 4: Market service...")
from app.services.market_service import get_market_summary, get_market_sentiment, get_sector_performance
summary = get_market_summary()
print(f"  Advancing: {summary['advancing']}, Declining: {summary['declining']}")
print(f"  Fear & Greed: {summary['fear_greed']['index']} - {summary['fear_greed']['label']}")

sentiment = get_market_sentiment()
print(f"  Sentiment: {sentiment['sentiment']}")
print("  PASS")

# Test 5: API Routes import
print("\nTest 5: API routes...")
from app.api.routes import router
print(f"  Routes: {len(router.routes)} endpoints")
print("  PASS")

# Test 6: Chart Generator
print("\nTest 6: Chart generator...")
from app.charts.chart_generator import generate_full_analysis_chart
data_with_df = get_latest_data('BBCA', period='3mo')
if data_with_df and 'dataframe' in data_with_df:
    chart_path = generate_full_analysis_chart(
        data_with_df['dataframe'],
        data_with_df['stock_code'],
        data_with_df.get('stock_name', '')
    )
    if chart_path and os.path.exists(chart_path):
        print(f"  Chart saved: {chart_path}")
        print("  PASS")
    else:
        print("  SKIP")
else:
    print("  SKIP (no data)")

print("\n" + "=" * 40)
print("ALL TESTS COMPLETED")
print("=" * 40)

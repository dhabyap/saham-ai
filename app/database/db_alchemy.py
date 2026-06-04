"""
Multi-database support for AI Stock Analyzer
Uses SQLAlchemy to support SQLite, MySQL, PostgreSQL
"""
import os
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker, Session
from app.config import Config

engine = create_engine(Config.DATABASE_URL, echo=Config.DEBUG)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """Get SQLAlchemy session"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    """Initialize database with schema"""
    from sqlalchemy import Table, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
    from sqlalchemy.sql import func

    metadata = MetaData()

    users = Table('users', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('telegram_id', Integer, unique=True),
        Column('username', String(255)),
        Column('is_active', Boolean, default=True),
        Column('created_at', DateTime, server_default=func.now()),
    )

    watchlist = Table('watchlist', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('user_id', Integer, ForeignKey('users.id')),
        Column('stock_code', String(50), nullable=False),
        Column('stock_name', String(255)),
        Column('added_at', DateTime, server_default=func.now()),
    )

    analysis_history = Table('analysis_history', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('stock_code', String(50), nullable=False),
        Column('stock_name', String(255)),
        Column('recommendation', String(10)),
        Column('confidence', Float),
        Column('trend', String(50)),
        Column('rsi', Float),
        Column('macd', String(50)),
        Column('price', Float),
        Column('reason', Text),
        Column('full_analysis', Text),
        Column('created_at', DateTime, server_default=func.now()),
    )

    ai_predictions = Table('ai_predictions', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('stock_code', String(50), nullable=False),
        Column('stock_name', String(255)),
        Column('prediction', String(10), nullable=False),
        Column('confidence', Float),
        Column('price_at_prediction', Float),
        Column('price_target', Float),
        Column('strategy', String(50), default='swing'),
        Column('indicators_used', Text),
        Column('ai_provider', String(50)),
        Column('actual_result', String(10)),
        Column('price_after', Float),
        Column('days_to_eval', Integer, default=7),
        Column('evaluated', Boolean, default=False),
        Column('accuracy', Float),
        Column('profit_pct', Float),
        Column('created_at', DateTime, server_default=func.now()),
        Column('evaluated_at', DateTime),
    )

    # Create all tables
    metadata.create_all(engine)

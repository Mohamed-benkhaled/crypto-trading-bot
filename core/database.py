from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
from core.config import settings

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

class User(Base):
    """User model for authentication and portfolio management"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    portfolios = relationship("Portfolio", back_populates="user")
    trades = relationship("Trade", back_populates="user")
    strategies = relationship("Strategy", back_populates="user")

class Portfolio(Base):
    """Portfolio model for tracking user assets"""
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False)  # e.g., BTC, ETH
    quantity = Column(Float, nullable=False, default=0.0)
    average_price = Column(Float, nullable=False, default=0.0)
    current_price = Column(Float, nullable=False, default=0.0)
    total_value = Column(Float, nullable=False, default=0.0)
    pnl = Column(Float, nullable=False, default=0.0)
    pnl_percentage = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="portfolios")

class Trade(Base):
    """Trade model for tracking all trading activities"""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)  # BUY, SELL
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)
    fee = Column(Float, nullable=False, default=0.0)
    timestamp = Column(DateTime, default=func.now())
    exchange = Column(String(50), nullable=False, default="binance")
    order_id = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False, default="completed")
    
    # Relationships
    user = relationship("User", back_populates="trades")
    strategy = relationship("Strategy", back_populates="trades")

class Strategy(Base):
    """Strategy model for trading strategies configuration"""
    __tablename__ = "strategies"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    strategy_type = Column(String(50), nullable=False)  # rsi, macd, bollinger, etc.
    symbol = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True)
    parameters = Column(Text, nullable=True)  # JSON string of strategy parameters
    risk_level = Column(String(20), nullable=False, default="medium")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="strategies")
    trades = relationship("Trade", back_populates="strategy")

class MarketData(Base):
    """Market data model for storing historical price data"""
    __tablename__ = "market_data"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    timeframe = Column(String(10), nullable=False, default="1h")

class BotSession(Base):
    """Bot session model for tracking active trading sessions"""
    __tablename__ = "bot_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    status = Column(String(20), nullable=False, default="running")  # running, stopped, paused
    started_at = Column(DateTime, default=func.now())
    stopped_at = Column(DateTime, nullable=True)
    total_trades = Column(Integer, default=0)
    total_pnl = Column(Float, default=0.0)
    current_balance = Column(Float, default=0.0)

class RiskMetrics(Base):
    """Risk metrics model for tracking portfolio risk"""
    __tablename__ = "risk_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=func.now())
    portfolio_value = Column(Float, nullable=False)
    total_pnl = Column(Float, nullable=False)
    daily_pnl = Column(Float, nullable=False)
    max_drawdown = Column(Float, nullable=False)
    sharpe_ratio = Column(Float, nullable=True)
    volatility = Column(Float, nullable=True)
    correlation_matrix = Column(Text, nullable=True)  # JSON string

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

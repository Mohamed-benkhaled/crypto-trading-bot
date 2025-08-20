import os
from pydantic_settings import BaseSettings
from typing import List, Dict, Any

class Settings(BaseSettings):
    model_config = {"extra": "allow"}
    # Database
    DATABASE_URL: str = "sqlite:///./crypto_bot.db"
    
    # JWT Settings
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Trading Settings
    DEFAULT_TRADING_PAIRS: List[str] = ["BTC/USDT", "ETH/USDT", "ADA/USDT", "DOT/USDT"]
    DEFAULT_TIMEFRAME: str = "1h"
    MAX_POSITION_SIZE: float = 0.1  # 10% of portfolio
    STOP_LOSS_PERCENTAGE: float = 0.02  # 2%
    TAKE_PROFIT_PERCENTAGE: float = 0.06  # 6%
    MAX_DRAWDOWN: float = 0.15  # 15%
    
    # Strategy Parameters
    RSI_PERIOD: int = 14
    RSI_OVERSOLD: int = 30
    RSI_OVERBOUGHT: int = 70
    
    MACD_FAST: int = 12
    MACD_SLOW: int = 26
    MACD_SIGNAL: int = 9
    
    BOLLINGER_PERIOD: int = 20
    BOLLINGER_STD: float = 2.0
    
    MA_FAST: int = 10
    MA_SLOW: int = 50
    
    # Exchange Settings
    EXCHANGE_NAME: str = "binance"
    EXCHANGE_TESTNET: bool = True
    
    # API Rate Limits
    MAX_REQUESTS_PER_MINUTE: int = 60
    MAX_REQUESTS_PER_HOUR: int = 1000
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "crypto_bot.log"
    
    # Web Interface
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    


# Trading Strategy Configurations
TRADING_STRATEGIES = {
    "rsi": {
        "name": "RSI Strategy",
        "description": "Buy oversold, sell overbought based on RSI indicator",
        "parameters": {
            "period": 14,
            "oversold": 30,
            "overbought": 70
        },
        "risk_level": "medium"
    },
    "macd": {
        "name": "MACD Strategy",
        "description": "Golden cross and death cross signals with volume confirmation",
        "parameters": {
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9
        },
        "risk_level": "medium"
    },
    "bollinger": {
        "name": "Bollinger Bands Strategy",
        "description": "Price touches bands for entry/exit signals",
        "parameters": {
            "period": 20,
            "std_dev": 2.0
        },
        "risk_level": "low"
    },
    "ma_crossover": {
        "name": "Moving Average Crossover",
        "description": "Short MA crosses above/below long MA",
        "parameters": {
            "fast_period": 10,
            "slow_period": 50
        },
        "risk_level": "low"
    },
    "grid_trading": {
        "name": "Grid Trading Strategy",
        "description": "Automated buy/sell orders at price intervals",
        "parameters": {
            "grid_levels": 10,
            "grid_spacing": 0.02
        },
        "risk_level": "high"
    }
}

# Risk Management Rules
RISK_RULES = {
    "max_position_size": 0.1,  # 10% of portfolio per position
    "max_portfolio_risk": 0.02,  # 2% max risk per trade
    "max_daily_loss": 0.05,  # 5% max daily loss
    "max_drawdown": 0.15,  # 15% max drawdown
    "correlation_limit": 0.7,  # Max correlation between positions
    "volatility_adjustment": True,  # Adjust position size based on volatility
}

# Exchange Configuration
EXCHANGE_CONFIG = {
    "binance": {
        "name": "Binance",
        "testnet": True,
        "sandbox": True,
        "rate_limit": 1200,
        "supported_pairs": ["BTC/USDT", "ETH/USDT", "ADA/USDT", "DOT/USDT", "LINK/USDT"]
    },
    "coinbase": {
        "name": "Coinbase Pro",
        "testnet": False,
        "sandbox": False,
        "rate_limit": 100,
        "supported_pairs": ["BTC/USD", "ETH/USD", "LTC/USD"]
    }
}

settings = Settings()

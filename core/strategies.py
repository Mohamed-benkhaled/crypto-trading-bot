import pandas as pd
import numpy as np
import ta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

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

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

@dataclass
class TradingSignal:
    signal_type: SignalType
    confidence: float  # 0.0 to 1.0
    price: float
    timestamp: pd.Timestamp
    strategy_name: str
    parameters: Dict
    additional_info: Dict = None

class BaseStrategy:
    """Base class for all trading strategies"""
    
    def __init__(self, name: str, parameters: Dict):
        self.name = name
        self.parameters = parameters
        self.min_data_points = 100
        
    def validate_data(self, data: pd.DataFrame) -> bool:
        """Validate that we have enough data for the strategy"""
        if len(data) < self.min_data_points:
            logger.warning(f"Insufficient data for {self.name}: {len(data)} < {self.min_data_points}")
            return False
        return True
    
    def calculate_signal(self, data: pd.DataFrame) -> TradingSignal:
        """Calculate trading signal - to be implemented by subclasses"""
        raise NotImplementedError
    
    def get_position_size(self, portfolio_value: float, risk_per_trade: float) -> float:
        """Calculate position size based on risk management rules"""
        return portfolio_value * risk_per_trade

class RSIStrategy(BaseStrategy):
    """RSI (Relative Strength Index) Trading Strategy"""
    
    def __init__(self, parameters: Dict):
        super().__init__("RSI Strategy", parameters)
        self.period = parameters.get("period", 14)
        self.oversold = parameters.get("oversold", 30)
        self.overbought = parameters.get("overbought", 70)
        self.min_data_points = self.period + 10
        
    def calculate_signal(self, data: pd.DataFrame) -> TradingSignal:
        if not self.validate_data(data):
            return TradingSignal(SignalType.HOLD, 0.0, 0.0, pd.Timestamp.now(), self.name, self.parameters)
        
        # Calculate RSI
        rsi = ta.momentum.RSIIndicator(data['close'], window=self.period).rsi()
        current_rsi = rsi.iloc[-1]
        current_price = data['close'].iloc[-1]
        current_time = data.index[-1]
        
        # Generate signals
        if current_rsi < self.oversold:
            # Oversold condition - potential buy signal
            confidence = min(1.0, (self.oversold - current_rsi) / self.oversold)
            return TradingSignal(
                SignalType.BUY,
                confidence,
                current_price,
                current_time,
                self.name,
                self.parameters,
                {"rsi_value": current_rsi, "oversold_threshold": self.oversold}
            )
        elif current_rsi > self.overbought:
            # Overbought condition - potential sell signal
            confidence = min(1.0, (current_rsi - self.overbought) / (100 - self.overbought))
            return TradingSignal(
                SignalType.SELL,
                confidence,
                current_price,
                current_time,
                self.name,
                self.parameters,
                {"rsi_value": current_rsi, "overbought_threshold": self.overbought}
            )
        else:
            return TradingSignal(SignalType.HOLD, 0.0, current_price, current_time, self.name, self.parameters)

class MACDStrategy(BaseStrategy):
    """MACD (Moving Average Convergence Divergence) Trading Strategy"""
    
    def __init__(self, parameters: Dict):
        super().__init__("MACD Strategy", parameters)
        self.fast_period = parameters.get("fast_period", 12)
        self.slow_period = parameters.get("slow_period", 26)
        self.signal_period = parameters.get("signal_period", 9)
        self.min_data_points = self.slow_period + self.signal_period + 10
        
    def calculate_signal(self, data: pd.DataFrame) -> TradingSignal:
        if not self.validate_data(data):
            return TradingSignal(SignalType.HOLD, 0.0, 0.0, pd.Timestamp.now(), self.name, self.parameters)
        
        # Calculate MACD
        macd_indicator = ta.trend.MACD(
            data['close'], 
            window_fast=self.fast_period, 
            window_slow=self.slow_period, 
            window_sign=self.signal_period
        )
        
        macd_line = macd_indicator.macd()
        signal_line = macd_indicator.macd_signal()
        histogram = macd_indicator.macd_diff()
        
        current_price = data['close'].iloc[-1]
        current_time = data.index[-1]
        
        # Get current and previous values
        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        current_histogram = histogram.iloc[-1]
        
        prev_macd = macd_line.iloc[-2]
        prev_signal = signal_line.iloc[-2]
        prev_histogram = histogram.iloc[-2]
        
        # Generate signals
        if current_macd > current_signal and prev_macd <= prev_signal:
            # Golden cross - MACD crosses above signal line
            confidence = min(1.0, abs(current_histogram) / abs(current_macd) if current_macd != 0 else 0.5)
            return TradingSignal(
                SignalType.BUY,
                confidence,
                current_price,
                current_time,
                self.name,
                self.parameters,
                {
                    "macd_value": current_macd,
                    "signal_value": current_signal,
                    "histogram": current_histogram,
                    "signal_type": "golden_cross"
                }
            )
        elif current_macd < current_signal and prev_macd >= prev_signal:
            # Death cross - MACD crosses below signal line
            confidence = min(1.0, abs(current_histogram) / abs(current_macd) if current_macd != 0 else 0.5)
            return TradingSignal(
                SignalType.SELL,
                confidence,
                current_price,
                current_time,
                self.name,
                self.parameters,
                {
                    "macd_value": current_macd,
                    "signal_value": current_signal,
                    "histogram": current_histogram,
                    "signal_type": "death_cross"
                }
            )
        else:
            return TradingSignal(SignalType.HOLD, 0.0, current_price, current_time, self.name, self.parameters)

class BollingerBandsStrategy(BaseStrategy):
    """Bollinger Bands Trading Strategy"""
    
    def __init__(self, parameters: Dict):
        super().__init__("Bollinger Bands Strategy", parameters)
        self.period = parameters.get("period", 20)
        self.std_dev = parameters.get("std_dev", 2.0)
        self.min_data_points = self.period + 10
        
    def calculate_signal(self, data: pd.DataFrame) -> TradingSignal:
        if not self.validate_data(data):
            return TradingSignal(SignalType.HOLD, 0.0, 0.0, pd.Timestamp.now(), self.name, self.parameters)
        
        # Calculate Bollinger Bands
        bb_indicator = ta.volatility.BollingerBands(
            data['close'], 
            window=self.period, 
            window_dev=self.std_dev
        )
        
        upper_band = bb_indicator.bollinger_hband()
        middle_band = bb_indicator.bollinger_mavg()
        lower_band = bb_indicator.bollinger_lband()
        
        current_price = data['close'].iloc[-1]
        current_time = data.index[-1]
        
        # Calculate bandwidth and %B
        bandwidth = (upper_band - lower_band) / middle_band
        percent_b = (current_price - lower_band) / (upper_band - lower_band)
        
        # Generate signals
        if current_price <= lower_band.iloc[-1]:
            # Price touches or goes below lower band - potential buy signal
            confidence = min(1.0, (lower_band.iloc[-1] - current_price) / current_price + 0.5)
            return TradingSignal(
                SignalType.BUY,
                confidence,
                current_price,
                current_time,
                self.name,
                self.parameters,
                {
                    "upper_band": upper_band.iloc[-1],
                    "middle_band": middle_band.iloc[-1],
                    "lower_band": lower_band.iloc[-1],
                    "percent_b": percent_b.iloc[-1],
                    "bandwidth": bandwidth.iloc[-1]
                }
            )
        elif current_price >= upper_band.iloc[-1]:
            # Price touches or goes above upper band - potential sell signal
            confidence = min(1.0, (current_price - upper_band.iloc[-1]) / current_price + 0.5)
            return TradingSignal(
                SignalType.SELL,
                confidence,
                current_price,
                current_time,
                self.name,
                self.parameters,
                {
                    "upper_band": upper_band.iloc[-1],
                    "middle_band": middle_band.iloc[-1],
                    "lower_band": lower_band.iloc[-1],
                    "percent_b": percent_b.iloc[-1],
                    "bandwidth": bandwidth.iloc[-1]
                }
            )
        else:
            return TradingSignal(SignalType.HOLD, 0.0, current_price, current_time, self.name, self.parameters)

class MovingAverageCrossoverStrategy(BaseStrategy):
    """Moving Average Crossover Trading Strategy"""
    
    def __init__(self, parameters: Dict):
        super().__init__("Moving Average Crossover Strategy", parameters)
        self.fast_period = parameters.get("fast_period", 10)
        self.slow_period = parameters.get("slow_period", 50)
        self.min_data_points = self.slow_period + 10
        
    def calculate_signal(self, data: pd.DataFrame) -> TradingSignal:
        if not self.validate_data(data):
            return TradingSignal(SignalType.HOLD, 0.0, 0.0, pd.Timestamp.now(), self.name, self.parameters)
        
        # Calculate moving averages
        fast_ma = ta.trend.SMAIndicator(data['close'], window=self.fast_period).sma_indicator()
        slow_ma = ta.trend.SMAIndicator(data['close'], window=self.slow_period).sma_indicator()
        
        current_price = data['close'].iloc[-1]
        current_time = data.index[-1]
        
        # Get current and previous values
        current_fast_ma = fast_ma.iloc[-1]
        current_slow_ma = slow_ma.iloc[-1]
        prev_fast_ma = fast_ma.iloc[-2]
        prev_slow_ma = slow_ma.iloc[-2]
        
        # Generate signals
        if current_fast_ma > current_slow_ma and prev_fast_ma <= prev_slow_ma:
            # Golden cross - fast MA crosses above slow MA
            confidence = min(1.0, (current_fast_ma - current_slow_ma) / current_slow_ma * 10)
            return TradingSignal(
                SignalType.BUY,
                confidence,
                current_price,
                current_time,
                self.name,
                self.parameters,
                {
                    "fast_ma": current_fast_ma,
                    "slow_ma": current_slow_ma,
                    "crossover_type": "golden_cross"
                }
            )
        elif current_fast_ma < current_slow_ma and prev_fast_ma >= prev_slow_ma:
            # Death cross - fast MA crosses below slow MA
            confidence = min(1.0, (current_slow_ma - current_fast_ma) / current_slow_ma * 10)
            return TradingSignal(
                SignalType.SELL,
                confidence,
                current_price,
                current_time,
                self.name,
                self.parameters,
                {
                    "fast_ma": current_fast_ma,
                    "slow_ma": current_slow_ma,
                    "crossover_type": "death_cross"
                }
            )
        else:
            return TradingSignal(SignalType.HOLD, 0.0, current_price, current_time, self.name, self.parameters)

class GridTradingStrategy(BaseStrategy):
    """Grid Trading Strategy"""
    
    def __init__(self, parameters: Dict):
        super().__init__("Grid Trading Strategy", parameters)
        self.grid_levels = parameters.get("grid_levels", 10)
        self.grid_spacing = parameters.get("grid_spacing", 0.02)  # 2% spacing
        self.min_data_points = 50
        
    def calculate_signal(self, data: pd.DataFrame) -> TradingSignal:
        if not self.validate_data(data):
            return TradingSignal(SignalType.HOLD, 0.0, 0.0, pd.Timestamp.now(), self.name, self.parameters)
        
        current_price = data['close'].iloc[-1]
        current_time = data.index[-1]
        
        # Calculate grid levels
        price_range = current_price * self.grid_spacing * self.grid_levels
        grid_prices = np.linspace(
            current_price - price_range/2,
            current_price + price_range/2,
            self.grid_levels
        )
        
        # Find nearest grid levels
        buy_levels = grid_prices[grid_prices < current_price]
        sell_levels = grid_prices[grid_prices > current_price]
        
        if len(buy_levels) > 0:
            nearest_buy = buy_levels[-1]
            if current_price - nearest_buy < current_price * self.grid_spacing * 0.5:
                confidence = 0.7
                return TradingSignal(
                    SignalType.BUY,
                    confidence,
                    current_price,
                    current_time,
                    self.name,
                    self.parameters,
                    {
                        "grid_level": nearest_buy,
                        "grid_spacing": self.grid_spacing,
                        "total_levels": self.grid_levels
                    }
                )
        
        if len(sell_levels) > 0:
            nearest_sell = sell_levels[0]
            if nearest_sell - current_price < current_price * self.grid_spacing * 0.5:
                confidence = 0.7
                return TradingSignal(
                    SignalType.SELL,
                    confidence,
                    current_price,
                    current_time,
                    self.name,
                    self.parameters,
                    {
                        "grid_level": nearest_sell,
                        "grid_spacing": self.grid_spacing,
                        "total_levels": self.grid_levels
                    }
                )
        
        return TradingSignal(SignalType.HOLD, 0.0, current_price, current_time, self.name, self.parameters)

# Strategy factory
class StrategyFactory:
    """Factory class for creating trading strategies"""
    
    @staticmethod
    def create_strategy(strategy_type: str, parameters: Dict) -> BaseStrategy:
        """Create a strategy instance based on type"""
        strategies = {
            "rsi": RSIStrategy,
            "macd": MACDStrategy,
            "bollinger": BollingerBandsStrategy,
            "ma_crossover": MovingAverageCrossoverStrategy,
            "grid_trading": GridTradingStrategy
        }
        
        if strategy_type not in strategies:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
        
        return strategies[strategy_type](parameters)
    
    @staticmethod
    def get_available_strategies() -> List[str]:
        """Get list of available strategy types"""
        return ["rsi", "macd", "bollinger", "ma_crossover", "grid_trading"]

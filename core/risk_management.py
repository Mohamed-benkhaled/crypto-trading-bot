import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from enum import Enum

from core.strategies import TradingSignal, SignalType
from core.database import SessionLocal, Trade, Portfolio, RiskMetrics
from core.config import RISK_RULES

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

@dataclass
class RiskAssessment:
    risk_score: float  # 0.0 to 1.0
    risk_level: RiskLevel
    max_position_size: float
    stop_loss_price: float
    take_profit_price: float
    risk_factors: List[str]
    recommendations: List[str]

class RiskManager:
    """Risk management system for enforcing trading limits and position sizing"""
    
    def __init__(self):
        self.risk_rules = RISK_RULES
        self.max_position_size = self.risk_rules["max_position_size"]
        self.max_portfolio_risk = self.risk_rules["max_portfolio_risk"]
        self.max_daily_loss = self.risk_rules["max_daily_loss"]
        self.max_drawdown = self.risk_rules["max_drawdown"]
        self.correlation_limit = self.risk_rules["correlation_limit"]
        self.volatility_adjustment = self.risk_rules["volatility_adjustment"]
    
    async def check_trade_allowed(self, user_id: int, signal: TradingSignal, symbol: str) -> bool:
        """Check if a trade is allowed based on risk rules"""
        try:
            # Get current portfolio state
            portfolio = await self._get_user_portfolio(user_id)
            current_risk = await self._calculate_portfolio_risk(user_id, portfolio)
            
            # Check basic risk limits
            if not self._check_basic_risk_limits(current_risk):
                logger.warning(f"Trade blocked: Basic risk limits exceeded for user {user_id}")
                return False
            
            # Check position concentration
            if not self._check_position_concentration(portfolio, symbol, signal):
                logger.warning(f"Trade blocked: Position concentration limit exceeded for {symbol}")
                return False
            
            # Check correlation limits
            if not await self._check_correlation_limits(user_id, symbol, signal):
                logger.warning(f"Trade blocked: Correlation limit exceeded for {symbol}")
                return False
            
            # Check volatility limits
            if not await self._check_volatility_limits(symbol, signal):
                logger.warning(f"Trade blocked: Volatility limit exceeded for {symbol}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking trade allowance: {e}")
            return False  # Block trade on error for safety
    
    async def adjust_position_size(self, user_id: int, symbol: str, base_size: float) -> float:
        """Adjust position size based on risk factors"""
        try:
            # Get risk assessment
            risk_assessment = await self._assess_risk(user_id, symbol, base_size)
            
            # Apply risk adjustments
            adjusted_size = base_size
            
            # Adjust for risk level
            if risk_assessment.risk_level == RiskLevel.HIGH:
                adjusted_size *= 0.5  # Reduce size by 50%
            elif risk_assessment.risk_level == RiskLevel.MEDIUM:
                adjusted_size *= 0.75  # Reduce size by 25%
            
            # Adjust for volatility
            if self.volatility_adjustment:
                volatility_factor = await self._calculate_volatility_factor(symbol)
                adjusted_size *= volatility_factor
            
            # Ensure within maximum limits
            max_allowed = risk_assessment.max_position_size
            adjusted_size = min(adjusted_size, max_allowed)
            
            # Round to reasonable precision
            adjusted_size = round(adjusted_size, 6)
            
            logger.info(f"Position size adjusted: {base_size} -> {adjusted_size} for {symbol}")
            return adjusted_size
            
        except Exception as e:
            logger.error(f"Error adjusting position size: {e}")
            return base_size * 0.5  # Conservative fallback
    
    async def assess_risk(self, user_id: int, symbol: str, position_size: float) -> RiskAssessment:
        """Comprehensive risk assessment for a potential trade"""
        try:
            risk_factors = []
            recommendations = []
            
            # Get portfolio data
            portfolio = await self._get_user_portfolio(user_id)
            portfolio_value = sum([p.total_value for p in portfolio])
            
            # Calculate position concentration risk
            position_concentration = position_size / portfolio_value if portfolio_value > 0 else 0
            if position_concentration > self.max_position_size:
                risk_factors.append("High position concentration")
                recommendations.append("Reduce position size")
            
            # Calculate market risk
            market_risk = await self._calculate_market_risk(symbol)
            if market_risk > 0.7:
                risk_factors.append("High market volatility")
                recommendations.append("Consider waiting for lower volatility")
            
            # Calculate correlation risk
            correlation_risk = await self._calculate_correlation_risk(user_id, symbol)
            if correlation_risk > self.correlation_limit:
                risk_factors.append("High portfolio correlation")
                recommendations.append("Diversify portfolio")
            
            # Calculate overall risk score
            risk_score = self._calculate_overall_risk_score(
                position_concentration, market_risk, correlation_risk
            )
            
            # Determine risk level
            if risk_score < 0.3:
                risk_level = RiskLevel.LOW
            elif risk_score < 0.6:
                risk_level = RiskLevel.MEDIUM
            else:
                risk_level = RiskLevel.HIGH
            
            # Calculate risk-adjusted position size
            max_position_size = portfolio_value * self.max_position_size * (1 - risk_score)
            
            # Calculate stop-loss and take-profit levels
            current_price = await self._get_current_price(symbol)
            stop_loss_price = current_price * (1 - self._get_stop_loss_percentage(risk_level))
            take_profit_price = current_price * (1 + self._get_take_profit_percentage(risk_level))
            
            return RiskAssessment(
                risk_score=risk_score,
                risk_level=risk_level,
                max_position_size=max_position_size,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                risk_factors=risk_factors,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Error assessing risk: {e}")
            # Return conservative assessment on error
            return RiskAssessment(
                risk_score=0.8,
                risk_level=RiskLevel.HIGH,
                max_position_size=0,
                stop_loss_price=0,
                take_profit_price=0,
                risk_factors=["Error in risk assessment"],
                recommendations=["Contact support"]
            )
    
    def _check_basic_risk_limits(self, current_risk: Dict) -> bool:
        """Check basic risk limits"""
        try:
            # Check daily loss limit
            if current_risk.get("daily_pnl", 0) < -(current_risk.get("portfolio_value", 0) * self.max_daily_loss):
                return False
            
            # Check drawdown limit
            if current_risk.get("drawdown", 0) > self.max_drawdown:
                return False
            
            # Check portfolio risk
            if current_risk.get("portfolio_risk", 0) > self.max_portfolio_risk:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking basic risk limits: {e}")
            return False
    
    def _check_position_concentration(self, portfolio: List[Portfolio], symbol: str, signal: TradingSignal) -> bool:
        """Check position concentration limits"""
        try:
            # Calculate total portfolio value
            total_value = sum([p.total_value for p in portfolio])
            
            # Calculate current position value for this symbol
            current_position = next((p for p in portfolio if p.symbol == symbol), None)
            current_value = current_position.total_value if current_position else 0
            
            # Calculate new position value
            if signal.signal_type == SignalType.BUY:
                new_value = current_value + (signal.price * self._estimate_position_size(signal))
            else:
                new_value = current_value - (signal.price * self._estimate_position_size(signal))
            
            # Check concentration limit
            concentration = new_value / total_value if total_value > 0 else 0
            return concentration <= self.max_position_size
            
        except Exception as e:
            logger.error(f"Error checking position concentration: {e}")
            return False
    
    async def _check_correlation_limits(self, user_id: int, symbol: str, signal: TradingSignal) -> bool:
        """Check correlation limits with existing positions"""
        try:
            # Get existing positions
            portfolio = await self._get_user_portfolio(user_id)
            if len(portfolio) < 2:
                return True  # No correlation risk with single position
            
            # Calculate correlation matrix
            correlation_matrix = await self._calculate_correlation_matrix(user_id)
            
            # Check if new position would exceed correlation limits
            for position in portfolio:
                if position.symbol != symbol:
                    correlation = correlation_matrix.get(f"{symbol}_{position.symbol}", 0)
                    if correlation > self.correlation_limit:
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking correlation limits: {e}")
            return True  # Allow trade on error
    
    async def _check_volatility_limits(self, symbol: str, signal: TradingSignal) -> bool:
        """Check volatility limits"""
        try:
            # Calculate current volatility
            volatility = await self._calculate_volatility(symbol)
            
            # Define volatility thresholds
            max_volatility = 0.5  # 50% annualized volatility
            
            if volatility > max_volatility:
                logger.warning(f"High volatility detected for {symbol}: {volatility:.2%}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking volatility limits: {e}")
            return True  # Allow trade on error
    
    async def _calculate_portfolio_risk(self, user_id: int, portfolio: List[Portfolio]) -> Dict:
        """Calculate overall portfolio risk metrics"""
        try:
            total_value = sum([p.total_value for p in portfolio])
            total_pnl = sum([p.pnl for p in portfolio])
            
            # Calculate daily P&L
            daily_pnl = await self._calculate_daily_pnl(user_id)
            
            # Calculate drawdown
            drawdown = await self._calculate_drawdown(user_id)
            
            # Calculate portfolio risk (VaR-like measure)
            portfolio_risk = await self._calculate_value_at_risk(user_id, portfolio)
            
            return {
                "portfolio_value": total_value,
                "total_pnl": total_pnl,
                "daily_pnl": daily_pnl,
                "drawdown": drawdown,
                "portfolio_risk": portfolio_risk
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio risk: {e}")
            return {
                "portfolio_value": 0,
                "total_pnl": 0,
                "daily_pnl": 0,
                "drawdown": 0,
                "portfolio_risk": 0
            }
    
    async def _calculate_correlation_matrix(self, user_id: int) -> Dict[str, float]:
        """Calculate correlation matrix for user's positions"""
        try:
            # This would typically use historical price data
            # For now, return a simple correlation matrix
            return {}
            
        except Exception as e:
            logger.error(f"Error calculating correlation matrix: {e}")
            return {}
    
    async def _calculate_volatility(self, symbol: str) -> float:
        """Calculate current volatility for a symbol"""
        try:
            # This would typically use historical price data
            # For now, return a default volatility
            return 0.3  # 30% annualized volatility
            
        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return 0.3
    
    async def _calculate_value_at_risk(self, user_id: int, portfolio: List[Portfolio], confidence: float = 0.95) -> float:
        """Calculate Value at Risk for the portfolio"""
        try:
            # This is a simplified VaR calculation
            # In production, you'd use historical simulation or Monte Carlo methods
            
            total_value = sum([p.total_value for p in portfolio])
            if total_value == 0:
                return 0
            
            # Assume normal distribution with 20% annual volatility
            daily_volatility = 0.20 / np.sqrt(252)  # Convert annual to daily
            var_factor = 1.645  # 95% confidence level
            
            var = total_value * daily_volatility * var_factor
            return var
            
        except Exception as e:
            logger.error(f"Error calculating VaR: {e}")
            return 0
    
    def _calculate_overall_risk_score(self, position_concentration: float, market_risk: float, correlation_risk: float) -> float:
        """Calculate overall risk score from individual risk factors"""
        try:
            # Weighted average of risk factors
            weights = [0.4, 0.3, 0.3]  # Position, market, correlation
            
            risk_score = (
                weights[0] * position_concentration +
                weights[1] * market_risk +
                weights[2] * correlation_risk
            )
            
            return min(1.0, max(0.0, risk_score))
            
        except Exception as e:
            logger.error(f"Error calculating overall risk score: {e}")
            return 0.5  # Medium risk on error
    
    def _get_stop_loss_percentage(self, risk_level: RiskLevel) -> float:
        """Get stop-loss percentage based on risk level"""
        stop_loss_percentages = {
            RiskLevel.LOW: 0.02,    # 2%
            RiskLevel.MEDIUM: 0.03,  # 3%
            RiskLevel.HIGH: 0.05     # 5%
        }
        return stop_loss_percentages.get(risk_level, 0.03)
    
    def _get_take_profit_percentage(self, risk_level: RiskLevel) -> float:
        """Get take-profit percentage based on risk level"""
        take_profit_percentages = {
            RiskLevel.LOW: 0.06,    # 6%
            RiskLevel.MEDIUM: 0.08,  # 8%
            RiskLevel.HIGH: 0.12     # 12%
        }
        return take_profit_percentages.get(risk_level, 0.08)
    
    def _estimate_position_size(self, signal: TradingSignal) -> float:
        """Estimate position size for risk calculations"""
        # This is a simplified estimation
        # In practice, you'd use the actual calculated position size
        return 0.01  # 1% of portfolio as default
    
    async def _get_user_portfolio(self, user_id: int) -> List[Portfolio]:
        """Get user's current portfolio"""
        try:
            db = SessionLocal()
            portfolio = db.query(Portfolio).filter(Portfolio.user_id == user_id).all()
            db.close()
            return portfolio
        except Exception as e:
            logger.error(f"Error getting user portfolio: {e}")
            return []
    
    async def _calculate_daily_pnl(self, user_id: int) -> float:
        """Calculate daily P&L for user"""
        try:
            db = SessionLocal()
            today = datetime.now().date()
            trades = db.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.timestamp >= today
            ).all()
            
            daily_pnl = sum([
                (trade.total_value if trade.side == "SELL" else -trade.total_value)
                for trade in trades
            ])
            
            db.close()
            return daily_pnl
        except Exception as e:
            logger.error(f"Error calculating daily P&L: {e}")
            return 0
    
    async def _calculate_drawdown(self, user_id: int) -> float:
        """Calculate current drawdown for user"""
        try:
            # This would typically use historical portfolio values
            # For now, return a default value
            return 0.05  # 5% drawdown
            
        except Exception as e:
            logger.error(f"Error calculating drawdown: {e}")
            return 0
    
    async def _get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol"""
        try:
            # This would typically come from exchange API
            # For now, return a default price
            return 100.0  # Default price
            
        except Exception as e:
            logger.error(f"Error getting current price: {e}")
            return 100.0
    
    async def _calculate_volatility_factor(self, symbol: str) -> float:
        """Calculate volatility adjustment factor for position sizing"""
        try:
            volatility = await self._calculate_volatility(symbol)
            
            # Higher volatility = smaller position size
            if volatility > 0.4:  # High volatility
                return 0.5
            elif volatility > 0.2:  # Medium volatility
                return 0.75
            else:  # Low volatility
                return 1.0
                
        except Exception as e:
            logger.error(f"Error calculating volatility factor: {e}")
            return 0.75  # Conservative default

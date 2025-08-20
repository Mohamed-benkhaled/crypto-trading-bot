import asyncio
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from enum import Enum

from core.strategies import StrategyFactory, TradingSignal, SignalType
from core.risk_management import RiskManager
from core.exchange_interface import ExchangeInterface
from core.database import SessionLocal, Trade, Portfolio, BotSession

logger = logging.getLogger(__name__)

class BotStatus(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    ERROR = "error"

@dataclass
class TradingDecision:
    signal: TradingSignal
    action: str  # "BUY", "SELL", "HOLD"
    quantity: float
    price: float
    confidence: float
    risk_score: float
    timestamp: datetime

class TradingEngine:
    """Main trading engine that coordinates strategies and executes trades"""
    
    def __init__(self, user_id: int, exchange_name: str = "binance"):
        self.user_id = user_id
        self.exchange_name = exchange_name
        self.status = BotStatus.STOPPED
        self.active_strategies: Dict[int, Dict] = {}
        self.risk_manager = RiskManager()
        self.exchange = ExchangeInterface(exchange_name)
        self.session_id = None
        
        # Performance tracking
        self.total_trades = 0
        self.total_pnl = 0.0
        self.start_balance = 0.0
        self.current_balance = 0.0
        
        # Trading parameters
        self.min_confidence = 0.6
        self.max_risk_per_trade = 0.02  # 2% per trade
        self.max_daily_loss = 0.05  # 5% daily loss limit
        
    async def start(self) -> bool:
        """Start the trading bot"""
        try:
            logger.info(f"Starting trading bot for user {self.user_id}")
            
            # Initialize exchange connection
            if not await self.exchange.connect():
                logger.error("Failed to connect to exchange")
                return False
            
            # Get initial balance
            self.start_balance = await self.exchange.get_balance()
            self.current_balance = self.start_balance
            
            # Create bot session
            self.session_id = await self._create_bot_session()
            
            # Start trading loop
            self.status = BotStatus.RUNNING
            asyncio.create_task(self._trading_loop())
            
            logger.info("Trading bot started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting trading bot: {e}")
            self.status = BotStatus.ERROR
            return False
    
    async def stop(self) -> bool:
        """Stop the trading bot"""
        try:
            logger.info(f"Stopping trading bot for user {self.user_id}")
            self.status = BotStatus.STOPPED
            
            # Close exchange connection
            await self.exchange.disconnect()
            
            # Update bot session
            if self.session_id:
                await self._update_bot_session()
            
            logger.info("Trading bot stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping trading bot: {e}")
            return False
    
    async def pause(self) -> bool:
        """Pause the trading bot"""
        try:
            logger.info(f"Pausing trading bot for user {self.user_id}")
            self.status = BotStatus.PAUSED
            await self._update_bot_session()
            return True
        except Exception as e:
            logger.error(f"Error pausing trading bot: {e}")
            return False
    
    async def resume(self) -> bool:
        """Resume the trading bot"""
        try:
            logger.info(f"Resuming trading bot for user {self.user_id}")
            self.status = BotStatus.RUNNING
            await self._update_bot_session()
            return True
        except Exception as e:
            logger.error(f"Error resuming trading bot: {e}")
            return False
    
    def add_strategy(self, strategy_id: int, strategy_type: str, parameters: Dict, symbol: str) -> bool:
        """Add a trading strategy to the bot"""
        try:
            strategy = StrategyFactory.create_strategy(strategy_type, parameters)
            self.active_strategies[strategy_id] = {
                "strategy": strategy,
                "type": strategy_type,
                "parameters": parameters,
                "symbol": symbol,
                "last_signal": None,
                "active_positions": []
            }
            logger.info(f"Added strategy {strategy_type} for {symbol}")
            return True
        except Exception as e:
            logger.error(f"Error adding strategy: {e}")
            return False
    
    def remove_strategy(self, strategy_id: int) -> bool:
        """Remove a trading strategy from the bot"""
        try:
            if str(strategy_id) in self.active_strategies:
                del self.active_strategies[str(strategy_id)]
                logger.info(f"Removed strategy {strategy_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing strategy: {e}")
            return False
    
    async def _trading_loop(self):
        """Main trading loop that runs continuously"""
        while self.status == BotStatus.RUNNING:
            try:
                # Check if we should pause trading
                if await self._should_pause_trading():
                    logger.info("Trading paused due to risk limits")
                    await asyncio.sleep(60)  # Wait 1 minute
                    continue
                
                # Process each active strategy
                for strategy_id, strategy_info in self.active_strategies.items():
                    await self._process_strategy(strategy_id, strategy_info)
                
                # Update portfolio and risk metrics
                await self._update_portfolio()
                await self._update_risk_metrics()
                
                # Wait before next iteration
                await asyncio.sleep(30)  # 30 second intervals
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                self.status = BotStatus.ERROR
                await asyncio.sleep(60)
    
    async def _process_strategy(self, strategy_id: int, strategy_info: Dict):
        """Process a single trading strategy"""
        try:
            symbol = strategy_info["symbol"]
            strategy = strategy_info["strategy"]
            
            # Get market data
            market_data = await self.exchange.get_market_data(symbol, timeframe="1h", limit=200)
            if market_data is None or len(market_data) < 100:
                logger.warning(f"Insufficient market data for {symbol}")
                return
            
            # Calculate trading signal
            signal = strategy.calculate_signal(market_data)
            strategy_info["last_signal"] = signal
            
            # Process signal if it's actionable
            if signal.signal_type != SignalType.HOLD and signal.confidence >= self.min_confidence:
                await self._execute_signal(signal, strategy_id, strategy_info)
            
        except Exception as e:
            logger.error(f"Error processing strategy {strategy_id}: {e}")
    
    async def _execute_signal(self, signal: TradingSignal, strategy_id: int, strategy_info: Dict):
        """Execute a trading signal"""
        try:
            symbol = strategy_info["symbol"]
            
            # Check risk limits
            if not await self.risk_manager.check_trade_allowed(self.user_id, signal, symbol):
                logger.info(f"Trade blocked by risk manager for {symbol}")
                return
            
            # Calculate position size
            position_size = await self._calculate_position_size(signal, strategy_info)
            
            # Execute trade
            if signal.signal_type == SignalType.BUY:
                success = await self._execute_buy(symbol, position_size, signal.price, strategy_id)
            elif signal.signal_type == SignalType.SELL:
                success = await self._execute_sell(symbol, position_size, signal.price, strategy_id)
            
            if success:
                logger.info(f"Successfully executed {signal.signal_type.value} for {symbol}")
                self.total_trades += 1
                
                # Update strategy info
                if signal.signal_type == SignalType.BUY:
                    strategy_info["active_positions"].append({
                        "symbol": symbol,
                        "quantity": position_size,
                        "entry_price": signal.price,
                        "timestamp": signal.timestamp
                    })
            
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
    
    async def _execute_buy(self, symbol: str, quantity: float, price: float, strategy_id: int) -> bool:
        """Execute a buy order"""
        try:
            # Place order on exchange
            order = await self.exchange.place_order(
                symbol=symbol,
                side="BUY",
                quantity=quantity,
                price=price,
                order_type="LIMIT"
            )
            
            if order and order.get("status") == "FILLED":
                # Record trade in database
                await self._record_trade(symbol, "BUY", quantity, price, strategy_id)
                
                # Update portfolio
                await self._update_portfolio_position(symbol, quantity, price, "BUY")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error executing buy order: {e}")
            return False
    
    async def _execute_sell(self, symbol: str, quantity: float, price: float, strategy_id: int) -> bool:
        """Execute a sell order"""
        try:
            # Place order on exchange
            order = await self.exchange.place_order(
                symbol=symbol,
                side="SELL",
                quantity=quantity,
                price=price,
                order_type="LIMIT"
            )
            
            if order and order.get("status") == "FILLED":
                # Record trade in database
                await self._record_trade(symbol, "SELL", quantity, price, strategy_id)
                
                # Update portfolio
                await self._update_portfolio_position(symbol, quantity, price, "SELL")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error executing sell order: {e}")
            return False
    
    async def _calculate_position_size(self, signal: TradingSignal, strategy_info: Dict) -> float:
        """Calculate position size based on risk management rules"""
        try:
            # Get current portfolio value
            portfolio_value = await self.exchange.get_balance()
            
            # Calculate base position size
            base_size = strategy_info["strategy"].get_position_size(
                portfolio_value, 
                self.max_risk_per_trade
            )
            
            # Adjust for signal confidence
            adjusted_size = base_size * signal.confidence
            
            # Apply risk manager adjustments
            final_size = await self.risk_manager.adjust_position_size(
                self.user_id, 
                signal.symbol, 
                adjusted_size
            )
            
            return final_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    async def _should_pause_trading(self) -> bool:
        """Check if trading should be paused due to risk limits"""
        try:
            # Check daily loss limit
            daily_pnl = await self._get_daily_pnl()
            if daily_pnl < -(self.start_balance * self.max_daily_loss):
                logger.warning("Daily loss limit reached")
                return True
            
            # Check drawdown limit
            current_drawdown = (self.start_balance - self.current_balance) / self.start_balance
            if current_drawdown > 0.15:  # 15% max drawdown
                logger.warning("Maximum drawdown limit reached")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking pause conditions: {e}")
            return True  # Pause on error for safety
    
    async def _record_trade(self, symbol: str, side: str, quantity: float, price: float, strategy_id: int):
        """Record a trade in the database"""
        try:
            db = SessionLocal()
            trade = Trade(
                user_id=self.user_id,
                strategy_id=strategy_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                total_value=quantity * price,
                fee=0.0,  # Calculate actual fee from exchange
                exchange=self.exchange_name,
                status="completed"
            )
            db.add(trade)
            db.commit()
            db.close()
            
        except Exception as e:
            logger.error(f"Error recording trade: {e}")
    
    async def _update_portfolio_position(self, symbol: str, quantity: float, price: float, side: str):
        """Update portfolio position after trade"""
        try:
            db = SessionLocal()
            
            # Get existing position
            portfolio = db.query(Portfolio).filter(
                Portfolio.user_id == self.user_id,
                Portfolio.symbol == symbol
            ).first()
            
            if side == "BUY":
                if portfolio:
                    # Update existing position
                    total_quantity = portfolio.quantity + quantity
                    total_cost = (portfolio.quantity * portfolio.average_price) + (quantity * price)
                    portfolio.average_price = total_cost / total_quantity
                    portfolio.quantity = total_quantity
                else:
                    # Create new position
                    portfolio = Portfolio(
                        user_id=self.user_id,
                        symbol=symbol,
                        quantity=quantity,
                        average_price=price,
                        current_price=price,
                        total_value=quantity * price,
                        pnl=0.0,
                        pnl_percentage=0.0
                    )
                    db.add(portfolio)
            else:  # SELL
                if portfolio:
                    portfolio.quantity -= quantity
                    if portfolio.quantity <= 0:
                        db.delete(portfolio)
            
            db.commit()
            db.close()
            
        except Exception as e:
            logger.error(f"Error updating portfolio: {e}")
    
    async def _update_portfolio(self):
        """Update portfolio with current prices"""
        try:
            db = SessionLocal()
            portfolios = db.query(Portfolio).filter(Portfolio.user_id == self.user_id).all()
            
            for portfolio in portfolios:
                # Get current price from exchange
                current_price = await self.exchange.get_current_price(portfolio.symbol)
                if current_price:
                    portfolio.current_price = current_price
                    portfolio.total_value = portfolio.quantity * current_price
                    portfolio.pnl = portfolio.total_value - (portfolio.quantity * portfolio.average_price)
                    portfolio.pnl_percentage = (portfolio.pnl / (portfolio.quantity * portfolio.average_price)) * 100
            
            db.commit()
            db.close()
            
        except Exception as e:
            logger.error(f"Error updating portfolio: {e}")
    
    async def _update_risk_metrics(self):
        """Update risk metrics"""
        try:
            # This would calculate and store various risk metrics
            # like Sharpe ratio, volatility, correlation matrix, etc.
            pass
        except Exception as e:
            logger.error(f"Error updating risk metrics: {e}")
    
    async def _get_daily_pnl(self) -> float:
        """Get daily P&L"""
        try:
            db = SessionLocal()
            today = datetime.now().date()
            trades = db.query(Trade).filter(
                Trade.user_id == self.user_id,
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
            return 0.0
    
    async def _create_bot_session(self) -> int:
        """Create a new bot session in the database"""
        try:
            db = SessionLocal()
            session = BotSession(
                user_id=self.user_id,
                strategy_id=1,  # Default strategy
                status=self.status.value,
                started_at=datetime.now()
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            db.close()
            return session.id
        except Exception as e:
            logger.error(f"Error creating bot session: {e}")
            return None
    
    async def _update_bot_session(self):
        """Update bot session status"""
        try:
            if self.session_id:
                db = SessionLocal()
                session = db.query(BotSession).filter(BotSession.id == self.session_id).first()
                if session:
                    session.status = self.status.value
                    session.stopped_at = datetime.now() if self.status == BotStatus.STOPPED else None
                    session.total_trades = self.total_trades
                    session.total_pnl = self.total_pnl
                    session.current_balance = self.current_balance
                    db.commit()
                db.close()
        except Exception as e:
            logger.error(f"Error updating bot session: {e}")
    
    def get_status(self) -> Dict:
        """Get current bot status"""
        return {
            "status": self.status.value,
            "total_trades": self.total_trades,
            "total_pnl": self.total_pnl,
            "current_balance": self.current_balance,
            "start_balance": self.start_balance,
            "active_strategies": len(self.active_strategies),
            "session_id": self.session_id
        }

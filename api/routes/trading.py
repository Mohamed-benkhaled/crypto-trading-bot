from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import datetime
import json

from core.database import get_db, User, Strategy, BotSession
from core.trading_engine import TradingEngine
from core.strategies import StrategyFactory, TRADING_STRATEGIES
from core.config import settings
from api.routes.auth import get_current_active_user

router = APIRouter()

# Store active trading engines for each user
active_engines: Dict[int, TradingEngine] = {}

@router.get("/strategies")
async def get_available_strategies():
    """Get list of available trading strategies"""
    return {
        "strategies": TRADING_STRATEGIES,
        "total": len(TRADING_STRATEGIES)
    }

@router.get("/strategies/user")
async def get_user_strategies(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's configured trading strategies"""
    try:
        strategies = db.query(Strategy).filter(Strategy.user_id == current_user.id).all()
        
        strategy_list = []
        for strategy in strategies:
            strategy_data = {
                "id": strategy.id,
                "name": strategy.name,
                "strategy_type": strategy.strategy_type,
                "symbol": strategy.symbol,
                "is_active": strategy.is_active,
                "risk_level": strategy.risk_level,
                "parameters": json.loads(strategy.parameters) if strategy.parameters else {},
                "created_at": strategy.created_at,
                "updated_at": strategy.updated_at
            }
            strategy_list.append(strategy_data)
        
        return {
            "strategies": strategy_list,
            "total": len(strategy_list)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving strategies: {str(e)}"
        )

@router.post("/strategies/create")
async def create_strategy(
    name: str,
    strategy_type: str,
    symbol: str,
    parameters: Dict,
    risk_level: str = "medium",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new trading strategy"""
    try:
        # Validate strategy type
        if strategy_type not in TRADING_STRATEGIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid strategy type. Available types: {list(TRADING_STRATEGIES.keys())}"
            )
        
        # Validate symbol format
        if not symbol or "/" not in symbol:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Symbol must be in format: BASE/QUOTE (e.g., BTC/USDT)"
            )
        
        # Validate risk level
        valid_risk_levels = ["low", "medium", "high"]
        if risk_level not in valid_risk_levels:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid risk level. Must be one of: {valid_risk_levels}"
            )
        
        # Create strategy
        strategy = Strategy(
            user_id=current_user.id,
            name=name,
            strategy_type=strategy_type,
            symbol=symbol,
            parameters=json.dumps(parameters),
            risk_level=risk_level,
            is_active=True
        )
        
        db.add(strategy)
        db.commit()
        db.refresh(strategy)
        
        return {
            "message": "Strategy created successfully",
            "strategy_id": strategy.id,
            "name": strategy.name,
            "strategy_type": strategy.strategy_type,
            "symbol": strategy.symbol
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating strategy: {str(e)}"
        )

@router.put("/strategies/{strategy_id}")
async def update_strategy(
    strategy_id: int,
    name: Optional[str] = None,
    parameters: Optional[Dict] = None,
    risk_level: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update an existing trading strategy"""
    try:
        # Get strategy
        strategy = db.query(Strategy).filter(
            Strategy.id == strategy_id,
            Strategy.user_id == current_user.id
        ).first()
        
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )
        
        # Update fields
        if name is not None:
            strategy.name = name
        if parameters is not None:
            strategy.parameters = json.dumps(parameters)
        if risk_level is not None:
            if risk_level not in ["low", "medium", "high"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid risk level"
                )
            strategy.risk_level = risk_level
        if is_active is not None:
            strategy.is_active = is_active
        
        strategy.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "message": "Strategy updated successfully",
            "strategy_id": strategy.id,
            "name": strategy.name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating strategy: {str(e)}"
        )

@router.delete("/strategies/{strategy_id}")
async def delete_strategy(
    strategy_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a trading strategy"""
    try:
        # Get strategy
        strategy = db.query(Strategy).filter(
            Strategy.id == strategy_id,
            Strategy.user_id == current_user.id
        ).first()
        
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )
        
        # Check if strategy is active in trading engine
        if current_user.id in active_engines:
            engine = active_engines[current_user.id]
            if str(strategy_id) in engine.active_strategies:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete active strategy. Stop the bot first."
                )
        
        # Delete strategy
        db.delete(strategy)
        db.commit()
        
        return {"message": "Strategy deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting strategy: {str(e)}"
        )

@router.post("/start")
async def start_trading_bot(
    strategy_ids: List[int],
    exchange_name: str = "binance",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Start the trading bot with specified strategies"""
    try:
        # Check if bot is already running
        if current_user.id in active_engines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trading bot is already running"
            )
        
        # Validate strategies
        strategies = db.query(Strategy).filter(
            Strategy.id.in_(strategy_ids),
            Strategy.user_id == current_user.id,
            Strategy.is_active == True
        ).all()
        
        if len(strategies) != len(strategy_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Some strategies not found or inactive"
            )
        
        # Create trading engine
        engine = TradingEngine(current_user.id, exchange_name)
        
        # Add strategies to engine
        for strategy in strategies:
            parameters = json.loads(strategy.parameters) if strategy.parameters else {}
            success = engine.add_strategy(
                strategy.id,
                strategy.strategy_type,
                parameters,
                strategy.symbol
            )
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to add strategy: {strategy.name}"
                )
        
        # Start the engine
        success = await engine.start()
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to start trading bot"
            )
        
        # Store active engine
        active_engines[current_user.id] = engine
        
        return {
            "message": "Trading bot started successfully",
            "strategies_count": len(strategies),
            "exchange": exchange_name,
            "status": "running"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting trading bot: {str(e)}"
        )

@router.post("/stop")
async def stop_trading_bot(
    current_user: User = Depends(get_current_active_user)
):
    """Stop the trading bot"""
    try:
        if current_user.id not in active_engines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trading bot is not running"
            )
        
        engine = active_engines[current_user.id]
        success = await engine.stop()
        
        if success:
            # Remove from active engines
            del active_engines[current_user.id]
            
            return {
                "message": "Trading bot stopped successfully",
                "status": "stopped"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to stop trading bot"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error stopping trading bot: {str(e)}"
        )

@router.post("/pause")
async def pause_trading_bot(
    current_user: User = Depends(get_current_active_user)
):
    """Pause the trading bot"""
    try:
        if current_user.id not in active_engines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trading bot is not running"
            )
        
        engine = active_engines[current_user.id]
        success = await engine.pause()
        
        if success:
            return {
                "message": "Trading bot paused successfully",
                "status": "paused"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to pause trading bot"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error pausing trading bot: {str(e)}"
        )

@router.post("/resume")
async def resume_trading_bot(
    current_user: User = Depends(get_current_active_user)
):
    """Resume the trading bot"""
    try:
        if current_user.id not in active_engines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trading bot is not running"
            )
        
        engine = active_engines[current_user.id]
        success = await engine.resume()
        
        if success:
            return {
                "message": "Trading bot resumed successfully",
                "status": "running"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to resume trading bot"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resuming trading bot: {str(e)}"
        )

@router.get("/status")
async def get_bot_status(
    current_user: User = Depends(get_current_active_user)
):
    """Get current trading bot status"""
    try:
        if current_user.id not in active_engines:
            return {
                "status": "stopped",
                "message": "Trading bot is not running"
            }
        
        engine = active_engines[current_user.id]
        status_info = engine.get_status()
        
        return {
            "status": status_info["status"],
            "total_trades": status_info["total_trades"],
            "total_pnl": status_info["total_pnl"],
            "current_balance": status_info["current_balance"],
            "start_balance": status_info["start_balance"],
            "active_strategies": status_info["active_strategies"],
            "session_id": status_info["session_id"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting bot status: {str(e)}"
        )

@router.get("/signals")
async def get_trading_signals(
    current_user: User = Depends(get_current_active_user)
):
    """Get current trading signals from active strategies"""
    try:
        if current_user.id not in active_engines:
            return {
                "signals": [],
                "message": "Trading bot is not running"
            }
        
        engine = active_engines[current_user.id]
        signals = []
        
        for strategy_id, strategy_info in engine.active_strategies.items():
            if strategy_info.get("last_signal"):
                signal = strategy_info["last_signal"]
                signals.append({
                    "strategy_id": strategy_id,
                    "strategy_name": strategy_info["strategy"].name,
                    "symbol": strategy_info["symbol"],
                    "signal_type": signal.signal_type.value,
                    "confidence": signal.confidence,
                    "price": signal.price,
                    "timestamp": signal.timestamp.isoformat(),
                    "additional_info": signal.additional_info
                })
        
        return {
            "signals": signals,
            "total": len(signals)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting trading signals: {str(e)}"
        )

@router.get("/backtest")
async def backtest_strategy(
    strategy_type: str,
    symbol: str,
    start_date: str,
    end_date: str,
    parameters: Dict,
    initial_balance: float = 10000.0,
    current_user: User = Depends(get_current_active_user)
):
    """Backtest a trading strategy"""
    try:
        # Validate strategy type
        if strategy_type not in TRADING_STRATEGIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid strategy type. Available types: {list(TRADING_STRATEGIES.keys())}"
            )
        
        # This would implement backtesting logic
        # For now, return a placeholder response
        return {
            "message": "Backtesting feature coming soon",
            "strategy_type": strategy_type,
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "initial_balance": initial_balance
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error running backtest: {str(e)}"
        )

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import json

from core.database import get_db, User, Trade, Portfolio, BotSession
from api.routes.auth import get_current_active_user

router = APIRouter()

@router.get("/trades")
async def get_trading_history(
    symbol: Optional[str] = None,
    strategy_id: Optional[int] = None,
    side: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get trading history with filters"""
    try:
        # Build query
        query = db.query(Trade).filter(Trade.user_id == current_user.id)
        
        # Apply filters
        if symbol:
            query = query.filter(Trade.symbol == symbol)
        
        if strategy_id:
            query = query.filter(Trade.strategy_id == strategy_id)
        
        if side:
            if side.upper() not in ["BUY", "SELL"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Side must be 'BUY' or 'SELL'"
                )
            query = query.filter(Trade.side == side.upper())
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query = query.filter(Trade.timestamp >= start_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
                )
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query = query.filter(Trade.timestamp <= end_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
                )
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply pagination and ordering
        trades = query.order_by(Trade.timestamp.desc()).offset(offset).limit(limit).all()
        
        # Format response
        trade_list = []
        for trade in trades:
            trade_data = {
                "id": trade.id,
                "symbol": trade.symbol,
                "side": trade.side,
                "quantity": trade.quantity,
                "price": trade.price,
                "total_value": trade.total_value,
                "fee": trade.fee,
                "timestamp": trade.timestamp.isoformat(),
                "exchange": trade.exchange,
                "order_id": trade.order_id,
                "status": trade.status,
                "strategy": {
                    "id": trade.strategy.id,
                    "name": trade.strategy.name,
                    "type": trade.strategy.strategy_type
                } if trade.strategy else None
            }
            trade_list.append(trade_data)
        
        return {
            "trades": trade_list,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving trading history: {str(e)}"
        )

@router.get("/trades/summary")
async def get_trading_summary(
    timeframe: str = Query("30d", regex="^(1d|7d|30d|90d|1y|all)$"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get trading summary statistics"""
    try:
        # Calculate time range
        now = datetime.utcnow()
        if timeframe == "1d":
            start_date = now - timedelta(days=1)
        elif timeframe == "7d":
            start_date = now - timedelta(days=7)
        elif timeframe == "30d":
            start_date = now - timedelta(days=30)
        elif timeframe == "90d":
            start_date = now - timedelta(days=90)
        elif timeframe == "1y":
            start_date = now - timedelta(days=365)
        else:  # "all"
            start_date = None
        
        # Build query
        query = db.query(Trade).filter(Trade.user_id == current_user.id)
        if start_date:
            query = query.filter(Trade.timestamp >= start_date)
        
        trades = query.all()
        
        if not trades:
            return {
                "timeframe": timeframe,
                "summary": {
                    "total_trades": 0,
                    "total_volume": 0,
                    "total_fees": 0,
                    "win_rate": 0,
                    "avg_trade_size": 0
                },
                "by_symbol": {},
                "by_strategy": {}
            }
        
        # Calculate basic statistics
        total_trades = len(trades)
        total_volume = sum([t.total_value for t in trades])
        total_fees = sum([t.fee for t in trades])
        
        # Calculate win rate (simplified)
        buy_trades = [t for t in trades if t.side == "BUY"]
        sell_trades = [t for t in trades if t.side == "SELL"]
        
        # This is a simplified win rate calculation
        # In reality, you'd need to pair buy/sell trades
        win_rate = 0  # Placeholder
        
        avg_trade_size = total_volume / total_trades if total_trades > 0 else 0
        
        # Group by symbol
        by_symbol = {}
        for trade in trades:
            symbol = trade.symbol
            if symbol not in by_symbol:
                by_symbol[symbol] = {
                    "total_trades": 0,
                    "total_volume": 0,
                    "buy_volume": 0,
                    "sell_volume": 0,
                    "total_fees": 0
                }
            
            by_symbol[symbol]["total_trades"] += 1
            by_symbol[symbol]["total_volume"] += trade.total_value
            by_symbol[symbol]["total_fees"] += trade.fee
            
            if trade.side == "BUY":
                by_symbol[symbol]["buy_volume"] += trade.total_value
            else:
                by_symbol[symbol]["sell_volume"] += trade.total_value
        
        # Group by strategy
        by_strategy = {}
        for trade in trades:
            if trade.strategy:
                strategy_name = trade.strategy.name
                if strategy_name not in by_strategy:
                    by_strategy[strategy_name] = {
                        "total_trades": 0,
                        "total_volume": 0,
                        "total_fees": 0
                    }
                
                by_strategy[strategy_name]["total_trades"] += 1
                by_strategy[strategy_name]["total_volume"] += trade.total_value
                by_strategy[strategy_name]["total_fees"] += trade.fee
        
        return {
            "timeframe": timeframe,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": now.isoformat(),
            "summary": {
                "total_trades": total_trades,
                "total_volume": total_volume,
                "total_fees": total_fees,
                "win_rate": win_rate,
                "avg_trade_size": avg_trade_size,
                "buy_trades": len(buy_trades),
                "sell_trades": len(sell_trades)
            },
            "by_symbol": by_symbol,
            "by_strategy": by_strategy
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting trading summary: {str(e)}"
        )

@router.get("/trades/analytics")
async def get_trading_analytics(
    symbol: Optional[str] = None,
    timeframe: str = Query("30d", regex="^(1d|7d|30d|90d|1y|all)$"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get advanced trading analytics"""
    try:
        # Calculate time range
        now = datetime.utcnow()
        if timeframe == "1d":
            start_date = now - timedelta(days=1)
        elif timeframe == "7d":
            start_date = now - timedelta(days=7)
        elif timeframe == "30d":
            start_date = now - timedelta(days=30)
        elif timeframe == "90d":
            start_date = now - timedelta(days=90)
        elif timeframe == "1y":
            start_date = now - timedelta(days=365)
        else:  # "all"
            start_date = None
        
        # Build query
        query = db.query(Trade).filter(Trade.user_id == current_user.id)
        if start_date:
            query = query.filter(Trade.timestamp >= start_date)
        if symbol:
            query = query.filter(Trade.symbol == symbol)
        
        trades = query.order_by(Trade.timestamp).all()
        
        if not trades:
            return {
                "message": "No trades found for the specified criteria",
                "analytics": {}
            }
        
        # Calculate daily trading volume
        daily_volume = {}
        for trade in trades:
            date_key = trade.timestamp.date().isoformat()
            if date_key not in daily_volume:
                daily_volume[date_key] = 0
            daily_volume[date_key] += trade.total_value
        
        # Calculate hourly trading patterns
        hourly_patterns = {}
        for trade in trades:
            hour = trade.timestamp.hour
            if hour not in hourly_patterns:
                hourly_patterns[hour] = {
                    "count": 0,
                    "volume": 0
                }
            hourly_patterns[hour]["count"] += 1
            hourly_patterns[hour]["volume"] += trade.total_value
        
        # Calculate trade size distribution
        trade_sizes = [t.total_value for t in trades]
        if trade_sizes:
            avg_trade_size = sum(trade_sizes) / len(trade_sizes)
            min_trade_size = min(trade_sizes)
            max_trade_size = max(trade_sizes)
            
            # Size categories
            small_trades = len([s for s in trade_sizes if s < avg_trade_size * 0.5])
            medium_trades = len([s for s in trade_sizes if avg_trade_size * 0.5 <= s <= avg_trade_size * 1.5])
            large_trades = len([s for s in trade_sizes if s > avg_trade_size * 1.5])
        else:
            avg_trade_size = min_trade_size = max_trade_size = 0
            small_trades = medium_trades = large_trades = 0
        
        # Calculate strategy performance
        strategy_performance = {}
        for trade in trades:
            if trade.strategy:
                strategy_name = trade.strategy.name
                if strategy_name not in strategy_performance:
                    strategy_performance[strategy_name] = {
                        "trades": 0,
                        "volume": 0,
                        "fees": 0,
                        "last_used": None
                    }
                
                strategy_performance[strategy_name]["trades"] += 1
                strategy_performance[strategy_name]["volume"] += trade.total_value
                strategy_performance[strategy_name]["fees"] += trade.fee
                
                if not strategy_performance[strategy_name]["last_used"] or trade.timestamp > strategy_performance[strategy_name]["last_used"]:
                    strategy_performance[strategy_name]["last_used"] = trade.timestamp
        
        # Convert timestamps to ISO format
        for strategy in strategy_performance.values():
            if strategy["last_used"]:
                strategy["last_used"] = strategy["last_used"].isoformat()
        
        return {
            "timeframe": timeframe,
            "symbol": symbol,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": now.isoformat(),
            "analytics": {
                "daily_volume": daily_volume,
                "hourly_patterns": hourly_patterns,
                "trade_size_analysis": {
                    "average": avg_trade_size,
                    "minimum": min_trade_size,
                    "maximum": max_trade_size,
                    "distribution": {
                        "small": small_trades,
                        "medium": medium_trades,
                        "large": large_trades
                    }
                },
                "strategy_performance": strategy_performance,
                "total_trades": len(trades),
                "total_volume": sum([t.total_value for t in trades]),
                "total_fees": sum([t.fee for t in trades])
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting trading analytics: {str(e)}"
        )

@router.get("/bot-sessions")
async def get_bot_sessions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get trading bot session history"""
    try:
        sessions = db.query(BotSession).filter(
            BotSession.user_id == current_user.id
        ).order_by(BotSession.started_at.desc()).all()
        
        session_list = []
        for session in sessions:
            session_data = {
                "id": session.id,
                "status": session.status,
                "started_at": session.started_at.isoformat(),
                "stopped_at": session.stopped_at.isoformat() if session.stopped_at else None,
                "total_trades": session.total_trades,
                "total_pnl": session.total_pnl,
                "current_balance": session.current_balance,
                "duration": None
            }
            
            # Calculate session duration
            if session.stopped_at:
                duration = session.stopped_at - session.started_at
                session_data["duration"] = str(duration)
            else:
                duration = datetime.utcnow() - session.started_at
                session_data["duration"] = str(duration)
            
            session_list.append(session_data)
        
        return {
            "sessions": session_list,
            "total": len(session_list)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving bot sessions: {str(e)}"
        )

@router.get("/bot-sessions/{session_id}")
async def get_bot_session_details(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get detailed information for a specific bot session"""
    try:
        session = db.query(BotSession).filter(
            BotSession.id == session_id,
            BotSession.user_id == current_user.id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot session not found"
            )
        
        # Get trades for this session
        trades = db.query(Trade).filter(
            Trade.user_id == current_user.id,
            Trade.timestamp >= session.started_at
        )
        
        if session.stopped_at:
            trades = trades.filter(Trade.timestamp <= session.stopped_at)
        
        trades = trades.order_by(Trade.timestamp).all()
        
        # Calculate session metrics
        session_metrics = {
            "total_trades": len(trades),
            "buy_trades": len([t for t in trades if t.side == "BUY"]),
            "sell_trades": len([t for t in trades if t.side == "SELL"]),
            "total_volume": sum([t.total_value for t in trades]),
            "total_fees": sum([t.fee for t in trades]),
            "unique_symbols": len(set([t.symbol for t in trades])),
            "strategies_used": len(set([t.strategy.name for t in trades if t.strategy]))
        }
        
        # Calculate P&L over time
        pnl_timeline = []
        cumulative_pnl = 0
        
        for trade in trades:
            if trade.side == "SELL":
                cumulative_pnl += trade.total_value
            else:
                cumulative_pnl -= trade.total_value
            
            pnl_timeline.append({
                "timestamp": trade.timestamp.isoformat(),
                "cumulative_pnl": cumulative_pnl,
                "trade_type": trade.side,
                "symbol": trade.symbol,
                "value": trade.total_value
            })
        
        return {
            "session": {
                "id": session.id,
                "status": session.status,
                "started_at": session.started_at.isoformat(),
                "stopped_at": session.stopped_at.isoformat() if session.stopped_at else None,
                "total_trades": session.total_trades,
                "total_pnl": session.total_pnl,
                "current_balance": session.current_balance
            },
            "session_metrics": session_metrics,
            "pnl_timeline": pnl_timeline,
            "trades": [
                {
                    "id": trade.id,
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "quantity": trade.quantity,
                    "price": trade.price,
                    "total_value": trade.total_value,
                    "timestamp": trade.timestamp.isoformat(),
                    "strategy": trade.strategy.name if trade.strategy else None
                }
                for trade in trades
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting bot session details: {str(e)}"
        )

@router.get("/export")
async def export_trading_data(
    format: str = Query("csv", regex="^(csv|json)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Export trading data in specified format"""
    try:
        # Build query
        query = db.query(Trade).filter(Trade.user_id == current_user.id)
        
        # Apply date filters
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query = query.filter(Trade.timestamp >= start_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_date format"
                )
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query = query.filter(Trade.timestamp <= end_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_date format"
                )
        
        trades = query.order_by(Trade.timestamp).all()
        
        if format == "csv":
            # Generate CSV content
            csv_content = "ID,Symbol,Side,Quantity,Price,Total Value,Fee,Timestamp,Exchange,Order ID,Status,Strategy\n"
            for trade in trades:
                strategy_name = trade.strategy.name if trade.strategy else ""
                csv_content += f"{trade.id},{trade.symbol},{trade.side},{trade.quantity},{trade.price},{trade.total_value},{trade.fee},{trade.timestamp},{trade.exchange},{trade.order_id},{trade.status},{strategy_name}\n"
            
            return {
                "format": "csv",
                "data": csv_content,
                "filename": f"trading_history_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        
        elif format == "json":
            # Generate JSON content
            trade_data = []
            for trade in trades:
                trade_data.append({
                    "id": trade.id,
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "quantity": trade.quantity,
                    "price": trade.price,
                    "total_value": trade.total_value,
                    "fee": trade.fee,
                    "timestamp": trade.timestamp.isoformat(),
                    "exchange": trade.exchange,
                    "order_id": trade.order_id,
                    "status": trade.status,
                    "strategy": trade.strategy.name if trade.strategy else None
                })
            
            return {
                "format": "json",
                "data": trade_data,
                "filename": f"trading_history_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting trading data: {str(e)}"
        )

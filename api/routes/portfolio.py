from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import json

from core.database import get_db, User, Portfolio, Trade, RiskMetrics
from core.risk_management import RiskManager
from api.routes.auth import get_current_active_user

router = APIRouter()

@router.get("/overview")
async def get_portfolio_overview(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get portfolio overview and summary"""
    try:
        # Get portfolio positions
        portfolios = db.query(Portfolio).filter(Portfolio.user_id == current_user.id).all()
        
        # Calculate totals
        total_value = sum([p.total_value for p in portfolios])
        total_pnl = sum([p.pnl for p in portfolios])
        total_pnl_percentage = (total_pnl / (total_value - total_pnl)) * 100 if (total_value - total_pnl) > 0 else 0
        
        # Get recent trades
        recent_trades = db.query(Trade).filter(
            Trade.user_id == current_user.id
        ).order_by(Trade.timestamp.desc()).limit(10).all()
        
        # Get risk metrics
        risk_metrics = db.query(RiskMetrics).filter(
            RiskMetrics.user_id == current_user.id
        ).order_by(RiskMetrics.timestamp.desc()).first()
        
        # Calculate position distribution
        position_distribution = []
        for portfolio in portfolios:
            if total_value > 0:
                percentage = (portfolio.total_value / total_value) * 100
            else:
                percentage = 0
            
            position_distribution.append({
                "symbol": portfolio.symbol,
                "quantity": portfolio.quantity,
                "average_price": portfolio.average_price,
                "current_price": portfolio.current_price,
                "total_value": portfolio.total_value,
                "pnl": portfolio.pnl,
                "pnl_percentage": portfolio.pnl_percentage,
                "percentage_of_portfolio": percentage
            })
        
        # Sort by value (highest first)
        position_distribution.sort(key=lambda x: x["total_value"], reverse=True)
        
        return {
            "portfolio_summary": {
                "total_value": total_value,
                "total_pnl": total_pnl,
                "total_pnl_percentage": total_pnl_percentage,
                "total_positions": len(portfolios),
                "last_updated": datetime.utcnow().isoformat()
            },
            "position_distribution": position_distribution,
            "recent_trades": [
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
                for trade in recent_trades
            ],
            "risk_metrics": {
                "max_drawdown": risk_metrics.max_drawdown if risk_metrics else 0,
                "sharpe_ratio": risk_metrics.sharpe_ratio if risk_metrics else 0,
                "volatility": risk_metrics.volatility if risk_metrics else 0,
                "last_updated": risk_metrics.timestamp.isoformat() if risk_metrics else None
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting portfolio overview: {str(e)}"
        )

@router.get("/positions")
async def get_portfolio_positions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get detailed portfolio positions"""
    try:
        portfolios = db.query(Portfolio).filter(Portfolio.user_id == current_user.id).all()
        
        positions = []
        for portfolio in portfolios:
            positions.append({
                "id": portfolio.id,
                "symbol": portfolio.symbol,
                "quantity": portfolio.quantity,
                "average_price": portfolio.average_price,
                "current_price": portfolio.current_price,
                "total_value": portfolio.total_value,
                "pnl": portfolio.pnl,
                "pnl_percentage": portfolio.pnl_percentage,
                "updated_at": portfolio.updated_at.isoformat()
            })
        
        # Sort by P&L (highest first)
        positions.sort(key=lambda x: x["pnl"], reverse=True)
        
        return {
            "positions": positions,
            "total": len(positions)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting portfolio positions: {str(e)}"
        )

@router.get("/positions/{symbol}")
async def get_position_details(
    symbol: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get detailed information for a specific position"""
    try:
        portfolio = db.query(Portfolio).filter(
            Portfolio.user_id == current_user.id,
            Portfolio.symbol == symbol
        ).first()
        
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Position not found for {symbol}"
            )
        
        # Get recent trades for this symbol
        recent_trades = db.query(Trade).filter(
            Trade.user_id == current_user.id,
            Trade.symbol == symbol
        ).order_by(Trade.timestamp.desc()).limit(20).all()
        
        # Calculate position metrics
        unrealized_pnl = portfolio.pnl
        cost_basis = portfolio.quantity * portfolio.average_price
        market_value = portfolio.quantity * portfolio.current_price
        
        return {
            "position": {
                "symbol": portfolio.symbol,
                "quantity": portfolio.quantity,
                "average_price": portfolio.average_price,
                "current_price": portfolio.current_price,
                "cost_basis": cost_basis,
                "market_value": market_value,
                "unrealized_pnl": unrealized_pnl,
                "pnl_percentage": portfolio.pnl_percentage,
                "last_updated": portfolio.updated_at.isoformat()
            },
            "recent_trades": [
                {
                    "id": trade.id,
                    "side": trade.side,
                    "quantity": trade.quantity,
                    "price": trade.price,
                    "total_value": trade.total_value,
                    "timestamp": trade.timestamp.isoformat(),
                    "strategy": trade.strategy.name if trade.strategy else None
                }
                for trade in recent_trades
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting position details: {str(e)}"
        )

@router.get("/performance")
async def get_portfolio_performance(
    timeframe: str = "1d",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get portfolio performance metrics over time"""
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
        else:
            start_date = now - timedelta(days=30)  # Default to 30 days
        
        # Get trades in timeframe
        trades = db.query(Trade).filter(
            Trade.user_id == current_user.id,
            Trade.timestamp >= start_date
        ).order_by(Trade.timestamp).all()
        
        # Calculate performance metrics
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.side == "SELL" and t.total_value > 0])
        losing_trades = len([t for t in trades if t.side == "SELL" and t.total_value < 0])
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Calculate P&L over time
        cumulative_pnl = 0
        pnl_data = []
        
        for trade in trades:
            if trade.side == "SELL":
                # Calculate P&L for sell trades
                # This is simplified - in reality you'd need to track buy/sell pairs
                cumulative_pnl += trade.total_value
            else:
                # For buy trades, subtract the cost
                cumulative_pnl -= trade.total_value
            
            pnl_data.append({
                "timestamp": trade.timestamp.isoformat(),
                "cumulative_pnl": cumulative_pnl,
                "trade_type": trade.side,
                "symbol": trade.symbol
            })
        
        return {
            "timeframe": timeframe,
            "start_date": start_date.isoformat(),
            "end_date": now.isoformat(),
            "performance_metrics": {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": win_rate,
                "final_pnl": cumulative_pnl
            },
            "pnl_timeline": pnl_data
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting portfolio performance: {str(e)}"
        )

@router.get("/risk-analysis")
async def get_risk_analysis(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive risk analysis for the portfolio"""
    try:
        # Get portfolio positions
        portfolios = db.query(Portfolio).filter(Portfolio.user_id == current_user.id).all()
        
        if not portfolios:
            return {
                "message": "No positions found",
                "risk_metrics": {}
            }
        
        # Calculate basic risk metrics
        total_value = sum([p.total_value for p in portfolios])
        total_pnl = sum([p.pnl for p in portfolios])
        
        # Calculate position concentration
        concentration_risk = []
        for portfolio in portfolios:
            concentration = (portfolio.total_value / total_value) * 100 if total_value > 0 else 0
            concentration_risk.append({
                "symbol": portfolio.symbol,
                "concentration": concentration,
                "risk_level": "high" if concentration > 20 else "medium" if concentration > 10 else "low"
            })
        
        # Sort by concentration (highest first)
        concentration_risk.sort(key=lambda x: x["concentration"], reverse=True)
        
        # Calculate portfolio diversification score
        if len(portfolios) == 1:
            diversification_score = 0  # Single position = no diversification
        elif len(portfolios) <= 3:
            diversification_score = 30  # Low diversification
        elif len(portfolios) <= 7:
            diversification_score = 60  # Medium diversification
        else:
            diversification_score = 90  # High diversification
        
        # Get risk metrics from database
        risk_metrics = db.query(RiskMetrics).filter(
            RiskMetrics.user_id == current_user.id
        ).order_by(RiskMetrics.timestamp.desc()).first()
        
        # Calculate volatility (simplified)
        if len(portfolios) > 1:
            returns = [p.pnl_percentage / 100 for p in portfolios if p.pnl_percentage != 0]
            if returns:
                volatility = sum(returns) / len(returns)  # Simplified volatility calculation
            else:
                volatility = 0
        else:
            volatility = 0
        
        # Calculate Value at Risk (simplified)
        if portfolios:
            # Assume normal distribution with 20% annual volatility
            daily_volatility = 0.20 / (252 ** 0.5)  # Convert annual to daily
            var_95 = total_value * daily_volatility * 1.645  # 95% confidence level
        else:
            var_95 = 0
        
        return {
            "portfolio_risk_summary": {
                "total_value": total_value,
                "total_pnl": total_pnl,
                "number_of_positions": len(portfolios),
                "diversification_score": diversification_score
            },
            "risk_metrics": {
                "max_drawdown": risk_metrics.max_drawdown if risk_metrics else 0,
                "sharpe_ratio": risk_metrics.sharpe_ratio if risk_metrics else 0,
                "volatility": volatility,
                "value_at_risk_95": var_95,
                "last_updated": risk_metrics.timestamp.isoformat() if risk_metrics else None
            },
            "concentration_risk": concentration_risk,
            "risk_recommendations": _generate_risk_recommendations(concentration_risk, diversification_score, volatility)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting risk analysis: {str(e)}"
        )

@router.post("/rebalance")
async def rebalance_portfolio(
    target_allocations: Dict[str, float],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Rebalance portfolio to target allocations"""
    try:
        # Validate target allocations
        total_allocation = sum(target_allocations.values())
        if abs(total_allocation - 100.0) > 0.01:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target allocations must sum to 100%"
            )
        
        # Get current portfolio
        portfolios = db.query(Portfolio).filter(Portfolio.user_id == current_user.id).all()
        total_value = sum([p.total_value for p in portfolios])
        
        if total_value == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Portfolio has no value to rebalance"
            )
        
        # Calculate rebalancing actions
        rebalancing_actions = []
        
        for portfolio in portfolios:
            symbol = portfolio.symbol
            current_allocation = (portfolio.total_value / total_value) * 100
            target_allocation = target_allocations.get(symbol, 0)
            
            if abs(current_allocation - target_allocation) > 1.0:  # 1% threshold
                if target_allocation > current_allocation:
                    # Need to buy more
                    additional_value = (target_allocation - current_allocation) / 100 * total_value
                    action = "BUY"
                else:
                    # Need to sell some
                    reduction_value = (current_allocation - target_allocation) / 100 * total_value
                    additional_value = -reduction_value
                    action = "SELL"
                
                rebalancing_actions.append({
                    "symbol": symbol,
                    "action": action,
                    "current_allocation": current_allocation,
                    "target_allocation": target_allocation,
                    "value_change": additional_value,
                    "quantity_change": additional_value / portfolio.current_price if portfolio.current_price > 0 else 0
                })
        
        # Sort actions by absolute value change (largest first)
        rebalancing_actions.sort(key=lambda x: abs(x["value_change"]), reverse=True)
        
        return {
            "message": "Portfolio rebalancing analysis completed",
            "total_portfolio_value": total_value,
            "rebalancing_actions": rebalancing_actions,
            "total_actions": len(rebalancing_actions),
            "note": "This is a simulation. Execute trades manually or use the trading bot to implement these changes."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing portfolio rebalancing: {str(e)}"
        )

def _generate_risk_recommendations(concentration_risk, diversification_score, volatility):
    """Generate risk recommendations based on portfolio analysis"""
    recommendations = []
    
    # Check concentration risk
    high_concentration = [p for p in concentration_risk if p["risk_level"] == "high"]
    if high_concentration:
        recommendations.append({
            "type": "warning",
            "message": f"High concentration in {len(high_concentration)} positions. Consider diversifying to reduce risk.",
            "priority": "high"
        })
    
    # Check diversification
    if diversification_score < 30:
        recommendations.append({
            "type": "warning",
            "message": "Low portfolio diversification. Consider adding more positions across different assets.",
            "priority": "medium"
        })
    
    # Check volatility
    if volatility > 0.5:  # 50% volatility
        recommendations.append({
            "type": "warning",
            "message": "High portfolio volatility detected. Consider adding defensive positions or reducing risk exposure.",
            "priority": "medium"
        })
    
    # Add general recommendations
    if not recommendations:
        recommendations.append({
            "type": "info",
            "message": "Portfolio risk levels appear normal. Continue monitoring and maintain current risk management practices.",
            "priority": "low"
        })
    
    return recommendations

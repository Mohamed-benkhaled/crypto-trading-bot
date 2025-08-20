# 🚀 Advanced Crypto Trading Bot

A sophisticated cryptocurrency trading bot with multiple strategies, real-time data, and a modern web interface.

## 🌟 Features

- **Multiple Trading Strategies**: RSI, MACD, Bollinger Bands, Moving Averages
- **Real-time Data**: Live price feeds from multiple exchanges
- **Risk Management**: Stop-loss, take-profit, position sizing
- **Modern Web UI**: Interactive charts and trading dashboard
- **Backtesting**: Historical strategy performance analysis
- **Multi-exchange Support**: Binance, Coinbase, and more
- **Portfolio Tracking**: Real-time P&L and performance metrics

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React + TradingView charts
- **Database**: SQLite + SQLAlchemy
- **Trading Engine**: Custom strategies with TA-Lib
- **Real-time**: WebSocket connections
- **Charts**: Plotly + Dash

## 🚀 Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Run the Application**:
   ```bash
   python main.py
   ```

4. **Access the Web Interface**:
   - Open http://localhost:8000
   - Login with default credentials: admin/admin

## 📊 Trading Strategies

### 1. RSI Strategy
- Buy when RSI < 30 (oversold)
- Sell when RSI > 70 (overbought)
- Customizable thresholds

### 2. MACD Strategy
- Golden cross (MACD > Signal)
- Death cross (MACD < Signal)
- Volume confirmation

### 3. Bollinger Bands Strategy
- Price touches lower band = Buy signal
- Price touches upper band = Sell signal
- Volatility-based position sizing

### 4. Moving Average Crossover
- Short MA crosses above long MA = Buy
- Short MA crosses below long MA = Sell
- Multiple timeframe support

## 🔐 Security Features

- JWT authentication
- API key encryption
- Rate limiting
- Input validation
- SQL injection protection

## 📈 Risk Management

- Position sizing based on volatility
- Dynamic stop-loss adjustment
- Maximum drawdown limits
- Portfolio diversification rules

## 🌐 API Endpoints

- `POST /api/auth/login` - User authentication
- `GET /api/trading/strategies` - Available strategies
- `POST /api/trading/start` - Start trading bot
- `GET /api/trading/status` - Bot status
- `GET /api/portfolio/overview` - Portfolio summary
- `GET /api/history/trades` - Trading history

## 📝 Configuration

Edit `config.py` to customize:
- Trading pairs
- Strategy parameters
- Risk limits
- Exchange settings

## ⚠️ Disclaimer

This is for educational purposes only. Cryptocurrency trading involves significant risk. Never invest more than you can afford to lose.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

MIT License - see LICENSE file for details

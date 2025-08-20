# 🚀 Quick Start Guide - Crypto Trading Bot

Get your advanced crypto trading bot up and running in minutes!

## ⚡ Quick Setup (5 minutes)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Setup Script
```bash
python setup.py
```

### 3. Start the Bot
```bash
python main.py
```

### 4. Access Web Interface
Open your browser and go to: **http://localhost:8000**

### 5. Login
- **Username:** `admin`
- **Password:** `admin`
- ⚠️ **Change password after first login!**

## 🔧 Configuration

### API Keys Setup
1. Get your Binance API keys from [Binance](https://www.binance.com/en/my/settings/api-management)
2. Edit the `.env` file:
```env
BINANCE_API_KEY=your_actual_api_key_here
BINANCE_SECRET_KEY=your_actual_secret_key_here
BINANCE_TESTNET=true  # Set to false for real trading
```

### Trading Settings
Edit `.env` file to customize:
```env
MAX_POSITION_SIZE=0.1        # 10% of portfolio per trade
STOP_LOSS_PERCENTAGE=0.02    # 2% stop loss
TAKE_PROFIT_PERCENTAGE=0.06  # 6% take profit
MAX_DRAWDOWN=0.15           # 15% max drawdown
```

## 📊 Features Available

### ✅ Ready to Use
- **5 Trading Strategies**: RSI, MACD, Bollinger Bands, Moving Averages, Grid Trading
- **Risk Management**: Position sizing, stop-loss, take-profit, drawdown limits
- **Portfolio Tracking**: Real-time P&L, position management, risk analytics
- **Web Dashboard**: Modern UI with charts, real-time data, bot controls
- **API Integration**: Binance, Coinbase Pro support
- **Database**: SQLite with full trade history and analytics

### 🚧 Coming Soon
- Backtesting engine
- Advanced risk metrics
- Mobile app
- Telegram notifications
- Multi-exchange arbitrage

## 🎯 First Steps

### 1. Create a Strategy
1. Go to **Strategies** section
2. Click **Create New Strategy**
3. Choose strategy type (start with RSI)
4. Set trading pair (e.g., BTC/USDT)
5. Set risk level (start with Low)

### 2. Start Trading
1. Go to **Trading** section
2. Click **Start Bot**
3. Monitor signals and trades
4. Check portfolio performance

### 3. Monitor Portfolio
1. Go to **Portfolio** section
2. View current positions
3. Check P&L and risk metrics
4. Analyze performance over time

## 🔒 Security Features

- JWT authentication
- API key encryption
- Rate limiting
- Input validation
- SQL injection protection
- CORS security

## 📈 Trading Strategies Explained

### RSI Strategy
- **Buy**: When RSI < 30 (oversold)
- **Sell**: When RSI > 70 (overbought)
- **Best for**: Range-bound markets

### MACD Strategy
- **Buy**: Golden cross (MACD > Signal)
- **Sell**: Death cross (MACD < Signal)
- **Best for**: Trend following

### Bollinger Bands
- **Buy**: Price touches lower band
- **Sell**: Price touches upper band
- **Best for**: Volatility trading

### Moving Average Crossover
- **Buy**: Fast MA crosses above slow MA
- **Sell**: Fast MA crosses below slow MA
- **Best for**: Trend identification

### Grid Trading
- **Automated**: Buy/sell at price intervals
- **Best for**: Sideways markets

## 🚨 Important Notes

### ⚠️ Risk Warning
- **This is for educational purposes**
- **Cryptocurrency trading involves significant risk**
- **Never invest more than you can afford to lose**
- **Start with small amounts and testnet**

### 🔧 Technical Requirements
- Python 3.8+
- 4GB RAM minimum
- Stable internet connection
- 24/7 operation recommended

## 🆘 Troubleshooting

### Common Issues

#### "Module not found" errors
```bash
pip install -r requirements.txt
```

#### Database errors
```bash
python setup.py
```

#### API connection issues
- Check your API keys in `.env`
- Verify internet connection
- Check Binance API status

#### Bot won't start
- Check strategy configuration
- Verify trading pairs exist
- Check API permissions

### Getting Help
1. Check the logs in console output
2. Verify all dependencies are installed
3. Ensure `.env` file is configured correctly
4. Check API key permissions on Binance

## 📚 Next Steps

### Advanced Configuration
- Customize strategy parameters
- Set up multiple strategies
- Configure advanced risk rules
- Set up portfolio rebalancing

### Monitoring & Alerts
- Set up performance tracking
- Monitor risk metrics
- Track strategy performance
- Set up automated reports

### Production Deployment
- Use production API keys
- Set up proper logging
- Configure monitoring
- Set up backups

## 🎉 You're Ready!

Your crypto trading bot is now running! Start with small amounts, monitor performance, and gradually increase your trading capital as you gain confidence in the system.

**Happy Trading! 🚀📈**

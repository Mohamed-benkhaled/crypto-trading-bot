import asyncio
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging
import ccxt
import ccxt.async_support as ccxt_async
from binance.client import Client
from binance.exceptions import BinanceAPIException

from core.config import settings, EXCHANGE_CONFIG

logger = logging.getLogger(__name__)

class ExchangeInterface:
    """Interface for connecting to cryptocurrency exchanges"""
    
    def __init__(self, exchange_name: str = "binance"):
        self.exchange_name = exchange_name
        self.exchange = None
        self.client = None
        self.is_connected = False
        
        # Get exchange configuration
        self.config = EXCHANGE_CONFIG.get(exchange_name, {})
        self.testnet = self.config.get("testnet", True)
        self.sandbox = self.config.get("sandbox", True)
        
        # Initialize exchange
        self._initialize_exchange()
    
    def _initialize_exchange(self):
        """Initialize the exchange connection"""
        try:
            if self.exchange_name == "binance":
                # Initialize Binance client
                api_key = settings.BINANCE_API_KEY if hasattr(settings, 'BINANCE_API_KEY') else ""
                api_secret = settings.BINANCE_SECRET_KEY if hasattr(settings, 'BINANCE_SECRET_KEY') else ""
                
                if self.testnet:
                    self.client = Client(api_key, api_secret, testnet=True)
                    logger.info("Initialized Binance testnet client")
                else:
                    self.client = Client(api_key, api_secret)
                    logger.info("Initialized Binance mainnet client")
                
                # Initialize CCXT for additional functionality
                self.exchange = ccxt_async.binance({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'sandbox': self.sandbox,
                    'testnet': self.testnet,
                    'enableRateLimit': True,
                })
                
            elif self.exchange_name == "coinbase":
                # Initialize Coinbase Pro
                api_key = settings.COINBASE_API_KEY if hasattr(settings, 'COINBASE_API_KEY') else ""
                api_secret = settings.COINBASE_SECRET_KEY if hasattr(settings, 'COINBASE_SECRET_KEY') else ""
                passphrase = settings.COINBASE_PASSPHRASE if hasattr(settings, 'COINBASE_PASSPHRASE') else ""
                
                self.exchange = ccxt_async.coinbasepro({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'password': passphrase,
                    'sandbox': self.sandbox,
                    'enableRateLimit': True,
                })
                
            else:
                # Generic CCXT exchange
                self.exchange = ccxt_async.exchange({
                    'sandbox': self.sandbox,
                    'enableRateLimit': True,
                })
                
            logger.info(f"Initialized {self.exchange_name} exchange interface")
            
        except Exception as e:
            logger.error(f"Error initializing exchange: {e}")
            self.exchange = None
            self.client = None
    
    async def connect(self) -> bool:
        """Connect to the exchange"""
        try:
            if self.exchange:
                await self.exchange.load_markets()
                self.is_connected = True
                logger.info(f"Connected to {self.exchange_name}")
                return True
            else:
                logger.error("Exchange not initialized")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to exchange: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from the exchange"""
        try:
            if self.exchange:
                await self.exchange.close()
                self.is_connected = False
                logger.info(f"Disconnected from {self.exchange_name}")
        except Exception as e:
            logger.error(f"Error disconnecting from exchange: {e}")
    
    async def get_balance(self) -> float:
        """Get current account balance"""
        try:
            if not self.is_connected:
                logger.warning("Not connected to exchange")
                return 0.0
            
            if self.exchange_name == "binance" and self.client:
                # Use Binance client for balance
                account = self.client.get_account()
                balances = account['balances']
                
                # Calculate total USDT value
                total_balance = 0.0
                for balance in balances:
                    if float(balance['free']) > 0 or float(balance['locked']) > 0:
                        symbol = balance['asset']
                        free_amount = float(balance['free'])
                        locked_amount = float(balance['locked'])
                        total_amount = free_amount + locked_amount
                        
                        if symbol == 'USDT':
                            total_balance += total_amount
                        else:
                            # Convert to USDT value
                            try:
                                ticker = self.client.get_symbol_ticker(symbol=f"{symbol}USDT")
                                usdt_value = total_amount * float(ticker['price'])
                                total_balance += usdt_value
                            except:
                                # Skip if conversion not possible
                                pass
                
                return total_balance
                
            else:
                # Use CCXT for other exchanges
                balance = await self.exchange.fetch_balance()
                total_balance = 0.0
                
                for currency, amount in balance['total'].items():
                    if amount > 0:
                        if currency == 'USDT' or currency == 'USD':
                            total_balance += amount
                        else:
                            # Convert to USDT value
                            try:
                                ticker = await self.exchange.fetch_ticker(f"{currency}/USDT")
                                usdt_value = amount * ticker['last']
                                total_balance += usdt_value
                            except:
                                # Skip if conversion not possible
                                pass
                
                return total_balance
                
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return 0.0
    
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        try:
            if not self.is_connected:
                logger.warning("Not connected to exchange")
                return None
            
            if self.exchange_name == "binance" and self.client:
                # Use Binance client
                ticker = self.client.get_symbol_ticker(symbol=symbol)
                return float(ticker['price'])
                
            else:
                # Use CCXT
                ticker = await self.exchange.fetch_ticker(symbol)
                return ticker['last']
                
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return None
    
    async def get_market_data(self, symbol: str, timeframe: str = "1h", limit: int = 200) -> Optional[pd.DataFrame]:
        """Get historical market data (OHLCV)"""
        try:
            if not self.is_connected:
                logger.warning("Not connected to exchange")
                return None
            
            # Convert timeframe to CCXT format
            ccxt_timeframe = self._convert_timeframe(timeframe)
            
            # Fetch OHLCV data
            ohlcv = await self.exchange.fetch_ohlcv(symbol, ccxt_timeframe, limit=limit)
            
            if not ohlcv:
                logger.warning(f"No market data received for {symbol}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Ensure data types
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Remove any NaN values
            df.dropna(inplace=True)
            
            logger.info(f"Retrieved {len(df)} data points for {symbol} ({timeframe})")
            return df
            
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return None
    
    async def place_order(self, symbol: str, side: str, quantity: float, price: float, order_type: str = "LIMIT") -> Optional[Dict]:
        """Place an order on the exchange"""
        try:
            if not self.is_connected:
                logger.warning("Not connected to exchange")
                return None
            
            if self.exchange_name == "binance" and self.client:
                # Use Binance client
                try:
                    if order_type == "LIMIT":
                        order = self.client.create_order(
                            symbol=symbol,
                            side=side,
                            type=order_type,
                            timeInForce='GTC',
                            quantity=quantity,
                            price=price
                        )
                    else:
                        order = self.client.create_order(
                            symbol=symbol,
                            side=side,
                            type=order_type,
                            quantity=quantity
                        )
                    
                    logger.info(f"Placed {side} order for {quantity} {symbol} at {price}")
                    return order
                    
                except BinanceAPIException as e:
                    logger.error(f"Binance API error: {e}")
                    return None
                    
            else:
                # Use CCXT
                order = await self.exchange.create_order(
                    symbol=symbol,
                    type=order_type.lower(),
                    side=side.lower(),
                    amount=quantity,
                    price=price if order_type == "LIMIT" else None
                )
                
                logger.info(f"Placed {side} order for {quantity} {symbol} at {price}")
                return order
                
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
    
    async def get_order_status(self, order_id: str, symbol: str) -> Optional[Dict]:
        """Get the status of an order"""
        try:
            if not self.is_connected:
                logger.warning("Not connected to exchange")
                return None
            
            if self.exchange_name == "binance" and self.client:
                # Use Binance client
                order = self.client.get_order(symbol=symbol, orderId=order_id)
                return order
                
            else:
                # Use CCXT
                order = await self.exchange.fetch_order(order_id, symbol)
                return order
                
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return None
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order"""
        try:
            if not self.is_connected:
                logger.warning("Not connected to exchange")
                return False
            
            if self.exchange_name == "binance" and self.client:
                # Use Binance client
                result = self.client.cancel_order(symbol=symbol, orderId=order_id)
                logger.info(f"Cancelled order {order_id} for {symbol}")
                return True
                
            else:
                # Use CCXT
                result = await self.exchange.cancel_order(order_id, symbol)
                logger.info(f"Cancelled order {order_id} for {symbol}")
                return True
                
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
    
    async def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """Get open orders"""
        try:
            if not self.is_connected:
                logger.warning("Not connected to exchange")
                return []
            
            if self.exchange_name == "binance" and self.client:
                # Use Binance client
                if symbol:
                    orders = self.client.get_open_orders(symbol=symbol)
                else:
                    orders = self.client.get_open_orders()
                return orders
                
            else:
                # Use CCXT
                if symbol:
                    orders = await self.exchange.fetch_open_orders(symbol)
                else:
                    orders = await self.exchange.fetch_open_orders()
                return orders
                
        except Exception as e:
            logger.error(f"Error getting open orders: {e}")
            return []
    
    async def get_trading_pairs(self) -> List[str]:
        """Get available trading pairs"""
        try:
            if not self.is_connected:
                logger.warning("Not connected to exchange")
                return []
            
            if self.exchange_name == "binance" and self.client:
                # Use Binance client
                exchange_info = self.client.get_exchange_info()
                symbols = [symbol['symbol'] for symbol in exchange_info['symbols'] if symbol['status'] == 'TRADING']
                return symbols
                
            else:
                # Use CCXT
                markets = await self.exchange.load_markets()
                symbols = list(markets.keys())
                return symbols
                
        except Exception as e:
            logger.error(f"Error getting trading pairs: {e}")
            return []
    
    def _convert_timeframe(self, timeframe: str) -> str:
        """Convert timeframe to CCXT format"""
        timeframe_map = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1h": "1h",
            "4h": "4h",
            "1d": "1d",
            "1w": "1w"
        }
        return timeframe_map.get(timeframe, "1h")
    
    def get_exchange_info(self) -> Dict[str, Any]:
        """Get exchange information"""
        return {
            "name": self.exchange_name,
            "connected": self.is_connected,
            "testnet": self.testnet,
            "sandbox": self.sandbox,
            "config": self.config
        }
    
    async def test_connection(self) -> bool:
        """Test the exchange connection"""
        try:
            if not self.exchange:
                return False
            
            # Try to fetch markets
            await self.exchange.load_markets()
            return True
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

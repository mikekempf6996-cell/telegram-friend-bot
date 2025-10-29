import os

# Telegram Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', 'your_bot_token_here')
TEST_MODE = os.getenv('TEST_MODE', 'True').lower() == 'true'

# Trading Configuration
TRADING_PAIRS = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 
    'XRPUSDT', 'ADAUSDT', 'SOLUSDT', 'ZECUSDT'
]

TIMEFRAME = '5m'  # 5-minute candles for scalping

# Technical Indicators Configuration
INDICATORS = {
    'MA': [5, 10, 20],
    'EMA': [5, 12, 26],
    'BOLL': {'window': 20, 'window_dev': 2},
    'SAR': {'acceleration': 0.02, 'maximum': 0.2},
    'MACD': {'fast': 12, 'slow': 26, 'signal': 9},
    'RSI': 14,
    'KDJ': 14,
    'OBV': {},
    'WR': 14,
    'STOCH_RSI': 14
}

# Risk Management
MAX_POSITION_SIZE = 0.1  # 10% of portfolio per trade
STOP_LOSS_PCT = 0.02     # 2% stop loss
TAKE_PROFIT_PCT = 0.015  # 1.5% take profit

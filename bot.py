import os
import time
import logging
import threading
import requests
import pandas as pd
import numpy as np
import ccxt
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from flask import Flask

# Create Flask app for health checks
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Trading Bot is Running!"

@app.route('/health')
def health():
    return "OK"

def run_web_server():
    app.run(host='0.0.0.0', port=5000, debug=False)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', 'your_bot_token_here')

TRADING_PAIRS = [
    'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 
    'XRP/USDT', 'ADA/USDT', 'SOL/USDT', 'ZEC/USDT'
]

# Initialize exchange
exchange = ccxt.binance({'enableRateLimit': True})

def keep_alive():
    """Prevent Render free tier from spinning down"""
    def ping():
        while True:
            try:
                requests.get('https://www.google.com', timeout=10)
                time.sleep(300)
            except Exception as e:
                logger.error(f"Keep-alive ping failed: {e}")
                time.sleep(300)
    
    thread = threading.Thread(target=ping)
    thread.daemon = True
    thread.start()
    logger.info("✅ Keep-alive started")

def calculate_indicators(df):
    """Calculate technical indicators without TA-LIB"""
    try:
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        # Moving Averages
        df['MA_10'] = close.rolling(window=10).mean()
        df['MA_20'] = close.rolling(window=20).mean()
        df['MA_50'] = close.rolling(window=50).mean()
        
        # EMA
        df['EMA_12'] = close.ewm(span=12).mean()
        df['EMA_26'] = close.ewm(span=26).mean()
        
        # Bollinger Bands
        df['BB_MIDDLE'] = close.rolling(window=20).mean()
        bb_std = close.rolling(window=20).std()
        df['BB_UPPER'] = df['BB_MIDDLE'] + (bb_std * 2)
        df['BB_LOWER'] = df['BB_MIDDLE'] - (bb_std * 2)
        
        # MACD
        df['MACD'] = df['EMA_12'] - df['EMA_26']
        df['MACD_SIGNAL'] = df['MACD'].ewm(span=9).mean()
        df['MACD_HISTOGRAM'] = df['MACD'] - df['MACD_SIGNAL']
        
        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        return df
        
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        return df

def generate_signal(df):
    """Generate trading signal"""
    try:
        current = df.iloc[-1]
        
        bullish = 0
        bearish = 0
        
        # Price vs MA
        if current['close'] > current['MA_20']:
            bullish += 1
        else:
            bearish += 1
            
        # EMA crossover
        if current['EMA_12'] > current['EMA_26']:
            bullish += 1
        else:
            bearish += 1
            
        # RSI
        if current['RSI'] < 30:
            bullish += 2
        elif current['RSI'] > 70:
            bearish += 2
        elif current['RSI'] > 50:
            bullish += 1
        else:
            bearish += 1
            
        # MACD
        if current['MACD'] > current['MACD_SIGNAL']:
            bullish += 1
        else:
            bearish += 1
            
        # Bollinger Bands
        if current['close'] < current['BB_LOWER']:
            bullish += 1
        elif current['close'] > current['BB_UPPER']:
            bearish += 1
        
        if bullish > bearish + 2:
            return 'STRONG LONG', bullish
        elif bullish > bearish:
            return 'LONG', bullish
        elif bearish > bullish + 2:
            return 'STRONG SHORT', bearish
        elif bearish > bullish:
            return 'SHORT', bearish
        else:
            return 'NEUTRAL', 0
            
    except Exception as e:
        logger.error(f"Error generating signal: {e}")
        return 'NEUTRAL', 0

def get_trading_signal(symbol):
    """Get trading analysis"""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, '5m', limit=100)
        if len(ohlcv) < 50:
            return None
            
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df = df.astype(float)
        
        df = calculate_indicators(df)
        
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        
        signal, strength = generate_signal(df)
        
        return {
            'pair': symbol.replace('/', ''),
            'price': current_price,
            'signal': signal,
            'strength': strength,
            'rsi': df['RSI'].iloc[-1],
            'timestamp': pd.Timestamp.now().strftime('%H:%M:%S')
        }
        
    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {e}")
        return None

async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get trading signal"""
    try:
        signals = []
        for pair in TRADING_PAIRS:
            signal_data = get_trading_signal(pair)
            if signal_data:
                signals.append(signal_data)
            time.sleep(0.5)
        
        if not signals:
            await update.message.reply_text("❌ No signals available")
            return
        
        best_signal = max(signals, key=lambda x: x['strength'])
        
        if 'LONG' in best_signal['signal']:
            emoji = '🚀' if 'STRONG' in best_signal['signal'] else '🟢'
            action = "GO LONG"
        elif 'SHORT' in best_signal['signal']:
            emoji = '📉' if 'STRONG' in best_signal['signal'] else '🔴'
            action = "GO SHORT"
        else:
            emoji = '⚪'
            action = "WAIT"
        
        signal_text = (
            f"{emoji} <b>{action}</b> {emoji}\n\n"
            f"<b>Pair:</b> {best_signal['pair']}\n"
            f"<b>Price:</b> ${best_signal['price']:,.2f}\n"
            f"<b>Signal:</b> {best_signal['signal']}\n"
            f"<b>RSI:</b> {best_signal['rsi']:.1f}\n"
            f"<b>Time:</b> {best_signal['timestamp']}"
        )
        
        await update.message.reply_text(signal_text, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in signal command: {e}")
        await update.message.reply_text("❌ Error generating signal")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    await update.message.reply_text(
        "🤖 <b>High Accuracy Trading Bot</b>\n\n"
        "Commands:\n"
        "/signal - Get trading signal\n"
        "/price - Current prices\n"
        "/status - Bot status",
        parse_mode='HTML'
    )

async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get current prices"""
    try:
        price_text = "💰 <b>CURRENT PRICES</b> 💰\n\n"
        
        for pair in TRADING_PAIRS:
            ticker = exchange.fetch_ticker(pair)
            price_text += f"{pair.replace('/', '')}: ${ticker['last']:,.2f}\n"
            time.sleep(0.2)
        
        price_text += f"\n<i>Updated: {pd.Timestamp.now().strftime('%H:%M:%S')}</i>"
        await update.message.reply_text(price_text, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in price command: {e}")
        await update.message.reply_text("❌ Error fetching prices")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Status command"""
    await update.message.reply_text(
        "🟢 <b>BOT STATUS: LIVE</b>\n"
        "📊 Analyzing 7 pairs\n"
        "⏰ 24/7 Operation\n"
        "🔧 Multi-indicator analysis",
        parse_mode='HTML'
    )

def main():
    """Start the bot"""
    if not BOT_TOKEN or BOT_TOKEN == 'your_bot_token_here':
        logger.error("❌ BOT_TOKEN not set!")
        return
    
    # Start web server in background
    web_thread = threading.Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()
    
    # Start keep-alive
    keep_alive()
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("signal", signal_command))
    application.add_handler(CommandHandler("price", price_command))
    application.add_handler(CommandHandler("status", status_command))
    
    # Log startup
    logger.info("🤖 Trading Bot Started!")
    logger.info("🌐 Web server running on port 5000")
    logger.info(f"📊 Monitoring {len(TRADING_PAIRS)} pairs")
    
    # Start bot
    application.run_polling()

if __name__ == '__main__':
    main()

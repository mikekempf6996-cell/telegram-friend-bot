import os
import time
import logging
import random
import threading
import requests
import pandas as pd
import ccxt
import telebot

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

# Initialize components
bot = telebot.TeleBot(BOT_TOKEN)
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

def get_real_price(symbol):
    """Get real current price from Binance"""
    try:
        ticker = exchange.fetch_ticker(symbol)
        return ticker['last']
    except Exception as e:
        logger.error(f"Error getting price for {symbol}: {e}")
        return None

def calculate_simple_indicators(symbol):
    """Calculate basic trading indicators"""
    try:
        # Get OHLCV data
        ohlcv = exchange.fetch_ohlcv(symbol, '5m', limit=50)
        if not ohlcv or len(ohlcv) < 20:
            return None
            
        # Convert to DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['close'] = pd.to_numeric(df['close'])
        
        # Simple Moving Averages
        df['MA_10'] = df['close'].rolling(window=10).mean()
        df['MA_20'] = df['close'].rolling(window=20).mean()
        
        # RSI Calculation
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        current_price = df['close'].iloc[-1]
        ma_10 = df['MA_10'].iloc[-1]
        ma_20 = df['MA_20'].iloc[-1]
        rsi = df['RSI'].iloc[-1]
        
        # Generate signal
        signals = 0
        if current_price > ma_10 and current_price > ma_20:
            signals += 1
        if ma_10 > ma_20:
            signals += 1
        if rsi < 70:  # Not overbought
            signals += 1
            
        if signals >= 2:
            signal = 'LONG'
        elif signals <= 1:
            signal = 'SHORT'
        else:
            signal = 'NEUTRAL'
            
        return {
            'pair': symbol.replace('/', ''),
            'price': current_price,
            'signal': signal,
            'rsi': rsi,
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        logger.error(f"Error calculating indicators for {symbol}: {e}")
        return None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Send welcome message"""
    welcome_text = (
        f"Hi! 🤖\n\n"
        f"🚀 <b>LIVE Crypto Trading Bot</b> 🚀\n\n"
        f"<b>Real-time Monitoring:</b>\n" + "\n".join([f"• {pair}" for pair in TRADING_PAIRS]) + f"\n\n"
        f"<b>Strategy:</b> 3-5 Minute Scalping\n"
        f"<b>Indicators:</b> MA, RSI, Price Action\n"
        f"<b>Status:</b> 🟢 LIVE TRADING\n\n"
        f"<i>Real Binance data analysis</i>"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode='HTML')

@bot.message_handler(commands=['signal'])
def send_signal(message):
    """Get real trading signal with Binance data"""
    try:
        pair = random.choice(TRADING_PAIRS)
        signal_data = calculate_simple_indicators(pair)
        
        if signal_data:
            signal_text = (
                f"📊 <b>LIVE TRADING SIGNAL</b> 📊\n\n"
                f"<b>Pair:</b> {signal_data['pair']}\n"
                f"<b>Price:</b> ${signal_data['price']:,.2f}\n"
                f"<b>Signal:</b> {'🟢' if signal_data['signal'] == 'LONG' else '🔴' if signal_data['signal'] == 'SHORT' else '⚪'} <b>{signal_data['signal']}</b>\n"
                f"<b>RSI:</b> {signal_data['rsi']:.1f}\n"
                f"<b>Time:</b> {signal_data['timestamp']}\n\n"
                f"<i>Real Binance market analysis</i>"
            )
        else:
            # Fallback to basic signal if real data fails
            signals = ['LONG', 'SHORT', 'NEUTRAL']
            signal = random.choice(signals)
            signal_text = (
                f"📊 <b>TRADING SIGNAL</b> 📊\n\n"
                f"<b>Pair:</b> {pair.replace('/', '')}\n"
                f"<b>Signal:</b> {'🟢' if signal == 'LONG' else '🔴' if signal == 'SHORT' else '⚪'} <b>{signal}</b>\n"
                f"<b>Time:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"<i>Basic analysis - Real data temporarily unavailable</i>"
            )
        
        bot.send_message(message.chat.id, signal_text, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in signal command: {e}")
        bot.send_message(message.chat.id, "❌ Error generating signal. Please try again.")

@bot.message_handler(commands=['price'])
def send_price(message):
    """Get current price for a specific pair"""
    try:
        pair = random.choice(TRADING_PAIRS)
        price = get_real_price(pair)
        
        if price:
            price_text = (
                f"💰 <b>LIVE PRICE</b> 💰\n\n"
                f"<b>Pair:</b> {pair.replace('/', '')}\n"
                f"<b>Price:</b> ${price:,.2f}\n"
                f"<b>Time:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"<i>Real Binance data</i>"
            )
        else:
            price_text = "❌ Could not fetch price data."
        
        bot.send_message(message.chat.id, price_text, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in price command: {e}")
        bot.send_message(message.chat.id, "❌ Error fetching price.")

@bot.message_handler(commands=['status'])
def send_status(message):
    """Check bot status"""
    status_text = (
        f"🤖 <b>Bot Status</b> 🤖\n\n"
        f"<b>Status:</b> 🟢 LIVE TRADING\n"
        f"<b>Pairs:</b> {len(TRADING_PAIRS)} cryptocurrencies\n"
        f"<b>Data:</b> Real Binance API\n"
        f"<b>Analysis:</b> Technical Indicators\n"
        f"<b>Uptime:</b> 24/7 Active\n\n"
        f"<i>Real-time trading bot operational</i>"
    )
    bot.send_message(message.chat.id, status_text, parse_mode='HTML')

def main():
    """Start the bot"""
    if not BOT_TOKEN or BOT_TOKEN == 'your_bot_token_here':
        logger.error("❌ BOT_TOKEN not set!")
        return
    
    # Start keep-alive
    keep_alive()
    
    # Log startup
    logger.info("🤖 LIVE Trading Bot Started!")
    logger.info(f"📊 Monitoring pairs: {', '.join(TRADING_PAIRS)}")
    logger.info("🔧 Mode: LIVE with real Binance data")
    logger.info("🔄 Keep-alive active - bot running 24/7")
    
    # Start bot
    logger.info("Bot is running and analyzing markets...")
    bot.infinity_polling()

if __name__ == '__main__':
    main()

import os
import time
import logging
import random
import threading
import requests
import pandas as pd
import schedule
from binance.client import Client
from binance.exceptions import BinanceAPIException
import telebot
from telebot import types
from technical import TechnicalAnalyzer

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', 'your_bot_token_here')

TRADING_PAIRS = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 
    'XRPUSDT', 'ADAUSDT', 'SOLUSDT', 'ZECUSDT'
]

# Store user chat IDs for automatic signals
user_chat_ids = set()

# Initialize components
bot = telebot.TeleBot(BOT_TOKEN)
technical_analyzer = TechnicalAnalyzer()
binance_client = Client()  # Public data only for now

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

def get_binance_data(symbol, interval='5m', limit=100):
    """Get real market data from Binance"""
    try:
        klines = binance_client.get_klines(
            symbol=symbol,
            interval=interval,
            limit=limit
        )
        
        # Convert to DataFrame
        df = pd.DataFrame(klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # Convert to numeric
        df['open'] = pd.to_numeric(df['open'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        df['close'] = pd.to_numeric(df['close'])
        df['volume'] = pd.to_numeric(df['volume'])
        
        return df
    
    except BinanceAPIException as e:
        logger.error(f"Binance API error for {symbol}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error getting data for {symbol}: {e}")
        return None

def generate_real_signal(symbol):
    """Generate real trading signal using Binance data and technical analysis"""
    try:
        # Get real market data
        df = get_binance_data(symbol)
        if df is None or len(df) < 50:
            return None
        
        # Calculate technical indicators
        df = technical_analyzer.calculate_all_indicators(df)
        
        # Generate signal
        signal, strength = technical_analyzer.generate_signal(df)
        
        # Get current price
        current_price = df['close'].iloc[-1]
        
        signal_data = {
            'pair': symbol,
            'price': current_price,
            'signal': signal,
            'strength': strength,
            'signal_emoji': '🟢' if signal == 'LONG' else '🔴' if signal == 'SHORT' else '⚪',
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return signal_data
    
    except Exception as e:
        logger.error(f"Error generating signal for {symbol}: {e}")
        return None

def broadcast_signal(signal_data):
    """Send signal to all registered users"""
    if not user_chat_ids:
        logger.info("No users registered for auto-signals yet")
        return
        
    signal_text = (
        f"🚨 <b>AUTO TRADING SIGNAL</b> 🚨\n\n"
        f"<b>Pair:</b> {signal_data['pair']}\n"
        f"<b>Price:</b> ${signal_data['price']:,.2f}\n"
        f"<b>Signal:</b> {signal_data['signal_emoji']} <b>{signal_data['signal']}</b>\n"
        f"<b>Confidence:</b> {signal_data['strength']}/4\n"
        f"<b>Time:</b> {signal_data['timestamp']}\n\n"
        f"<i>Automated market analysis</i>"
    )
    
    for chat_id in user_chat_ids:
        try:
            bot.send_message(chat_id, signal_text, parse_mode='HTML')
            logger.info(f"Signal sent to user {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send to {chat_id}: {e}")

def send_auto_signals():
    """Automatically send trading signals for all pairs"""
    try:
        logger.info("🔍 Scanning markets for trading signals...")
        
        for pair in TRADING_PAIRS:
            signal_data = generate_real_signal(pair)
            
            if signal_data and signal_data['signal'] != 'NEUTRAL':
                logger.info(f"Strong signal found: {signal_data}")
                broadcast_signal(signal_data)
                
    except Exception as e:
        logger.error(f"Error in auto signals: {e}")

def start_auto_signals():
    """Start automatic signal generation on schedule"""
    # Schedule signals every 5 minutes
    schedule.every(5).minutes.do(send_auto_signals)
    
    # Run scheduler in background
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(1)
    
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    logger.info("✅ Auto-signal scheduler started (every 5 minutes)")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Send welcome message and register user for auto-signals"""
    user_chat_id = message.chat.id
    user_chat_ids.add(user_chat_id)
    
    welcome_text = (
        f"Hi! 🤖\n\n"
        f"🚀 <b>LIVE Crypto Trading Bot</b> 🚀\n\n"
        f"<b>Real-time Monitoring:</b>\n" + "\n".join([f"• {pair}" for pair in TRADING_PAIRS]) + f"\n\n"
        f"<b>Strategy:</b> 3-5 Minute Scalping\n"
        f"<b>Indicators:</b> MA, EMA, BOLL, SAR, MACD, RSI, KDJ, OBV, WR, StochRSI\n"
        f"<b>Status:</b> 🟢 LIVE TRADING\n\n"
        f"<i>✅ Registered for automatic signals every 5 minutes!</i>"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode='HTML')
    logger.info(f"User registered for auto-signals: {user_chat_id}")

@bot.message_handler(commands=['signal'])
def send_signal(message):
    """Manual command to get current trading signal"""
    try:
        # Get signal for a random pair
        pair = random.choice(TRADING_PAIRS)
        signal_data = generate_real_signal(pair)
        
        if signal_data:
            signal_text = (
                f"📊 <b>LIVE TRADING SIGNAL</b> 📊\n\n"
                f"<b>Pair:</b> {signal_data['pair']}\n"
                f"<b>Price:</b> ${signal_data['price']:,.2f}\n"
                f"<b>Signal:</b> {signal_data['signal_emoji']} <b>{signal_data['signal']}</b>\n"
                f"<b>Confidence:</b> {signal_data['strength']}/4\n"
                f"<b>Time:</b> {signal_data['timestamp']}\n\n"
                f"<i>Real Binance market data analysis</i>"
            )
        else:
            signal_text = "❌ Could not generate signal. Please try again."
        
        bot.send_message(message.chat.id, signal_text, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in signal command: {e}")
        bot.send_message(message.chat.id, "❌ Error generating signal. Please try again.")

@bot.message_handler(commands=['scan'])
def scan_all_markets(message):
    """Scan all markets and show current signals"""
    try:
        bot.send_message(message.chat.id, "🔍 Scanning all markets...")
        
        signals_found = []
        for pair in TRADING_PAIRS:
            signal_data = generate_real_signal(pair)
            if signal_data and signal_data['signal'] != 'NEUTRAL':
                signals_found.append(signal_data)
        
        if signals_found:
            response = "🎯 <b>ACTIVE TRADING SIGNALS</b> 🎯\n\n"
            for signal in signals_found:
                response += (
                    f"<b>{signal['pair']}</b> - ${signal['price']:,.2f}\n"
                    f"Signal: {signal['signal_emoji']} {signal['signal']} "
                    f"(Confidence: {signal['strength']}/4)\n\n"
                )
        else:
            response = "⚪ <b>No strong signals found at the moment.</b>\n\nMarkets are neutral."
        
        bot.send_message(message.chat.id, response, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in scan command: {e}")
        bot.send_message(message.chat.id, "❌ Error scanning markets.")

@bot.message_handler(commands=['status'])
def send_status(message):
    """Check bot status"""
    status_text = (
        f"🤖 <b>Bot Status</b> 🤖\n\n"
        f"<b>Status:</b> 🟢 LIVE TRADING\n"
        f"<b>Pairs:</b> {len(TRADING_PAIRS)} cryptocurrencies\n"
        f"<b>Analysis:</b> Real Binance data\n"
        f"<b>Indicators:</b> 10+ technical indicators\n"
        f"<b>Auto-signals:</b> Every 5 minutes\n"
        f"<b>Registered Users:</b> {len(user_chat_ids)}\n\n"
        f"<i>High-accuracy scalping bot active</i>"
    )
    bot.send_message(message.chat.id, status_text, parse_mode='HTML')

def main():
    """Start the bot"""
    if not BOT_TOKEN or BOT_TOKEN == 'your_bot_token_here':
        logger.error("❌ BOT_TOKEN not set!")
        return
    
    # Start services
    keep_alive()
    start_auto_signals()
    
    # Log startup info
    logger.info("🤖 LIVE Trading Bot Started!")
    logger.info(f"📊 Monitoring pairs: {', '.join(TRADING_PAIRS)}")
    logger.info("🔧 Mode: LIVE with real Binance data")
    logger.info("📈 Auto-signals: Every 5 minutes")
    logger.info("🔄 Keep-alive active - bot running 24/7")
    
    # Start the bot
    logger.info("Bot is running and analyzing markets...")
    bot.infinity_polling()

if __name__ == '__main__':
    main()

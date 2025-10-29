import os
import time
import logging
import random
import threading
import requests
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

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

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

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Send welcome message"""
    welcome_text = (
        f"Hi! 🤖\n\n"
        f"🚀 <b>Crypto Trading Bot</b> 🚀\n\n"
        f"<b>Monitoring:</b>\n" + "\n".join([f"• {pair}" for pair in TRADING_PAIRS]) + f"\n\n"
        f"<b>Strategy:</b> 3-5 Minute Scalping\n"
        f"<b>Status:</b> 🟢 BASIC MODE\n\n"
        f"<i>Advanced features loading...</i>"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode='HTML')

@bot.message_handler(commands=['signal'])
def send_signal(message):
    """Manual command to get trading signal"""
    try:
        pair = random.choice(TRADING_PAIRS)
        signals = ['LONG', 'SHORT', 'NEUTRAL']
        signal = random.choice(signals)
        
        signal_text = (
            f"📊 <b>TRADING SIGNAL</b> 📊\n\n"
            f"<b>Pair:</b> {pair}\n"
            f"<b>Signal:</b> {'🟢' if signal == 'LONG' else '🔴' if signal == 'SHORT' else '⚪'} <b>{signal}</b>\n"
            f"<b>Time:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"<i>Basic mode - Advanced analysis coming soon</i>"
        )
        
        bot.send_message(message.chat.id, signal_text, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in signal command: {e}")
        bot.send_message(message.chat.id, "❌ Error generating signal.")

@bot.message_handler(commands=['status'])
def send_status(message):
    """Check bot status"""
    status_text = (
        f"🤖 <b>Bot Status</b> 🤖\n\n"
        f"<b>Status:</b> 🟢 RUNNING\n"
        f"<b>Pairs:</b> {len(TRADING_PAIRS)}\n"
        f"<b>Mode:</b> Basic (Stable)\n"
        f"<b>Uptime:</b> 24/7 Active\n\n"
        f"<i>Core system operational</i>"
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
    logger.info("🤖 Trading Bot Started (Basic Mode)")
    logger.info(f"📊 Pairs: {', '.join(TRADING_PAIRS)}")
    logger.info("🔄 Keep-alive active")
    
    # Start bot
    logger.info("Bot is running...")
    bot.infinity_polling()

if __name__ == '__main__':
    main()

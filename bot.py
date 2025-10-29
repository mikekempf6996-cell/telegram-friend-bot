import os
import time
import logging
import requests
import pandas as pd
import ccxt
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
TRADING_PAIRS = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'SOL/USDT']
exchange = ccxt.binance()

def keep_alive():
    def ping():
        while True:
            try:
                requests.get('https://google.com')
                time.sleep(300)
            except:
                time.sleep(300)
    import threading
    thread = threading.Thread(target=ping)
    thread.daemon = True
    thread.start()

def get_signal(symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, '5m', limit=20)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df = df.astype(float)
        
        # Simple indicators
        df['MA_10'] = df['close'].rolling(10).mean()
        df['MA_20'] = df['close'].rolling(20).mean()
        df['RSI'] = 100 - (100 / (1 + (df['close'].diff().clip(lower=0).rolling(14).mean() / 
                                      -df['close'].diff().clip(upper=0).rolling(14).mean())))
        
        current = df.iloc[-1]
        price = exchange.fetch_ticker(symbol)['last']
        
        # Simple signal logic
        bullish = sum([
            current['close'] > current['MA_10'],
            current['MA_10'] > current['MA_20'], 
            current['RSI'] < 70,
            current['RSI'] > 30
        ])
        
        if bullish >= 3:
            signal = 'LONG'
        else:
            signal = 'SHORT'
            
        return {
            'pair': symbol.replace('/', ''),
            'price': price,
            'signal': signal,
            'rsi': current['RSI']
        }
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        signal_data = get_signal('BTC/USDT')
        if signal_data:
            text = f"🚀 {signal_data['signal']} {signal_data['pair']}\nPrice: ${signal_data['price']:.2f}\nRSI: {signal_data['rsi']:.1f}"
        else:
            text = "❌ Error getting signal"
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text("❌ Error")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Trading Bot Active\nUse /signal")

def main():
    if not BOT_TOKEN:
        logger.error("No BOT_TOKEN")
        return
        
    keep_alive()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("signal", signal_command))
    
    logger.info("Bot started!")
    app.run_polling()

if __name__ == '__main__':
    main()

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

def calculate_all_indicators(df):
    """Calculate all technical indicators"""
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
        
        # Parabolic SAR (simplified)
        df['SAR'] = calculate_parabolic_sar(high, low)
        
        # Volume indicators
        df['VOLUME_MA'] = volume.rolling(window=20).mean()
        df['OBV'] = calculate_obv(close, volume)
        
        # MACD
        ema_12 = close.ewm(span=12).mean()
        ema_26 = close.ewm(span=26).mean()
        df['MACD'] = ema_12 - ema_26
        df['MACD_SIGNAL'] = df['MACD'].ewm(span=9).mean()
        df['MACD_HISTOGRAM'] = df['MACD'] - df['MACD_SIGNAL']
        
        # RSI
        df['RSI'] = calculate_rsi(close)
        
        # KDJ (Stochastic Oscillator)
        df['K'], df['D'] = calculate_kdj(high, low, close)
        df['J'] = (3 * df['K']) - (2 * df['D'])
        
        # Williams %R
        df['WILLIAMS_R'] = calculate_williams_r(high, low, close)
        
        # Stochastic RSI
        df['STOCH_RSI'] = calculate_stoch_rsi(close)
        
        return df
        
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        return df

def calculate_parabolic_sar(high, low, acceleration=0.02, maximum=0.2):
    """Calculate Parabolic SAR"""
    sar = [low.iloc[0]]
    ep = high.iloc[0]
    af = acceleration
    
    for i in range(1, len(high)):
        if high.iloc[i] > ep:
            ep = high.iloc[i]
            af = min(af + acceleration, maximum)
        
        sar_current = sar[-1] + af * (ep - sar[-1])
        
        if sar_current > low.iloc[i]:
            sar_current = low.iloc[i]
        if sar_current > low.iloc[i-1]:
            sar_current = low.iloc[i-1]
            
        sar.append(sar_current)
    
    return pd.Series(sar, index=high.index)

def calculate_obv(close, volume):
    """Calculate On Balance Volume"""
    obv = [0]
    for i in range(1, len(close)):
        if close.iloc[i] > close.iloc[i-1]:
            obv.append(obv[-1] + volume.iloc[i])
        elif close.iloc[i] < close.iloc[i-1]:
            obv.append(obv[-1] - volume.iloc[i])
        else:
            obv.append(obv[-1])
    return pd.Series(obv, index=close.index)

def calculate_rsi(close, period=14):
    """Calculate RSI"""
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_kdj(high, low, close, period=14):
    """Calculate KDJ indicator"""
    lowest_low = low.rolling(window=period).min()
    highest_high = high.rolling(window=period).max()
    
    rsv = ((close - lowest_low) / (highest_high - lowest_low)) * 100
    k = rsv.ewm(com=2).mean()
    d = k.ewm(com=2).mean()
    
    return k, d

def calculate_williams_r(high, low, close, period=14):
    """Calculate Williams %R"""
    highest_high = high.rolling(window=period).max()
    lowest_low = low.rolling(window=period).min()
    williams_r = ((highest_high - close) / (highest_high - lowest_low)) * -100
    return williams_r

def calculate_stoch_rsi(close, period=14):
    """Calculate Stochastic RSI"""
    rsi = calculate_rsi(close, period)
    stoch_rsi = (rsi - rsi.rolling(window=period).min()) / (rsi.rolling(window=period).max() - rsi.rolling(window=period).min())
    return stoch_rsi * 100

def generate_trading_signal(df):
    """Generate trading signal based on all indicators"""
    try:
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        bullish_signals = 0
        bearish_signals = 0
        
        # Price vs MA analysis
        if current['close'] > current['MA_20']:
            bullish_signals += 1
        else:
            bearish_signals += 1
            
        if current['MA_10'] > current['MA_20']:
            bullish_signals += 1
        else:
            bearish_signals += 1
            
        # EMA analysis
        if current['EMA_12'] > current['EMA_26']:
            bullish_signals += 1
        else:
            bearish_signals += 1
            
        # Bollinger Bands
        if current['close'] < current['BB_LOWER']:
            bullish_signals += 1  # Oversold bounce potential
        elif current['close'] > current['BB_UPPER']:
            bearish_signals += 1  # Overbought rejection potential
            
        # RSI analysis
        if current['RSI'] < 30:
            bullish_signals += 2  # Strong oversold
        elif current['RSI'] > 70:
            bearish_signals += 2  # Strong overbought
        elif current['RSI'] > 50:
            bullish_signals += 1
        else:
            bearish_signals += 1
            
        # MACD analysis
        if current['MACD'] > current['MACD_SIGNAL']:
            bullish_signals += 1
        else:
            bearish_signals += 1
            
        # KDJ analysis
        if current['K'] > current['D'] and current['K'] < 20:
            bullish_signals += 1
        elif current['K'] < current['D'] and current['K'] > 80:
            bearish_signals += 1
            
        # Williams %R
        if current['WILLIAMS_R'] > -20:
            bearish_signals += 1
        elif current['WILLIAMS_R'] < -80:
            bullish_signals += 1
            
        # Volume confirmation
        if current['volume'] > current['VOLUME_MA']:
            if current['close'] > prev['close']:
                bullish_signals += 1
            else:
                bearish_signals += 1
        
        # Generate final signal
        signal_strength = abs(bullish_signals - bearish_signals)
        
        if bullish_signals > bearish_signals + 3:
            return 'STRONG LONG', signal_strength
        elif bullish_signals > bearish_signals:
            return 'LONG', signal_strength
        elif bearish_signals > bullish_signals + 3:
            return 'STRONG SHORT', signal_strength
        elif bearish_signals > bullish_signals:
            return 'SHORT', signal_strength
        else:
            return 'NEUTRAL', signal_strength
            
    except Exception as e:
        logger.error(f"Error generating signal: {e}")
        return 'NEUTRAL', 0

def get_trading_signal(symbol):
    """Get complete trading analysis for a symbol"""
    try:
        # Get OHLCV data
        ohlcv = exchange.fetch_ohlcv(symbol, '5m', limit=100)
        if len(ohlcv) < 50:
            return None
            
        # Convert to DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df = df.astype(float)
        
        # Calculate all indicators
        df = calculate_all_indicators(df)
        
        # Get current price
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        
        # Generate signal
        signal, strength = generate_trading_signal(df)
        
        return {
            'pair': symbol.replace('/', ''),
            'price': current_price,
            'signal': signal,
            'strength': strength,
            'rsi': df['RSI'].iloc[-1],
            'macd': df['MACD'].iloc[-1],
            'timestamp': pd.Timestamp.now().strftime('%H:%M:%S')
        }
        
    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {e}")
        return None

async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get trading signal"""
    try:
        # Analyze all pairs
        signals = []
        for pair in TRADING_PAIRS:
            signal_data = get_trading_signal(pair)
            if signal_data:
                signals.append(signal_data)
            time.sleep(0.5)  # Rate limiting
        
        if not signals:
            await update.message.reply_text("❌ No signals available")
            return
        
        # Find best signal
        best_signal = max(signals, key=lambda x: x['strength'])
        
        # Create signal message
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
            f"<b>Strength:</b> {best_signal['strength']}/10\n"
            f"<b>RSI:</b> {best_signal['rsi']:.1f}\n"
            f"<b>Time:</b> {best_signal['timestamp']}\n\n"
            f"<i>Multi-indicator analysis</i>"
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
            time.sleep(0.2)  # Rate limiting
        
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
    logger.info("🤖 High Accuracy Trading Bot Started!")
    logger.info(f"📊 Monitoring {len(TRADING_PAIRS)} pairs")
    logger.info("📈 Using 12 technical indicators")
    logger.info("🔄 24/7 operation active")
    
    # Start bot
    application.run_polling()

if __name__ == '__main__':
    main()

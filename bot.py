import os
import time
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import config

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self):
        self.app = None
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message when the command /start is issued."""
        user = update.effective_user
        await update.message.reply_html(
            f"Hi {user.mention_html()}! 🤖\n\n"
            f"🚀 <b>Crypto Futures Trading Bot</b> 🚀\n\n"
            f"<b>Pairs Monitoring:</b>\n" + "\n".join([f"• {pair}" for pair in config.TRADING_PAIRS]) + f"\n\n"
            f"<b>Timeframe:</b> {config.TIMEFRAME}\n"
            f"<b>Strategy:</b> 3-5 Minute Scalping\n"
            f"<b>Status:</b> {'🔴 TEST MODE' if config.TEST_MODE else '🟢 LIVE TRADING'}\n\n"
            f"Bot will send automatic trading signals for LONG/SHORT positions."
        )
    
    async def get_signal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manual command to get current trading signal."""
        try:
            # Simulate signal for now
            signal_data = await self.generate_test_signal()
            
            message = (
                f"📊 <b>Trading Signal - TEST DATA</b> 📊\n\n"
                f"<b>Pair:</b> {signal_data['pair']}\n"
                f"<b>Price:</b> ${signal_data['price']:,.2f}\n"
                f"<b>Signal:</b> {signal_data['signal_emoji']} {signal_data['signal']}\n"
                f"<b>Strength:</b> {signal_data['strength']}/5\n\n"
                f"<i>Note: Currently in TEST MODE - Basic version</i>"
            )
            
            await update.message.reply_html(message)
            
        except Exception as e:
            logger.error(f"Error in get_signal: {e}")
            await update.message.reply_html("❌ Error generating signal. Please try again.")
    
    async def generate_test_signal(self):
        """Generate test trading signal."""
        import random
        
        pairs = config.TRADING_PAIRS
        pair = random.choice(pairs)
        
        # Simulate price data
        signals = ['LONG', 'SHORT', 'NEUTRAL']
        signal = random.choice(signals)
        
        signal_data = {
            'pair': pair,
            'price': random.uniform(100, 50000),
            'signal': signal,
            'strength': random.randint(1, 5),
            'signal_emoji': '🟢' if signal == 'LONG' else '🔴' if signal == 'SHORT' else '⚪'
        }
        
        return signal_data
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check bot status."""
        status_message = (
            f"🤖 <b>Bot Status</b> 🤖\n\n"
            f"<b>Status:</b> 🟢 RUNNING\n"
            f"<b>Mode:</b> {'🔴 TEST MODE' if config.TEST_MODE else '🟢 LIVE'}\n"
            f"<b>Pairs:</b> {len(config.TRADING_PAIRS)}\n"
            f"<b>Uptime:</b> Basic version deployed\n\n"
            f"<i>Technical analysis features coming soon!</i>"
        )
        await update.message.reply_html(status_message)
    
    def run(self):
        """Start the bot."""
        if not config.BOT_TOKEN or config.BOT_TOKEN == 'your_bot_token_here':
            logger.error("❌ BOT_TOKEN not set! Please add it in Render environment variables.")
            return
        
        # Create Application
        self.app = Application.builder().token(config.BOT_TOKEN).build()
        
        # Add command handlers
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("signal", self.get_signal))
        self.app.add_handler(CommandHandler("status", self.status))
        
        # Log bot info
        logger.info("🤖 Trading Bot Started!")
        logger.info(f"📊 Monitoring pairs: {', '.join(config.TRADING_PAIRS)}")
        logger.info(f"⏰ Timeframe: {config.TIMEFRAME}")
        logger.info(f"🔧 Mode: {'TEST' if config.TEST_MODE else 'LIVE'}")
        logger.info("🚀 Basic version - Technical analysis coming soon!")
        
        # Start the Bot
        self.app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    bot = TradingBot()
    bot.run()

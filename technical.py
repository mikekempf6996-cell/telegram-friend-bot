import pandas as pd
import numpy as np
from ta.trend import MACD, SMAIndicator, EMAIndicator, PSARIndicator, IchimokuIndicator
from ta.momentum import RSIIndicator, StochasticOscillator, WilliamsRIndicator, StochRSIIndicator
from ta.volume import OnBalanceVolumeIndicator
from ta.volatility import BollingerBands
from ta.others import DailyReturnIndicator
import config

class TechnicalAnalyzer:
    def __init__(self):
        self.indicators_config = config.INDICATORS
    
    def calculate_all_indicators(self, df):
        """
        Calculate all technical indicators for the given DataFrame
        """
        if len(df) < 50:  # Ensure enough data
            return df
        
        # Moving Averages
        for period in self.indicators_config['MA']:
            df[f'MA_{period}'] = SMAIndicator(close=df['close'], window=period).sma_indicator()
        
        # Exponential Moving Averages
        for period in self.indicators_config['EMA']:
            df[f'EMA_{period}'] = EMAIndicator(close=df['close'], window=period).ema_indicator()
        
        # Bollinger Bands
        bb_config = self.indicators_config['BOLL']
        bb = BollingerBands(close=df['close'], window=bb_config['window'], window_dev=bb_config['window_dev'])
        df['BB_upper'] = bb.bollinger_hband()
        df['BB_middle'] = bb.bollinger_mavg()
        df['BB_lower'] = bb.bollinger_lband()
        df['BB_width'] = bb.bollinger_wband()
        
        # Parabolic SAR
        sar_config = self.indicators_config['SAR']
        df['SAR'] = PSARIndicator(
            high=df['high'], 
            low=df['low'], 
            close=df['close'],
            step=sar_config['acceleration'],
            max_step=sar_config['maximum']
        ).psar()
        
        # MACD
        macd_config = self.indicators_config['MACD']
        macd = MACD(
            close=df['close'],
            window_fast=macd_config['fast'],
            window_slow=macd_config['slow'],
            window_sign=macd_config['signal']
        )
        df['MACD'] = macd.macd()
        df['MACD_signal'] = macd.macd_signal()
        df['MACD_histogram'] = macd.macd_diff()
        
        # RSI
        rsi_period = self.indicators_config['RSI']
        df['RSI'] = RSIIndicator(close=df['close'], window=rsi_period).rsi()
        
        # KDJ (Stochastic Oscillator)
        kdj_period = self.indicators_config['KDJ']
        stoch = StochasticOscillator(high=df['high'], low=df['low'], close=df['close'], window=kdj_period)
        df['K'] = stoch.stoch()
        df['D'] = stoch.stoch_signal()
        df['J'] = 3 * df['K'] - 2 * df['D']
        
        # OBV (On Balance Volume)
        df['OBV'] = OnBalanceVolumeIndicator(close=df['close'], volume=df['volume']).on_balance_volume()
        
        # Williams %R
        wr_period = self.indicators_config['WR']
        df['WR'] = WilliamsRIndicator(high=df['high'], low=df['low'], close=df['close'], lbp=wr_period).williams_r()
        
        # Stochastic RSI
        stoch_rsi_period = self.indicators_config['STOCH_RSI']
        stoch_rsi = StochRSIIndicator(close=df['close'], window=stoch_rsi_period)
        df['Stoch_RSI'] = stoch_rsi.stochrsi()
        
        return df
    
    def generate_signal(self, df):
        """
        Generate trading signal based on all indicators
        Returns: 'LONG', 'SHORT', or 'NEUTRAL'
        """
        if len(df) < 2:
            return 'NEUTRAL'
        
        latest = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Initialize signal strengths
        long_signals = 0
        short_signals = 0
        
        # Trend Analysis (MA/EMA)
        if 'MA_5' in df.columns and 'MA_20' in df.columns:
            if latest['MA_5'] > latest['MA_20'] and previous['MA_5'] <= previous['MA_20']:
                long_signals += 1
            elif latest['MA_5'] < latest['MA_20'] and previous['MA_5'] >= previous['MA_20']:
                short_signals += 1
        
        # MACD Signal
        if 'MACD' in df.columns and 'MACD_signal' in df.columns:
            if latest['MACD'] > latest['MACD_signal'] and previous['MACD'] <= previous['MACD_signal']:
                long_signals += 1
            elif latest['MACD'] < latest['MACD_signal'] and previous['MACD'] >= previous['MACD_signal']:
                short_signals += 1
        
        # RSI Signals
        if 'RSI' in df.columns:
            if latest['RSI'] < 30:  # Oversold
                long_signals += 1
            elif latest['RSI'] > 70:  # Overbought
                short_signals += 1
        
        # Bollinger Bands
        if 'BB_lower' in df.columns and 'BB_upper' in df.columns:
            if latest['close'] <= latest['BB_lower']:
                long_signals += 1
            elif latest['close'] >= latest['BB_upper']:
                short_signals += 1
        
        # KDJ Signals
        if 'K' in df.columns and 'D' in df.columns:
            if latest['K'] < 20 and latest['D'] < 20:  # Oversold
                long_signals += 1
            elif latest['K'] > 80 and latest['D'] > 80:  # Overbought
                short_signals += 1
        
        # Generate final signal
        if long_signals >= 3 and long_signals > short_signals:
            return 'LONG'
        elif short_signals >= 3 and short_signals > long_signals:
            return 'SHORT'
        else:
            return 'NEUTRAL'

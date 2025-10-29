import pandas as pd
import numpy as np
from ta.trend import MACD, SMAIndicator, EMAIndicator, PSARIndicator
from ta.momentum import RSIIndicator, StochasticOscillator, WilliamsRIndicator, StochRSIIndicator
from ta.volume import OnBalanceVolumeIndicator
from ta.volatility import BollingerBands

class TechnicalAnalyzer:
    def __init__(self):
        self.indicators_config = {
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
    
    def calculate_all_indicators(self, df):
        """Calculate all technical indicators"""
        if len(df) < 50:
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
        
        # Parabolic SAR
        sar_config = self.indicators_config['SAR']
        df['SAR'] = PSARIndicator(high=df['high'], low=df['low'], close=df['close']).psar()
        
        # MACD
        macd_config = self.indicators_config['MACD']
        macd = MACD(close=df['close'], window_fast=macd_config['fast'], window_slow=macd_config['slow'], window_sign=macd_config['signal'])
        df['MACD'] = macd.macd()
        df['MACD_signal'] = macd.macd_signal()
        df['MACD_histogram'] = macd.macd_diff()
        
        # RSI
        df['RSI'] = RSIIndicator(close=df['close'], window=self.indicators_config['RSI']).rsi()
        
        # KDJ (Stochastic)
        stoch = StochasticOscillator(high=df['high'], low=df['low'], close=df['close'], window=self.indicators_config['KDJ'])
        df['K'] = stoch.stoch()
        df['D'] = stoch.stoch_signal()
        
        # OBV
        df['OBV'] = OnBalanceVolumeIndicator(close=df['close'], volume=df['volume']).on_balance_volume()
        
        # Williams %R
        df['WR'] = WilliamsRIndicator(high=df['high'], low=df['low'], close=df['close'], lbp=self.indicators_config['WR']).williams_r()
        
        # Stochastic RSI
        df['Stoch_RSI'] = StochRSIIndicator(close=df['close'], window=self.indicators_config['STOCH_RSI']).stochrsi()
        
        return df
    
    def generate_signal(self, df):
        """Generate trading signal based on all indicators"""
        if len(df) < 2:
            return 'NEUTRAL', 0
        
        latest = df.iloc[-1]
        previous = df.iloc[-2]
        
        long_signals = 0
        short_signals = 0
        
        # Trend Analysis
        if latest['EMA_5'] > latest['EMA_20']:
            long_signals += 1
        else:
            short_signals += 1
        
        # MACD Signal
        if latest['MACD'] > latest['MACD_signal']:
            long_signals += 1
        else:
            short_signals += 1
        
        # RSI Signals
        if latest['RSI'] < 30:
            long_signals += 1
        elif latest['RSI'] > 70:
            short_signals += 1
        
        # Bollinger Bands
        if latest['close'] <= latest['BB_lower']:
            long_signals += 1
        elif latest['close'] >= latest['BB_upper']:
            short_signals += 1
        
        # Generate final signal
        if long_signals >= 3:
            return 'LONG', long_signals
        elif short_signals >= 3:
            return 'SHORT', short_signals
        else:
            return 'NEUTRAL', 0

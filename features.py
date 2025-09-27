import pandas as pd
import numpy as np
import talib

class TechnicalFeatures:
    def __init__(self):
        self.features = []
    
    def calculate_all_indicators(self, df):
        """Calculate comprehensive technical indicators"""
        data = df.copy()
        
        # Basic price features
        data['returns'] = data['close'].pct_change()
        data['log_returns'] = np.log(data['close'] / data['close'].shift(1))
        
        # Moving Averages
        for period in [7, 14, 21, 50, 100, 200]:
            data[f'sma_{period}'] = data['close'].rolling(period).mean()
            data[f'ema_{period}'] = data['close'].ewm(span=period).mean()
            
            # MA ratios
            data[f'close_sma_{period}_ratio'] = data['close'] / data[f'sma_{period}']
            data[f'sma_{period}_slope'] = data[f'sma_{period}'].diff() / data[f'sma_{period}'].shift(1)
        
        # RSI for multiple periods
        for period in [7, 14, 21]:
            data[f'rsi_{period}'] = talib.RSI(data['close'].values, timeperiod=period)
        
        # MACD
        exp1 = data['close'].ewm(span=12).mean()
        exp2 = data['close'].ewm(span=26).mean()
        data['macd'] = exp1 - exp2
        data['macd_signal'] = data['macd'].ewm(span=9).mean()
        data['macd_histogram'] = data['macd'] - data['macd_signal']
        
        # Bollinger Bands
        data['bb_middle'] = data['close'].rolling(20).mean()
        bb_std = data['close'].rolling(20).std()
        data['bb_upper'] = data['bb_middle'] + (bb_std * 2)
        data['bb_lower'] = data['bb_middle'] - (bb_std * 2)
        data['bb_width'] = data['bb_upper'] - data['bb_lower']
        data['bb_position'] = (data['close'] - data['bb_lower']) / (data['bb_upper'] - data['bb_lower'])
        
        # Stochastic Oscillator
        data['stoch_k'] = talib.STOCHK(data['high'].values, data['low'].values, 
                                       data['close'].values, fastk_period=14)
        data['stoch_d'] = talib.STOCHD(data['high'].values, data['low'].values, 
                                       data['close'].values, fastk_period=14, 
                                       slowk_period=3, slowd_period=3)
        
        # Williams %R
        data['williams_r'] = talib.WILLR(data['high'].values, data['low'].values, 
                                         data['close'].values, timeperiod=14)
        
        # Average True Range (ATR)
        data['atr'] = talib.ATR(data['high'].values, data['low'].values, 
                                data['close'].values, timeperiod=14)
        data['atr_ratio'] = data['atr'] / data['close']
        
        # Volume indicators
        data['volume_sma'] = data['volume'].rolling(20).mean()
        data['volume_ratio'] = data['volume'] / data['volume_sma']
        
        # Price momentum
        for period in [1, 3, 5, 10]:
            data[f'momentum_{period}'] = data['close'] / data['close'].shift(period) - 1
        
        # Volatility measures
        for period in [5, 10, 20]:
            data[f'volatility_{period}'] = data['returns'].rolling(period).std()
        
        # Support and Resistance levels
        data['support'] = data['low'].rolling(20).min()
        data['resistance'] = data['high'].rolling(20).max()
        data['support_distance'] = (data['close'] - data['support']) / data['close']
        data['resistance_distance'] = (data['resistance'] - data['close']) / data['close']
        
        # Market microstructure (if available)
        data['hl_ratio'] = (data['high'] - data['low']) / data['close']
        data['oc_ratio'] = (data['close'] - data['open']) / data['close']
        
        return data
    
    def create_target_variable(self, df, prediction_horizon=1, threshold=0.001):
        """
        Create target variable for classification
        
        Parameters:
        - prediction_horizon: Hours ahead to predict
        - threshold: Minimum movement percentage to consider as signal
        """
        data = df.copy()
        
        # Calculate future returns
        data['future_return'] = data['close'].shift(-prediction_horizon) / data['close'] - 1
        
        # Create categorical target
        conditions = [
            data['future_return'] > threshold,   # Buy signal
            data['future_return'] < -threshold,  # Sell signal
        ]
        choices = [1, -1]  # 1=Buy, -1=Sell, 0=Hold
        
        data['target'] = np.select(conditions, choices, default=0)
        
        return data
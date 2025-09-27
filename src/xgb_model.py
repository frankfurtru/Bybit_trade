import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from typing import Dict, List, Tuple, Optional, Literal
import logging
import os
import pickle

logger = logging.getLogger(__name__)

MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "enhanced_xgb_model.pkl")

def ensure_model_dir():
    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR, exist_ok=True)

def custom_win_rate_eval(preds, dtrain):
    """
    Custom evaluation function untuk maximize win rate
    """
    labels = dtrain.get_label()
    preds_binary = (preds > 0.5).astype(int)
    win_rate = np.mean(preds_binary == labels)
    return 'win_rate', win_rate

class XGBTradingModel:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        
        # Optimized XGBoost parameters berdasarkan spesifikasi
        self.params = {
            # 1. Objective Function (binary classification untuk buy/sell signals)
            'objective': 'binary:logistic',
            
            # 4. Parameter Hyperparameter
            'eta': 0.05,                    # learning rate, trade-off konvergensi
            'max_depth': 6,                 # kedalaman tree, hindari overfitting
            'min_child_weight': 10,         # min. sum of hessians per leaf
            'gamma': 1.0,                   # min. loss reduction untuk split
            'lambda': 1.5,                  # L2 regularization weight
            'alpha': 0.0,                   # L1 regularization weight
            'subsample': 0.8,               # sampling untuk row per tree
            'colsample_bytree': 0.7,        # sampling column per tree
            'colsample_bylevel': 0.7,       # sampling column tiap level
            'scale_pos_weight': 1.2,        # imbalance correction untuk buy/sell
            'eval_metric': 'aucpr',         # priority precision-recall area
            
            'random_state': 42,
            'verbosity': 0,
            'tree_method': 'hist',          # faster training
            'grow_policy': 'lossguide'      # more efficient tree growth
        }
        
        # 5. Early Stopping & Validation
        self.early_stopping_rounds = 50
    
    def prepare_features(self, data: pd.DataFrame) -> np.ndarray:
        """
        Prepare technical indicators as features dengan enhanced indicators
        """
        if 'close' not in data.columns:
            raise ValueError("Data must contain 'close' column")
            
        close = data['close'].copy()
        high = data.get('high', close).copy()
        low = data.get('low', close).copy()
        volume = data.get('volume', pd.Series(index=close.index, data=1)).copy()
        
        # Price-based features
        data['returns'] = close.pct_change()
        data['returns_ma'] = data['returns'].rolling(5).mean()
        data['log_returns'] = np.log(close / close.shift(1))
        
        # Moving averages dengan berbagai periode
        data['ema_5'] = close.ewm(span=5).mean()
        data['ema_21'] = close.ewm(span=21).mean()
        data['ema_50'] = close.ewm(span=50).mean()
        data['ema_ratio_5_21'] = data['ema_5'] / data['ema_21']
        data['ema_ratio_21_50'] = data['ema_21'] / data['ema_50']
        
        # Volatility indicators
        data['volatility_5'] = data['returns'].rolling(5).std()
        data['volatility_21'] = data['returns'].rolling(21).std()
        data['volatility_ratio'] = data['volatility_5'] / data['volatility_21']
        
        # RSI dengan multiple periods
        def calculate_rsi(prices, period=14):
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))
            
        data['rsi_14'] = calculate_rsi(close, 14)
        data['rsi_7'] = calculate_rsi(close, 7)
        data['rsi_divergence'] = data['rsi_14'] - data['rsi_7']
        
        # MACD
        ema_12 = close.ewm(span=12).mean()
        ema_26 = close.ewm(span=26).mean()
        data['macd'] = ema_12 - ema_26
        data['macd_signal'] = data['macd'].ewm(span=9).mean()
        data['macd_histogram'] = data['macd'] - data['macd_signal']
        
        # Bollinger Bands
        ma_20 = close.rolling(20).mean()
        std_20 = close.rolling(20).std()
        data['bb_upper'] = ma_20 + (2 * std_20)
        data['bb_lower'] = ma_20 - (2 * std_20)
        data['bb_position'] = (close - data['bb_lower']) / (data['bb_upper'] - data['bb_lower'])
        data['bb_width'] = (data['bb_upper'] - data['bb_lower']) / ma_20
        
        # Price position indicators
        data['price_vs_ma_20'] = close / ma_20
        data['high_low_ratio'] = (close - low) / (high - low)
        
        # Volume indicators
        data['volume_sma'] = volume.rolling(10).mean()
        data['volume_ratio'] = volume / data['volume_sma']
        data['price_volume'] = data['returns'] * data['volume_ratio']
        
        # Momentum indicators
        data['momentum_3'] = close / close.shift(3)
        data['momentum_5'] = close / close.shift(5)
        data['momentum_10'] = close / close.shift(10)
        
        # Support/Resistance levels
        data['support_level'] = low.rolling(10).min()
        data['resistance_level'] = high.rolling(10).max()
        data['support_distance'] = (close - data['support_level']) / close
        data['resistance_distance'] = (data['resistance_level'] - close) / close
        
        # Select feature columns
        feature_columns = [
            'returns', 'returns_ma', 'log_returns',
            'ema_ratio_5_21', 'ema_ratio_21_50',
            'volatility_ratio',
            'rsi_14', 'rsi_7', 'rsi_divergence',
            'macd', 'macd_histogram',
            'bb_position', 'bb_width', 'price_vs_ma_20',
            'high_low_ratio', 'volume_ratio', 'price_volume',
            'momentum_3', 'momentum_5', 'momentum_10',
            'support_distance', 'resistance_distance'
        ]
        
        # Remove NaN values and return
        data_clean = data[feature_columns].dropna()
        return data_clean.values
    
    def create_labels(self, data: pd.DataFrame, forward_periods: int = 3) -> np.ndarray:
        """
        Create binary labels berdasarkan future price movement
        1 = price goes up significantly, 0 = otherwise
        """
        if 'close' not in data.columns:
            raise ValueError("Data must contain 'close' column")
            
        close = data['close']
        
        # Calculate future returns dengan threshold
        future_returns = close.shift(-forward_periods) / close - 1
        
        # Dynamic threshold berdasarkan volatility
        volatility = close.pct_change().rolling(20).std()
        threshold = volatility * 0.5  # 0.5x volatility sebagai threshold
        
        # Label: 1 jika return > threshold, 0 otherwise
        labels = (future_returns > threshold).astype(int)
        
        return labels.values
    
    def train(self, data: pd.DataFrame, prediction_mode: Literal["xgboost", "ai_hybrid"] = "xgboost") -> Dict:
        """
        Train the XGBoost model dengan win-rate optimization
        """
        try:
            # Prepare features and labels
            features = self.prepare_features(data)
            labels = self.create_labels(data)
            
            if len(features) == 0 or len(labels) == 0:
                raise ValueError("No features or labels generated from data")
            
            # Align features and labels (remove NaN rows)
            min_len = min(len(features), len(labels))
            features = features[-min_len:]
            labels = labels[-min_len:]
            
            # Remove rows where labels are NaN
            valid_mask = ~np.isnan(labels)
            features = features[valid_mask]
            labels = labels[valid_mask]
            
            if len(features) < 100:
                raise ValueError("Insufficient data for training (need at least 100 samples)")
            
            # Scale features
            features_scaled = self.scaler.fit_transform(features)
            
            # Split data dengan stratification
            X_train, X_val, y_train, y_val = train_test_split(
                features_scaled, labels, test_size=0.2, random_state=42, stratify=labels
            )
            
            # Create DMatrix
            dtrain = xgb.DMatrix(X_train, label=y_train)
            dval = xgb.DMatrix(X_val, label=y_val)
            
            # 5. Early Stopping & Validation
            eval_set = [(dtrain, 'train'), (dval, 'validation')]
            
            # Train model dengan custom evaluation
            self.model = xgb.train(
                params=self.params,
                dtrain=dtrain,
                num_boost_round=1000,
                evals=eval_set,
                early_stopping_rounds=self.early_stopping_rounds,
                feval=custom_win_rate_eval,
                maximize=True,
                verbose_eval=False
            )
            
            self.is_trained = True
            
            # Calculate comprehensive metrics
            train_preds = self.model.predict(dtrain)
            val_preds = self.model.predict(dval)
            
            train_acc = np.mean((train_preds > 0.5) == y_train)
            val_acc = np.mean((val_preds > 0.5) == y_val)
            
            # Win rate calculation
            train_win_rate = np.mean((train_preds > 0.5) == y_train)
            val_win_rate = np.mean((val_preds > 0.5) == y_val)
            
            # Feature importance
            importance = self.model.get_score(importance_type='weight')
            
            # Save model
            self.save_model()
            
            return {
                'status': 'success',
                'mode': prediction_mode,
                'train_accuracy': round(train_acc, 4),
                'val_accuracy': round(val_acc, 4),
                'train_win_rate': round(train_win_rate, 4),
                'val_win_rate': round(val_win_rate, 4),
                'samples_used': len(features),
                'feature_importance': dict(sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10])
            }
            
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def predict(self, data: pd.DataFrame, prediction_mode: Literal["xgboost", "ai_hybrid"] = "xgboost") -> Dict:
        """
        Make predictions menggunakan trained model dengan mode selection
        """
        if not self.is_trained:
            return {
                'status': 'error',
                'message': 'Model not trained yet'
            }
        
        try:
            # Prepare features
            features = self.prepare_features(data)
            if len(features) == 0:
                raise ValueError("No features could be generated from data")
            
            # Use last row for prediction
            features_scaled = self.scaler.transform(features[-1:])
            
            # XGBoost prediction
            dtest = xgb.DMatrix(features_scaled)
            xgb_prediction = self.model.predict(dtest)[0]
            
            if prediction_mode == "xgboost":
                # Pure XGBoost prediction
                signal = 'BUY' if xgb_prediction > 0.5 else 'SELL'
                confidence = xgb_prediction if xgb_prediction > 0.5 else (1 - xgb_prediction)
                
                return {
                    'status': 'success',
                    'mode': 'xgboost',
                    'signal': signal,
                    'confidence': round(confidence, 3),
                    'probability': round(xgb_prediction, 3),
                    'reasoning': f"XGBoost model prediction based on {len(features_scaled[0])} technical indicators"
                }
                
            elif prediction_mode == "ai_hybrid":
                # Hybrid: XGBoost + AI reasoning
                # Get current market conditions
                current_data = data.iloc[-1]
                
                # AI reasoning berdasarkan market conditions
                market_conditions = self._analyze_market_conditions(data)
                
                # Combine XGBoost dengan market analysis
                final_confidence = (xgb_prediction * 0.7) + (market_conditions['confidence'] * 0.3)
                final_signal = 'BUY' if final_confidence > 0.5 else 'SELL'
                
                return {
                    'status': 'success',
                    'mode': 'ai_hybrid',
                    'signal': final_signal,
                    'confidence': round(final_confidence, 3),
                    'xgb_probability': round(xgb_prediction, 3),
                    'market_analysis': market_conditions,
                    'reasoning': f"Hybrid analysis: XGBoost ({xgb_prediction:.3f}) + Market conditions ({market_conditions['confidence']:.3f})"
                }
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _analyze_market_conditions(self, data: pd.DataFrame) -> Dict:
        """
        AI-based market condition analysis untuk hybrid mode
        """
        try:
            close = data['close']
            volume = data.get('volume', pd.Series(index=close.index, data=1))
            
            # Trend analysis
            ema_20 = close.ewm(span=20).mean()
            trend_strength = (close.iloc[-1] - ema_20.iloc[-1]) / ema_20.iloc[-1]
            
            # Momentum analysis
            roc_5 = (close.iloc[-1] / close.iloc[-6] - 1) if len(close) >= 6 else 0
            
            # Volume analysis
            avg_volume = volume.rolling(10).mean().iloc[-1] if len(volume) >= 10 else volume.iloc[-1]
            volume_surge = volume.iloc[-1] / avg_volume if avg_volume > 0 else 1
            
            # Volatility analysis
            returns = close.pct_change()
            volatility = returns.rolling(10).std().iloc[-1] if len(returns) >= 10 else 0
            
            # Scoring system
            score = 0.5  # neutral start
            
            # Trend component (±0.2)
            if trend_strength > 0.02:
                score += 0.2
            elif trend_strength < -0.02:
                score -= 0.2
            
            # Momentum component (±0.15)
            if roc_5 > 0.01:
                score += 0.15
            elif roc_5 < -0.01:
                score -= 0.15
            
            # Volume component (±0.1)
            if volume_surge > 1.5:
                score += 0.1
            elif volume_surge < 0.7:
                score -= 0.1
            
            # Volatility adjustment (±0.05)
            if volatility > 0.05:  # high volatility = more uncertainty
                score *= 0.95
            
            return {
                'confidence': max(0, min(1, score)),
                'trend_strength': round(trend_strength, 4),
                'momentum': round(roc_5, 4),
                'volume_surge': round(volume_surge, 2),
                'volatility': round(volatility, 4)
            }
            
        except Exception as e:
            return {
                'confidence': 0.5,
                'error': str(e)
            }
    
    def save_model(self, path: str = MODEL_PATH) -> None:
        """Save trained model"""
        ensure_model_dir()
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'is_trained': self.is_trained,
            'params': self.params
        }
        with open(path, "wb") as f:
            pickle.dump(model_data, f)
    
    def load_model(self, path: str = MODEL_PATH) -> bool:
        """Load trained model"""
        if not os.path.exists(path):
            return False
        try:
            with open(path, "rb") as f:
                model_data = pickle.load(f)
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.is_trained = model_data['is_trained']
            self.params = model_data.get('params', self.params)
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

# Legacy compatibility functions
def train_quick(X: pd.DataFrame, y: pd.Series) -> XGBTradingModel:
    """Legacy compatibility function"""
    model = XGBTradingModel()
    data = X.copy()
    data['close'] = y  # Simulate close prices for labels
    model.train(data)
    return model

def save_model(model: XGBTradingModel, path: str = MODEL_PATH) -> None:
    """Legacy compatibility function"""
    model.save_model(path)

def load_model(path: str = MODEL_PATH) -> XGBTradingModel | None:
    """Legacy compatibility function"""
    model = XGBTradingModel()
    if model.load_model(path):
        return model
    return None


def predict_proba(model: XGBClassifier, X_last: pd.DataFrame) -> float:
    proba = model.predict_proba(X_last.values.reshape(1, -1))[0, 1]
    return float(proba)


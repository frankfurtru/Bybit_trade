import numpy as np
import pandas as pd

class EnsembleTradingStrategy:
    def __init__(self, model, initial_capital=10000, risk_per_trade=0.02):
        self.model = model
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        
        self.positions = []
        self.trades = []
        self.performance_metrics = {}
    
    def calculate_position_size(self, signal_confidence, current_price, stop_loss_pct=0.02):
        """Calculate position size based on Kelly Criterion and risk management"""
        # Risk amount per trade
        risk_amount = self.current_capital * self.risk_per_trade
        
        # Position size based on stop loss
        stop_loss_amount = current_price * stop_loss_pct
        position_size = risk_amount / stop_loss_amount
        
        # Adjust by signal confidence
        position_size *= signal_confidence
        
        # Maximum position size (e.g., 10% of capital)
        max_position_value = self.current_capital * 0.1
        max_position_size = max_position_value / current_price
        
        return min(position_size, max_position_size)
    
    def backtest_strategy(self, df, start_date=None, end_date=None):
        """Backtest the ensemble trading strategy"""
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]
        
        portfolio_value = [self.initial_capital]
        signals = []
        
        for i in range(100, len(df)):  # Start after enough data for indicators
            current_data = df.iloc[:i+1]
            
            # Get prediction
            try:
                predictions = self.model.predict_signal(current_data)
                signal = predictions['stacking']
                confidence = max(predictions['stacking_proba'])
                
                current_price = df.iloc[i]['close']
                
                # Generate trading signal
                if signal == 1 and confidence > 0.6:  # Strong buy signal
                    action = 'BUY'
                    size = self.calculate_position_size(confidence, current_price)
                elif signal == -1 and confidence > 0.6:  # Strong sell signal
                    action = 'SELL'
                    size = self.calculate_position_size(confidence, current_price)
                else:
                    action = 'HOLD'
                    size = 0
                
                signals.append({
                    'timestamp': df.index[i],
                    'price': current_price,
                    'signal': signal,
                    'confidence': confidence,
                    'action': action,
                    'size': size
                })
                
                # Update portfolio value (simplified)
                if action in ['BUY', 'SELL']:
                    # Calculate returns based on next period
                    if i < len(df) - 1:
                        next_price = df.iloc[i+1]['close']
                        if action == 'BUY':
                            return_pct = (next_price - current_price) / current_price
                        else:  # SELL
                            return_pct = (current_price - next_price) / current_price
                        
                        trade_return = return_pct * size * current_price
                        self.current_capital += trade_return
                
                portfolio_value.append(self.current_capital)
                
            except Exception as e:
                print(f"Error in backtesting at index {i}: {e}")
                signals.append({
                    'timestamp': df.index[i],
                    'price': current_price,
                    'signal': 0,
                    'confidence': 0,
                    'action': 'HOLD',
                    'size': 0
                })
                portfolio_value.append(self.current_capital)
        
        # Calculate performance metrics
        self.calculate_performance_metrics(portfolio_value, df)
        
        return signals, portfolio_value
    
    def calculate_performance_metrics(self, portfolio_values, df):
        """Calculate comprehensive performance metrics"""
        returns = pd.Series(portfolio_values).pct_change().dropna()
        
        # Basic metrics
        total_return = (portfolio_values[-1] - portfolio_values[0]) / portfolio_values[0]
        annualized_return = (1 + total_return) ** (365.25 / len(df)) - 1
        
        # Risk metrics
        volatility = returns.std() * np.sqrt(365.25)  # Annualized
        sharpe_ratio = (annualized_return) / volatility if volatility > 0 else 0
        
        # Drawdown analysis
        portfolio_series = pd.Series(portfolio_values)
        rolling_max = portfolio_series.expanding().max()
        drawdown = (portfolio_series - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        self.performance_metrics = {
            'Total Return': f"{total_return:.2%}",
            'Annualized Return': f"{annualized_return:.2%}",
            'Volatility': f"{volatility:.2%}",
            'Sharpe Ratio': f"{sharpe_ratio:.2f}",
            'Max Drawdown': f"{max_drawdown:.2%}",
            'Final Portfolio Value': f"${portfolio_values[-1]:,.2f}"
        }
        
        print("\n=== PERFORMANCE METRICS ===")
        for metric, value in self.performance_metrics.items():
            print(f"{metric}: {value}")

import numpy as np
from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier,
    StackingClassifier,
    VotingClassifier,
)
from sklearn.model_selection import TimeSeriesSplit, cross_val_score, RandomizedSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report
import xgboost as xgb

class EnsembleTradingModel:
    def __init__(self, random_state=42, model_params=None):
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.feature_columns = None
        self.models = {}

        if model_params is None:
            model_params = {
                'rf': {'n_estimators': 200, 'max_depth': 10, 'min_samples_split': 5, 'min_samples_leaf': 2},
                'xgb': {'n_estimators': 200, 'max_depth': 6, 'learning_rate': 0.1, 'subsample': 0.8, 'colsample_bytree': 0.8},
                'gb': {'n_estimators': 200, 'max_depth': 6, 'learning_rate': 0.1, 'subsample': 0.8},
                'meta_learner': {'n_estimators': 50, 'max_depth': 3}
            }

        # Initialize base models with dynamic parameters
        self.base_models = [
            ('rf', RandomForestClassifier(
                random_state=random_state,
                n_jobs=-1,
                **model_params.get('rf', {})
            )),
            ('xgb', xgb.XGBClassifier(
                random_state=random_state,
                n_jobs=-1,
                **model_params.get('xgb', {})
            )),
            ('gb', GradientBoostingClassifier(
                random_state=random_state,
                **model_params.get('gb', {})
            ))
        ]
        
        # Meta-learner (final estimator)
        self.meta_learner = RandomForestClassifier(
            random_state=random_state,
            **model_params.get('meta_learner', {})
        )
        
        # Create stacking ensemble
        self.ensemble_model = StackingClassifier(
            estimators=self.base_models,
            final_estimator=self.meta_learner,
            cv=3,  # 3-fold cross-validation
            stack_method='predict_proba',
            n_jobs=-1
        )
        
        # Voting ensemble (alternative approach)
        self.voting_model = VotingClassifier(
            estimators=self.base_models,
            voting='soft',  # Use probability voting
            n_jobs=-1
        )
    
    def prepare_features(self, df):
        """Prepare and select features for training"""
        # Remove non-feature columns
        exclude_cols = ['target', 'future_return', 'open', 'high', 'low', 'close', 'volume', 'turnover']
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        # Remove columns with too many NaN values
        valid_cols = []
        for col in feature_cols:
            if df[col].notna().sum() / len(df) > 0.7:  # At least 70% valid data
                valid_cols.append(col)
        
        self.feature_columns = valid_cols
        print(f"Selected {len(self.feature_columns)} features")
        
        # Prepare feature matrix
        X = df[self.feature_columns].fillna(method='ffill').fillna(method='bfill')
        
        return X
    
    def train_models(self, df, test_size=0.2):
        """Train ensemble models"""
        # Prepare features and target
        X = self.prepare_features(df)
        y = df['target'].values
        
        # Remove rows where target is NaN
        valid_idx = ~np.isnan(y)
        X = X[valid_idx]
        y = y[valid_idx]
        
        # Time series split to maintain temporal order
        tscv = TimeSeriesSplit(n_splits=5)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Split data
        split_idx = int(len(X_scaled) * (1 - test_size))
        X_train, X_test = X_scaled[:split_idx], X_scaled[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        print("Training models...")
        
        # Train individual models
        for name, model in self.base_models:
            print(f"Training {name}...")
            model.fit(X_train, y_train)
            
            # Cross-validation score
            cv_scores = cross_val_score(model, X_train, y_train, cv=tscv, scoring='accuracy')
            print(f"{name} CV Score: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")
            
            self.models[name] = model
        
        # Train ensemble models
        print("Training Stacking Ensemble...")
        self.ensemble_model.fit(X_train, y_train)
        
        print("Training Voting Ensemble...")
        self.voting_model.fit(X_train, y_train)
        
        # Evaluate models
        self.evaluate_models(X_test, y_test)
        
        return X_train, X_test, y_train, y_test
    
    def evaluate_models(self, X_test, y_test):
        """Evaluate all models"""
        results = {}
        
        # Test individual models
        for name, model in self.models.items():
            y_pred = model.predict(X_test)
            accuracy = np.mean(y_pred == y_test)
            results[name] = accuracy
            print(f"{name} Test Accuracy: {accuracy:.4f}")
        
        # Test ensemble models
        stacking_pred = self.ensemble_model.predict(X_test)
        stacking_accuracy = np.mean(stacking_pred == y_test)
        results['stacking'] = stacking_accuracy
        print(f"Stacking Ensemble Accuracy: {stacking_accuracy:.4f}")
        
        voting_pred = self.voting_model.predict(X_test)
        voting_accuracy = np.mean(voting_pred == y_test)
        results['voting'] = voting_accuracy
        print(f"Voting Ensemble Accuracy: {voting_accuracy:.4f}")
        
        # Detailed report for best model
        best_model_name = max(results, key=results.get)
        print(f"\nBest Model: {best_model_name}")
        
        if best_model_name == 'stacking':
            best_pred = stacking_pred
        elif best_model_name == 'voting':
            best_pred = voting_pred
        else:
            best_pred = self.models[best_model_name].predict(X_test)
        
        print("\nClassification Report:")
        print(classification_report(y_test, best_pred))
        
        return results
    
    def predict_signal(self, current_data):
        """Generate trading signal for current market data"""
        # Prepare features
        X = current_data[self.feature_columns].fillna(method='ffill').fillna(method='bfill')
        X_scaled = self.scaler.transform(X.iloc[[-1]])  # Get latest data point
        
        # Get predictions from all models
        predictions = {}
        predictions['stacking'] = self.ensemble_model.predict(X_scaled)[0]
        predictions['stacking_proba'] = self.ensemble_model.predict_proba(X_scaled)[0]
        
        predictions['voting'] = self.voting_model.predict(X_scaled)[0]
        predictions['voting_proba'] = self.voting_model.predict_proba(X_scaled)[0]
        
        for name, model in self.models.items():
            predictions[name] = model.predict(X_scaled)[0]
            predictions[f'{name}_proba'] = model.predict_proba(X_scaled)[0]
        
        return predictions


class ModelOptimizer:
    def __init__(self, model):
        self.model = model
    
    def optimize_hyperparameters(self, X_train, y_train):
        """Optimize hyperparameters using random search"""
        from sklearn.model_selection import RandomizedSearchCV
        
        # Parameter grid for Random Forest
        rf_param_grid = {
            'rf__n_estimators': [100, 200, 300, 500],
            'rf__max_depth': [5, 10, 15, 20, None],
            'rf__min_samples_split': [2, 5, 10],
            'rf__min_samples_leaf': [1, 2, 4],
            'rf__max_features': ['sqrt', 'log2', 0.5, 0.8]
        }
        
        # Parameter grid for XGBoost
        xgb_param_grid = {
            'xgb__n_estimators': [100, 200, 300],
            'xgb__max_depth': [3, 6, 9],
            'xgb__learning_rate': [0.01, 0.1, 0.2],
            'xgb__subsample': [0.6, 0.8, 1.0],
            'xgb__colsample_bytree': [0.6, 0.8, 1.0]
        }
        
        # Time series cross-validation
        tscv = TimeSeriesSplit(n_splits=3)
        
        # Random search
        random_search = RandomizedSearchCV(
            estimator=self.model.ensemble_model,
            param_distributions={**rf_param_grid, **xgb_param_grid},
            n_iter=50,
            cv=tscv,
            scoring='accuracy',
            n_jobs=-1,
            random_state=42
        )
        
        print("Optimizing hyperparameters...")
        random_search.fit(X_train, y_train)
        
        print(f"Best parameters: {random_search.best_params_}")
        print(f"Best CV score: {random_search.best_score_:.4f}")
        
        return random_search.best_estimator_
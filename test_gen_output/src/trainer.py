"""Model training module.

This module provides comprehensive training capabilities including
cross-validation, hyperparameter tuning, and model selection.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import time
import json

import numpy as np
from sklearn.model_selection import (
    KFold,
    StratifiedKFold,
    cross_val_score,
    cross_validate,
    train_test_split
)
from sklearn.metrics import get_scorer

from src.model import SklearnClassifierWrapper, ModelError

logger = logging.getLogger(__name__)


class TrainingError(Exception):
    """Exception raised for training-related errors."""
    pass


class ModelTrainer:
    """Handles model training with cross-validation and hyperparameter tuning.
    
    Provides a comprehensive training pipeline with logging, metrics tracking,
    and model selection capabilities.
    
    Attributes:
        model: The model to train.
        cv_folds: Number of cross-validation folds.
        scoring: Scoring metric(s) for evaluation.
        random_state: Random seed for reproducibility.
    
    Example:
        >>> trainer = ModelTrainer(model, cv_folds=5, scoring='accuracy')
        >>> results = trainer.train(X_train, y_train)
        >>> print(results['mean_score'])
    """
    
    DEFAULT_SCORING = ['accuracy', 'precision_weighted', 'recall_weighted', 'f1_weighted']
    
    def __init__(
        self,
        model: SklearnClassifierWrapper,
        cv_folds: int = 5,
        scoring: Union[str, List[str]] = 'accuracy',
        random_state: int = 42,
        use_stratified: bool = True
    ):
        """Initialize the ModelTrainer.
        
        Args:
            model: Model instance to train.
            cv_folds: Number of cross-validation folds.
            scoring: Scoring metric or list of metrics.
            random_state: Random seed for reproducibility.
            use_stratified: Whether to use stratified K-fold.
        """
        self.model = model
        self.cv_folds = cv_folds
        self.scoring = scoring if isinstance(scoring, list) else [scoring]
        self.random_state = random_state
        self.use_stratified = use_stratified
        
        self._cv_results: Dict[str, Any] = {}
        self._training_history: List[Dict[str, Any]] = []
        self._best_params: Dict[str, Any] = {}
        
        logger.info(
            f"ModelTrainer initialized with {cv_folds}-fold CV, "
            f"scoring: {scoring}"
        )
    
    def _get_cv_splitter(self, y: Optional[np.ndarray] = None):
        """Get the appropriate cross-validation splitter.
        
        Args:
            y: Target array for stratification decision.
            
        Returns:
            Cross-validation splitter.
        """
        if self.use_stratified and y is not None:
            return StratifiedKFold(
                n_splits=self.cv_folds,
                shuffle=True,
                random_state=self.random_state
            )
        return KFold(
            n_splits=self.cv_folds,
            shuffle=True,
            random_state=self.random_state
        )
    
    def cross_validate(
        self,
        X: np.ndarray,
        y: np.ndarray,
        return_estimator: bool = False
    ) -> Dict[str, Any]:
        """Perform cross-validation.
        
        Args:
            X: Feature array.
            y: Target array.
            return_estimator: Whether to return fitted estimators.
            
        Returns:
            Dictionary containing CV results.
        """
        logger.info(f"Starting {self.cv_folds}-fold cross-validation")
        
        cv = self._get_cv_splitter(y)
        
        # Build scoring dictionary
        scoring_dict = {metric: metric for metric in self.scoring}
        
        start_time = time.time()
        
        cv_results = cross_validate(
            self.model.model,
            X, y,
            cv=cv,
            scoring=scoring_dict,
            return_estimator=return_estimator,
            n_jobs=-1
        )
        
        elapsed_time = time.time() - start_time
        
        # Process results
        results = {
            'fit_time': cv_results['fit_time'].tolist(),
            'score_time': cv_results['score_time'].tolist(),
            'total_time': elapsed_time,
            'n_splits': self.cv_folds
        }
        
        # Process each scoring metric
        for metric in self.scoring:
            key = f'test_{metric}'
            if key in cv_results:
                results[f'{metric}_scores'] = cv_results[key].tolist()
                results[f'{metric}_mean'] = float(np.mean(cv_results[key]))
                results[f'{metric}_std'] = float(np.std(cv_results[key]))
        
        if return_estimator:
            results['estimators'] = cv_results['estimator']
        
        self._cv_results = results
        
        # Log summary
        primary_metric = self.scoring[0]
        logger.info(
            f"Cross-validation completed in {elapsed_time:.2f}s - "
            f"{primary_metric}: {results[f'{primary_metric}_mean']:.4f} "
            f"(±{results[f'{primary_metric}_std']:.4f})"
        )
        
        return results
    
    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        use_cross_validation: bool = True
    ) -> Dict[str, Any]:
        """Train the model.
        
        Args:
            X: Training features.
            y: Training targets.
            X_val: Optional validation features.
            y_val: Optional validation targets.
            use_cross_validation: Whether to use cross-validation.
            
        Returns:
            Dictionary containing training results.
        """
        training_start = datetime.now()
        
        results = {
            'start_time': training_start.isoformat(),
            'model_type': self.model.model_type,
            'n_samples': X.shape[0],
            'n_features': X.shape[1]
        }
        
        # Perform cross-validation
        if use_cross_validation:
            cv_results = self.cross_validate(X, y)
            results['cross_validation'] = cv_results
        
        # Fit final model on all training data
        logger.info("Fitting final model on all training data")
        fit_start = time.time()
        self.model.fit(X, y)
        fit_time = time.time() - fit_start
        
        results['fit_time'] = fit_time
        
        # Evaluate on validation set if provided
        if X_val is not None and y_val is not None:
            val_results = self._evaluate_validation(X_val, y_val)
            results['validation'] = val_results
        
        training_end = datetime.now()
        results['end_time'] = training_end.isoformat()
        results['total_time'] = (training_end - training_start).total_seconds()
        
        # Record training history
        self._training_history.append(results)
        
        logger.info(f"Training completed in {results['total_time']:.2f}s")
        
        return results
    
    def _evaluate_validation(
        self,
        X_val: np.ndarray,
        y_val: np.ndarray
    ) -> Dict[str, float]:
        """Evaluate model on validation set.
        
        Args:
            X_val: Validation features.
            y_val: Validation targets.
            
        Returns:
            Dictionary of metric scores.
        """
        from sklearn.metrics import (
            accuracy_score,
            f1_score,
            precision_score,
            recall_score
        )
        
        y_pred = self.model.predict(X_val)
        
        metrics = {
            'accuracy': accuracy_score(y_val, y_pred),
            'precision_weighted': precision_score(y_val, y_pred, average='weighted', zero_division=0),
            'recall_weighted': recall_score(y_val, y_pred, average='weighted', zero_division=0),
            'f1_weighted': f1_score(y_val, y_pred, average='weighted', zero_division=0)
        }
        
        logger.info(f"Validation metrics: {metrics}")
        
        return metrics
    
    def hyperparameter_search(
        self,
        X: np.ndarray,
        y: np.ndarray,
        param_grid: Dict[str, List[Any]],
        search_type: str = 'grid',
        n_iter: int = 50
    ) -> Tuple[Dict[str, Any], float]:
        """Perform hyperparameter search.
        
        Args:
            X: Training features.
            y: Training targets.
            param_grid: Dictionary of parameter ranges to search.
            search_type: Type of search ('grid' or 'random').
            n_iter: Number of iterations for random search.
            
        Returns:
            Tuple of (best_params, best_score).
        """
        from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
        
        logger.info(f"Starting {search_type} search with {len(param_grid)} parameters")
        
        cv = self._get_cv_splitter(y)
        
        search_start = time.time()
        
        if search_type == 'grid':
            search = GridSearchCV(
                self.model.model,
                param_grid,
                cv=cv,
                scoring=self.scoring[0],
                n_jobs=-1,
                verbose=1,
                refit=True
            )
        else:
            search = RandomizedSearchCV(
                self.model.model,
                param_grid,
                n_iter=n_iter,
                cv=cv,
                scoring=self.scoring[0],
                n_jobs=-1,
                verbose=1,
                random_state=self.random_state,
                refit=True
            )
        
        search.fit(X, y)
        
        search_time = time.time() - search_start
        
        # Update model with best parameters
        self.model.model = search.best_estimator_
        self._best_params = search.best_params_
        
        results = {
            'best_params': search.best_params_,
            'best_score': search.best_score_,
            'search_time': search_time,
            'n_splits': self.cv_folds
        }
        
        logger.info(
            f"Hyperparameter search completed in {search_time:.2f}s - "
            f"Best score: {search.best_score_:.4f}"
        )
        logger.info(f"Best parameters: {search.best_params_}")
        
        return search.best_params_, search.best_score_
    
    def get_feature_importance(
        self,
        feature_names: Optional[List[str]] = None,
        top_n: int = 20
    ) -> Dict[str, float]:
        """Get feature importance from trained model.
        
        Args:
            feature_names: Names of features.
            top_n: Number of top features to return.
            
        Returns:
            Dictionary of feature names and importance scores.
        """
        importance = self.model.get_feature_importance()
        
        if importance is None:
            logger.warning("Feature importance not available for this model type")
            return {}
        
        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(len(importance))]
        
        # Create feature importance dictionary
        importance_dict = dict(zip(feature_names, importance))
        
        # Sort by importance
        sorted_importance = dict(
            sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)[:top_n]
        )
        
        return sorted_importance
    
    def save_training_history(self, path: str) -> None:
        """Save training history to JSON file.
        
        Args:
            path: Path to save the history.
        """
        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'w') as f:
            json.dump(self._training_history, f, indent=2)
        
        logger.info(f"Training history saved to {path}")
    
    @property
    def cv_results(self) -> Dict[str, Any]:
        """Get the latest cross-validation results."""
        return self._cv_results
    
    @property
    def best_params(self) -> Dict[str, Any]:
        """Get the best hyperparameters from search."""
        return self._best_params


class EarlyStoppingTrainer:
    """Trainer with early stopping support.
    
    Supports models that implement partial_fit for incremental training.
    
    Example:
        >>> trainer = EarlyStoppingTrainer(model, patience=5)
        >>> trainer.train(X_train, y_train, X_val, y_val)
    """
    
    def __init__(
        self,
        model,
        patience: int = 10,
        min_delta: float = 0.001,
        scoring: str = 'accuracy'
    ):
        """Initialize the early stopping trainer.
        
        Args:
            model: Model to train.
            patience: Number of epochs without improvement to wait.
            min_delta: Minimum change to qualify as improvement.
            scoring: Scoring metric to monitor.
        """
        self.model = model
        self.patience = patience
        self.min_delta = min_delta
        self.scoring = scoring
        
        self._best_score = -np.inf
        self._best_epoch = 0
        self._wait = 0
        
        logger.info(
            f"EarlyStoppingTrainer initialized with patience={patience}, "
            f"min_delta={min_delta}"
        )
    
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        max_epochs: int = 100,
        batch_size: int = 32
    ) -> Dict[str, Any]:
        """Train with early stopping.
        
        Args:
            X_train: Training features.
            y_train: Training targets.
            X_val: Validation features.
            y_val: Validation targets.
            max_epochs: Maximum number of epochs.
            batch_size: Training batch size.
            
        Returns:
            Training results dictionary.
        """
        from sklearn.metrics import accuracy_score
        
        n_samples = X_train.shape[0]
        history = {'train_scores': [], 'val_scores': []}
        
        for epoch in range(max_epochs):
            # Shuffle training data
            indices = np.random.permutation(n_samples)
            X_shuffled = X_train[indices]
            y_shuffled = y_train[indices]
            
            # Train on batches
            for i in range(0, n_samples, batch_size):
                X_batch = X_shuffled[i:i+batch_size]
                y_batch = y_shuffled[i:i+batch_size]
                
                if hasattr(self.model.model, 'partial_fit'):
                    self.model.model.partial_fit(X_batch, y_batch)
            
            # Evaluate
            train_pred = self.model.predict(X_train)
            val_pred = self.model.predict(X_val)
            
            train_score = accuracy_score(y_train, train_pred)
            val_score = accuracy_score(y_val, val_pred)
            
            history['train_scores'].append(train_score)
            history['val_scores'].append(val_score)
            
            # Check for improvement
            if val_score > self._best_score + self.min_delta:
                self._best_score = val_score
                self._best_epoch = epoch
                self._wait = 0
                # Save best model state
                self.model.save('best_model_temp.pkl')
            else:
                self._wait += 1
            
            logger.debug(
                f"Epoch {epoch+1}/{max_epochs} - "
                f"Train: {train_score:.4f}, Val: {val_score:.4f}"
            )
            
            # Early stopping check
            if self._wait >= self.patience:
                logger.info(f"Early stopping at epoch {epoch+1}")
                break
        
        # Restore best model
        self.model.load('best_model_temp.pkl')
        
        history['best_epoch'] = self._best_epoch
        history['best_score'] = self._best_score
        
        return history

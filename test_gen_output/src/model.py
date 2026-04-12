"""Machine learning model implementations.

This module provides model classes for classification and regression tasks,
with support for various algorithms and hyperparameter tuning.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import warnings

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import (
    GradientBoostingClassifier,
    RandomForestClassifier,
    VotingClassifier
)
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import (
    GridSearchCV,
    RandomizedSearchCV,
    cross_val_score
)
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

logger = logging.getLogger(__name__)


class ModelError(Exception):
    """Exception raised for model-related errors."""
    pass


class BaseModel(ABC):
    """Abstract base class for machine learning models.
    
    Defines the interface that all model implementations must follow.
    """
    
    @abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'BaseModel':
        """Fit the model to training data.
        
        Args:
            X: Training features.
            y: Training targets.
            
        Returns:
            Fitted model instance.
        """
        pass
    
    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions on new data.
        
        Args:
            X: Features to predict.
            
        Returns:
            Predictions.
        """
        pass
    
    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Get prediction probabilities.
        
        Args:
            X: Features to predict.
            
            Returns:
            Probability predictions.
        """
        pass
    
    @abstractmethod
    def save(self, path: str) -> None:
        """Save the model to disk.
        
        Args:
            path: Path to save the model.
        """
        pass
    
    @abstractmethod
    def load(self, path: str) -> None:
        """Load the model from disk.
        
        Args:
            path: Path to load the model from.
        """
        pass


class SklearnClassifierWrapper(BaseModel):
    """Wrapper for scikit-learn classifiers.
    
    Provides a consistent interface for various sklearn classifiers.
    
    Attributes:
        model: The underlying sklearn model.
        model_name: Name of the model type.
        params: Model hyperparameters.
    
    Example:
        >>> wrapper = SklearnClassifierWrapper(
        ...     model_type='random_forest',
        ...     n_estimators=100
        ... )
        >>> wrapper.fit(X_train, y_train)
        >>> predictions = wrapper.predict(X_test)
    """
    
    SUPPORTED_MODELS = {
        'random_forest': RandomForestClassifier,
        'logistic_regression': LogisticRegression,
        'decision_tree': DecisionTreeClassifier,
        'gradient_boosting': GradientBoostingClassifier,
        'knn': KNeighborsClassifier,
        'svm': SVC
    }
    
    def __init__(
        self,
        model_type: str = 'random_forest',
        random_state: int = 42,
        **kwargs
    ):
        """Initialize the classifier wrapper.
        
        Args:
            model_type: Type of classifier to use.
            random_state: Random seed for reproducibility.
            **kwargs: Additional hyperparameters for the model.
            
        Raises:
            ModelError: If the model type is not supported.
        """
        if model_type not in self.SUPPORTED_MODELS:
            raise ModelError(
                f"Unsupported model type: {model_type}. "
                f"Supported types: {list(self.SUPPORTED_MODELS.keys())}"
            )
        
        self.model_type = model_type
        self.model_name = model_type
        self.random_state = random_state
        self.params = kwargs
        
        # Set probability=True for SVM
        if model_type == 'svm' and 'probability' not in kwargs:
            kwargs['probability'] = True
        
        # Set random_state for applicable models
        if model_type in ['random_forest', 'decision_tree', 'gradient_boosting', 'svm', 'logistic_regression']:
            kwargs['random_state'] = random_state
        
        self.model: BaseEstimator = self.SUPPORTED_MODELS[model_type](**kwargs)
        self._is_fitted = False
        
        logger.info(f"Initialized {model_type} classifier")
    
    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        sample_weight: Optional[np.ndarray] = None
    ) -> 'SklearnClassifierWrapper':
        """Fit the classifier to training data.
        
        Args:
            X: Training features.
            y: Training targets.
            sample_weight: Optional sample weights.
            
        Returns:
            Fitted model instance.
        """
        logger.info(f"Fitting {self.model_type} on {X.shape[0]} samples")
        
        fit_params = {}
        if sample_weight is not None:
            fit_params['sample_weight'] = sample_weight
        
        self.model.fit(X, y, **fit_params)
        self._is_fitted = True
        
        logger.info("Model fitting completed")
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions on new data.
        
        Args:
            X: Features to predict.
            
        Returns:
            Predicted class labels.
            
        Raises:
            ModelError: If model is not fitted.
        """
        if not self._is_fitted:
            raise ModelError("Model must be fitted before prediction")
        
        return self.model.predict(X)
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Get prediction probabilities.
        
        Args:
            X: Features to predict.
            
        Returns:
            Probability predictions for each class.
            
        Raises:
            ModelError: If model is not fitted.
        """
        if not self._is_fitted:
            raise ModelError("Model must be fitted before prediction")
        
        return self.model.predict_proba(X)
    
    def get_feature_importance(self) -> Optional[np.ndarray]:
        """Get feature importance if available.
        
        Returns:
            Feature importance array or None if not available.
        """
        if hasattr(self.model, 'feature_importances_'):
            return self.model.feature_importances_
        elif hasattr(self.model, 'coef_'):
            return np.abs(self.model.coef_).mean(axis=0)
        return None
    
    def get_params(self, deep: bool = True) -> Dict[str, Any]:
        """Get model parameters.
        
        Args:
            deep: Whether to return nested parameters.
            
        Returns:
            Dictionary of parameters.
        """
        return self.model.get_params(deep=deep)
    
    def set_params(self, **params) -> 'SklearnClassifierWrapper':
        """Set model parameters.
        
        Args:
            **params: Parameters to set.
            
        Returns:
            Model instance.
        """
        self.model.set_params(**params)
        self.params.update(params)
        return self
    
    def save(self, path: str) -> None:
        """Save the model to disk.
        
        Args:
            path: Path to save the model.
        """
        import joblib
        
        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        model_data = {
            'model': self.model,
            'model_type': self.model_type,
            'params': self.params,
            'random_state': self.random_state,
            'is_fitted': self._is_fitted
        }
        
        joblib.dump(model_data, save_path)
        logger.info(f"Model saved to {path}")
    
    def load(self, path: str) -> None:
        """Load the model from disk.
        
        Args:
            path: Path to load the model from.
        """
        import joblib
        
        model_data = joblib.load(path)
        
        self.model = model_data['model']
        self.model_type = model_data['model_type']
        self.params = model_data['params']
        self.random_state = model_data['random_state']
        self._is_fitted = model_data['is_fitted']
        
        logger.info(f"Model loaded from {path}")


class EnsembleClassifier(BaseModel):
    """Ensemble classifier combining multiple models.
    
    Creates a voting classifier from multiple base models.
    
    Attributes:
        models: List of base models.
        voting: Type of voting ('hard' or 'soft').
        ensemble: The voting classifier.
    
    Example:
        >>> ensemble = EnsembleClassifier(voting='soft')
        >>> ensemble.add_model('rf', RandomForestClassifier())
        >>> ensemble.add_model('lr', LogisticRegression())
        >>> ensemble.fit(X_train, y_train)
    """
    
    def __init__(
        self,
        voting: str = 'soft',
        weights: Optional[List[float]] = None
    ):
        """Initialize the ensemble classifier.
        
        Args:
            voting: Type of voting ('hard' or 'soft').
            weights: Weights for each model in voting.
        """
        self.voting = voting
        self.weights = weights
        self.models: List[Tuple[str, BaseEstimator]] = []
        self.ensemble: Optional[VotingClassifier] = None
        self._is_fitted = False
        
        logger.info(f"Initialized EnsembleClassifier with {voting} voting")
    
    def add_model(
        self,
        name: str,
        model: BaseEstimator
    ) -> 'EnsembleClassifier':
        """Add a model to the ensemble.
        
        Args:
            name: Name for the model.
            model: Sklearn-compatible model.
            
        Returns:
            Ensemble instance.
        """
        self.models.append((name, model))
        logger.info(f"Added model '{name}' to ensemble")
        return self
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'EnsembleClassifier':
        """Fit the ensemble to training data.
        
        Args:
            X: Training features.
            y: Training targets.
            
        Returns:
            Fitted ensemble instance.
        """
        if not self.models:
            raise ModelError("No models added to ensemble")
        
        self.ensemble = VotingClassifier(
            estimators=self.models,
            voting=self.voting,
            weights=self.weights
        )
        
        logger.info(f"Fitting ensemble with {len(self.models)} models")
        self.ensemble.fit(X, y)
        self._is_fitted = True
        
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions.
        
        Args:
            X: Features to predict.
            
        Returns:
            Predictions.
        """
        if not self._is_fitted:
            raise ModelError("Ensemble must be fitted before prediction")
        
        return self.ensemble.predict(X)
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Get prediction probabilities.
        
        Args:
            X: Features to predict.
            
        Returns:
            Probability predictions.
        """
        if not self._is_fitted:
            raise ModelError("Ensemble must be fitted before prediction")
        
        if self.voting == 'hard':
            raise ModelError("predict_proba not available for hard voting")
        
        return self.ensemble.predict_proba(X)
    
    def save(self, path: str) -> None:
        """Save the ensemble to disk."""
        import joblib
        
        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        joblib.dump({
            'ensemble': self.ensemble,
            'models': self.models,
            'voting': self.voting,
            'weights': self.weights,
            'is_fitted': self._is_fitted
        }, save_path)
        
        logger.info(f"Ensemble saved to {path}")
    
    def load(self, path: str) -> None:
        """Load the ensemble from disk."""
        import joblib
        
        data = joblib.load(path)
        
        self.ensemble = data['ensemble']
        self.models = data['models']
        self.voting = data['voting']
        self.weights = data['weights']
        self._is_fitted = data['is_fitted']
        
        logger.info(f"Ensemble loaded from {path}")


class MLPipeline:
    """Complete machine learning pipeline.
    
    Combines data processing, model training, and evaluation.
    
    Example:
        >>> pipeline = MLPipeline(config=config)
        >>> results = pipeline.run('data/train.csv')
    """
    
    def __init__(
        self,
        model_type: str = 'random_forest',
        random_state: int = 42,
        **model_params
    ):
        """Initialize the ML pipeline.
        
        Args:
            model_type: Type of model to use.
            random_state: Random seed.
            **model_params: Model hyperparameters.
        """
        self.model = SklearnClassifierWrapper(
            model_type=model_type,
            random_state=random_state,
            **model_params
        )
        self._is_trained = False
        
        logger.info(f"ML Pipeline initialized with {model_type}")
    
    def train(
        self,
        X: np.ndarray,
        y: np.ndarray
    ) -> 'MLPipeline':
        """Train the model.
        
        Args:
            X: Training features.
            y: Training targets.
            
        Returns:
            Trained pipeline instance.
        """
        self.model.fit(X, y)
        self._is_trained = True
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions.
        
        Args:
            X: Features to predict.
            
        Returns:
            Predictions.
        """
        if not self._is_trained:
            raise ModelError("Pipeline must be trained before prediction")
        
        return self.model.predict(X)
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Get prediction probabilities."""
        if not self._is_trained:
            raise ModelError("Pipeline must be trained before prediction")
        
        return self.model.predict_proba(X)
    
    def save(self, path: str) -> None:
        """Save the pipeline."""
        self.model.save(path)
    
    def load(self, path: str) -> None:
        """Load the pipeline."""
        self.model.load(path)
        self._is_trained = True

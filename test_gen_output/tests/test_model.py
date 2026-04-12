"""Unit tests for the model module."""

import pytest
import numpy as np
from pathlib import Path
import tempfile

from src.model import (
    SklearnClassifierWrapper,
    EnsembleClassifier,
    MLPipeline,
    ModelError
)


@pytest.fixture
def sample_data():
    """Generate sample data for testing."""
    np.random.seed(42)
    X = np.random.randn(100, 5)
    y = np.random.randint(0, 3, 100)
    return X, y


class TestSklearnClassifierWrapper:
    """Tests for SklearnClassifierWrapper class."""
    
    def test_init_random_forest(self):
        """Test initialization with random forest."""
        model = SklearnClassifierWrapper(model_type='random_forest')
        assert model.model_type == 'random_forest'
        assert model.model is not None
    
    def test_init_invalid_model_type(self):
        """Test initialization with invalid model type."""
        with pytest.raises(ModelError):
            SklearnClassifierWrapper(model_type='invalid_model')
    
    def test_fit(self, sample_data):
        """Test model fitting."""
        X, y = sample_data
        model = SklearnClassifierWrapper(model_type='random_forest')
        model.fit(X, y)
        assert model._is_fitted
    
    def test_predict(self, sample_data):
        """Test prediction."""
        X, y = sample_data
        model = SklearnClassifierWrapper(model_type='random_forest')
        model.fit(X, y)
        predictions = model.predict(X[:10])
        assert len(predictions) == 10
    
    def test_predict_not_fitted(self, sample_data):
        """Test prediction before fitting."""
        X, _ = sample_data
        model = SklearnClassifierWrapper(model_type='random_forest')
        with pytest.raises(ModelError):
            model.predict(X)
    
    def test_predict_proba(self, sample_data):
        """Test probability prediction."""
        X, y = sample_data
        model = SklearnClassifierWrapper(model_type='random_forest')
        model.fit(X, y)
        proba = model.predict_proba(X[:10])
        assert proba.shape == (10, 3)  # 3 classes
        assert np.allclose(proba.sum(axis=1), 1.0)
    
    def test_get_feature_importance(self, sample_data):
        """Test feature importance."""
        X, y = sample_data
        model = SklearnClassifierWrapper(model_type='random_forest')
        model.fit(X, y)
        importance = model.get_feature_importance()
        assert importance is not None
        assert len(importance) == 5
    
    def test_save_load(self, sample_data):
        """Test model save and load."""
        X, y = sample_data
        model = SklearnClassifierWrapper(model_type='random_forest', n_estimators=10)
        model.fit(X, y)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'model.pkl'
            model.save(str(path))
            
            new_model = SklearnClassifierWrapper(model_type='random_forest')
            new_model.load(str(path))
            
            assert new_model._is_fitted
            predictions = new_model.predict(X[:5])
            assert len(predictions) == 5
    
    def test_all_model_types(self, sample_data):
        """Test all supported model types."""
        X, y = sample_data
        
        for model_type in SklearnClassifierWrapper.SUPPORTED_MODELS:
            model = SklearnClassifierWrapper(model_type=model_type)
            model.fit(X, y)
            predictions = model.predict(X[:5])
            assert len(predictions) == 5


class TestEnsembleClassifier:
    """Tests for EnsembleClassifier class."""
    
    def test_add_model(self):
        """Test adding models to ensemble."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        
        ensemble = EnsembleClassifier(voting='soft')
        ensemble.add_model('rf', RandomForestClassifier())
        ensemble.add_model('lr', LogisticRegression())
        
        assert len(ensemble.models) == 2
    
    def test_fit_predict(self, sample_data):
        """Test ensemble fit and predict."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        
        X, y = sample_data
        
        ensemble = EnsembleClassifier(voting='soft')
        ensemble.add_model('rf', RandomForestClassifier(n_estimators=10))
        ensemble.add_model('lr', LogisticRegression())
        
        ensemble.fit(X, y)
        predictions = ensemble.predict(X[:5])
        
        assert len(predictions) == 5
    
    def test_predict_proba_soft_voting(self, sample_data):
        """Test probability prediction with soft voting."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        
        X, y = sample_data
        
        ensemble = EnsembleClassifier(voting='soft')
        ensemble.add_model('rf', RandomForestClassifier(n_estimators=10))
        ensemble.add_model('lr', LogisticRegression())
        
        ensemble.fit(X, y)
        proba = ensemble.predict_proba(X[:5])
        
        assert proba.shape[0] == 5
    
    def test_hard_voting_no_proba(self, sample_data):
        """Test that hard voting doesn't support predict_proba."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        
        X, y = sample_data
        
        ensemble = EnsembleClassifier(voting='hard')
        ensemble.add_model('rf', RandomForestClassifier(n_estimators=10))
        ensemble.fit(X, y)
        
        with pytest.raises(ModelError):
            ensemble.predict_proba(X[:5])


class TestMLPipeline:
    """Tests for MLPipeline class."""
    
    def test_train_predict(self, sample_data):
        """Test pipeline train and predict."""
        X, y = sample_data
        
        pipeline = MLPipeline(model_type='random_forest', n_estimators=10)
        pipeline.train(X, y)
        
        predictions = pipeline.predict(X[:5])
        assert len(predictions) == 5
    
    def test_predict_not_trained(self, sample_data):
        """Test predict before training."""
        X, _ = sample_data
        
        pipeline = MLPipeline(model_type='random_forest')
        
        with pytest.raises(ModelError):
            pipeline.predict(X)
    
    def test_save_load(self, sample_data):
        """Test pipeline save and load."""
        X, y = sample_data
        
        pipeline = MLPipeline(model_type='random_forest', n_estimators=10)
        pipeline.train(X, y)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'pipeline.pkl'
            pipeline.save(str(path))
            
            new_pipeline = MLPipeline(model_type='random_forest')
            new_pipeline.load(str(path))
            
            predictions = new_pipeline.predict(X[:5])
            assert len(predictions) == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

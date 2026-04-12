"""Machine Learning Pipeline Package.

This package provides a complete, production-ready machine learning pipeline
with data processing, model training, and evaluation capabilities.
"""

__version__ = "1.0.0"
__author__ = "ML Pipeline Team"

from src.model import MLPipeline
from src.data_processor import DataProcessor
from src.trainer import ModelTrainer
from src.evaluator import ModelEvaluator

__all__ = [
    "MLPipeline",
    "DataProcessor",
    "ModelTrainer",
    "ModelEvaluator",
]

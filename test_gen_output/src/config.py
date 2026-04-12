"""Configuration management module.

This module handles loading and validating configuration settings
from YAML files and environment variables.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for the machine learning model.
    
    Attributes:
        model_type: Type of model to use (e.g., 'random_forest', 'logistic_regression').
        random_state: Random seed for reproducibility.
        hyperparameters: Model-specific hyperparameters.
    """
    model_type: str = "random_forest"
    random_state: int = 42
    hyperparameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataConfig:
    """Configuration for data processing.
    
    Attributes:
        data_path: Path to the input data file.
        target_column: Name of the target variable column.
        test_size: Proportion of data to use for testing.
        validation_size: Proportion of training data to use for validation.
        categorical_columns: List of categorical column names.
        numerical_columns: List of numerical column names.
    """
    data_path: str = "data/input/dataset.csv"
    target_column: str = "target"
    test_size: float = 0.2
    validation_size: float = 0.2
    categorical_columns: list = field(default_factory=list)
    numerical_columns: list = field(default_factory=list)


@dataclass
class TrainingConfig:
    """Configuration for model training.
    
    Attributes:
        cross_validation_folds: Number of folds for cross-validation.
        scoring_metric: Metric to optimize during training.
        enable_hyperparameter_tuning: Whether to perform hyperparameter search.
        n_trials: Number of trials for hyperparameter optimization.
    """
    cross_validation_folds: int = 5
    scoring_metric: str = "accuracy"
    enable_hyperparameter_tuning: bool = False
    n_trials: int = 50


@dataclass
class Config:
    """Main configuration class combining all config sections.
    
    Attributes:
        model: Model configuration.
        data: Data processing configuration.
        training: Training configuration.
        output_dir: Directory for saving outputs.
        log_level: Logging level.
    """
    model: ModelConfig = field(default_factory=ModelConfig)
    data: DataConfig = field(default_factory=DataConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    output_dir: str = "outputs"
    log_level: str = "INFO"


class ConfigManager:
    """Manages loading and validation of configuration.
    
    This class provides methods to load configuration from YAML files,
    validate settings, and create configuration objects.
    
    Example:
        >>> config_manager = ConfigManager()
        >>> config = config_manager.load_config("config/config.yaml")
        >>> print(config.model.model_type)
    """
    
    DEFAULT_CONFIG_PATH = "config/config.yaml"
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the ConfigManager.
        
        Args:
            config_path: Path to the configuration file. If None, uses default.
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._config: Optional[Config] = None
        
    def load_config(self, config_path: Optional[str] = None) -> Config:
        """Load configuration from a YAML file.
        
        Args:
            config_path: Path to the configuration file. Overrides instance path.
            
        Returns:
            Config object with loaded settings.
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist.
            ValueError: If the configuration is invalid.
        """
        path = Path(config_path or self.config_path)
        
        if not path.exists():
            logger.warning(f"Config file not found at {path}, using defaults")
            return self._create_default_config()
        
        try:
            with open(path, 'r') as f:
                config_dict = yaml.safe_load(f) or {}
            
            self._config = self._parse_config(config_dict)
            logger.info(f"Configuration loaded successfully from {path}")
            return self._config
            
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML config: {e}")
            raise ValueError(f"Invalid YAML in config file: {e}")
    
    def _parse_config(self, config_dict: Dict[str, Any]) -> Config:
        """Parse configuration dictionary into Config object.
        
        Args:
            config_dict: Dictionary with configuration values.
            
        Returns:
            Config object with parsed settings.
        """
        model_dict = config_dict.get('model', {})
        data_dict = config_dict.get('data', {})
        training_dict = config_dict.get('training', {})
        
        model_config = ModelConfig(
            model_type=model_dict.get('model_type', 'random_forest'),
            random_state=model_dict.get('random_state', 42),
            hyperparameters=model_dict.get('hyperparameters', {})
        )
        
        data_config = DataConfig(
            data_path=data_dict.get('data_path', 'data/input/dataset.csv'),
            target_column=data_dict.get('target_column', 'target'),
            test_size=data_dict.get('test_size', 0.2),
            validation_size=data_dict.get('validation_size', 0.2),
            categorical_columns=data_dict.get('categorical_columns', []),
            numerical_columns=data_dict.get('numerical_columns', [])
        )
        
        training_config = TrainingConfig(
            cross_validation_folds=training_dict.get('cross_validation_folds', 5),
            scoring_metric=training_dict.get('scoring_metric', 'accuracy'),
            enable_hyperparameter_tuning=training_dict.get('enable_hyperparameter_tuning', False),
            n_trials=training_dict.get('n_trials', 50)
        )
        
        return Config(
            model=model_config,
            data=data_config,
            training=training_config,
            output_dir=config_dict.get('output_dir', 'outputs'),
            log_level=config_dict.get('log_level', 'INFO')
        )
    
    def _create_default_config(self) -> Config:
        """Create a default configuration.
        
        Returns:
            Config object with default settings.
        """
        return Config()
    
    def save_config(self, config: Config, output_path: str) -> None:
        """Save configuration to a YAML file.
        
        Args:
            config: Config object to save.
            output_path: Path where to save the configuration.
        """
        config_dict = {
            'model': {
                'model_type': config.model.model_type,
                'random_state': config.model.random_state,
                'hyperparameters': config.model.hyperparameters
            },
            'data': {
                'data_path': config.data.data_path,
                'target_column': config.data.target_column,
                'test_size': config.data.test_size,
                'validation_size': config.data.validation_size,
                'categorical_columns': config.data.categorical_columns,
                'numerical_columns': config.data.numerical_columns
            },
            'training': {
                'cross_validation_folds': config.training.cross_validation_folds,
                'scoring_metric': config.training.scoring_metric,
                'enable_hyperparameter_tuning': config.training.enable_hyperparameter_tuning,
                'n_trials': config.training.n_trials
            },
            'output_dir': config.output_dir,
            'log_level': config.log_level
        }
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)
        
        logger.info(f"Configuration saved to {output_path}")


def get_config(config_path: Optional[str] = None) -> Config:
    """Convenience function to get configuration.
    
    Args:
        config_path: Optional path to configuration file.
        
    Returns:
        Config object.
    """
    manager = ConfigManager(config_path)
    return manager.load_config()

# Machine Learning Pipeline

A production-ready, modular machine learning pipeline for classification tasks.

## Features

- **Modular Architecture**: Separate modules for data processing, model training, and evaluation
- **Multiple Model Support**: Random Forest, Logistic Regression, Gradient Boosting, SVM, KNN, and Decision Trees
- **Hyperparameter Tuning**: Grid search and random search optimization
- **Cross-Validation**: Stratified K-fold cross-validation support
- **Comprehensive Evaluation**: Metrics, confusion matrices, ROC curves, and feature importance
- **Configuration Management**: YAML-based configuration with command-line overrides
- **Logging**: Structured logging with JSON format support
- **Extensible**: Easy to add new models and preprocessing steps

## Installation

```bash
# Clone the repository
git clone https://github.com/example/ml_pipeline.git
cd ml_pipeline

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e ".[dev]"
```

## Quick Start

### Using Command Line

```bash
# Run with default configuration
python -m src.main

# Run with custom configuration
python -m src.main --config config/config.yaml

# Run with specific model and data
python -m src.main --model gradient_boosting --data data/train.csv

# Run with hyperparameter tuning
python -m src.main --tune

# Create sample data for testing
python -m src.main --create-sample-data --output data/sample.csv
```

### Using Python API

```python
from src.config import get_config
from src.main import run_pipeline

# Load configuration
config = get_config('config/config.yaml')

# Run pipeline
results = run_pipeline(config)

print(f"Accuracy: {results['evaluation']['metrics']['accuracy']:.4f}")
```

## Project Structure

```
ml_pipeline/
├── config/
│   └── config.yaml          # Configuration file
├── data/
│   └── input/               # Input data directory
├── outputs/                  # Model outputs and reports
├── logs/                     # Log files
├── src/
│   ├── __init__.py
│   ├── config.py            # Configuration management
│   ├── logger.py            # Logging setup
│   ├── data_processor.py    # Data preprocessing
│   ├── model.py             # Model implementations
│   ├── trainer.py           # Training pipeline
│   ├── evaluator.py         # Model evaluation
│   └── main.py              # Entry point
├── tests/
│   ├── __init__.py
│   └── test_model.py        # Unit tests
├── requirements.txt
├── setup.py
└── README.md
```

## Configuration

Configuration is managed via YAML files. See `config/config.yaml` for all available options:

```yaml
model:
  model_type: random_forest
  random_state: 42
  hyperparameters:
    n_estimators: 100
    max_depth: 10

data:
  data_path: data/input/dataset.csv
  target_column: target
  test_size: 0.2

training:
  cross_validation_folds: 5
  scoring_metric: accuracy
  enable_hyperparameter_tuning: false
```

## Supported Models

- `random_forest` - Random Forest Classifier
- `logistic_regression` - Logistic Regression
- `gradient_boosting` - Gradient Boosting Classifier
- `decision_tree` - Decision Tree Classifier
- `knn` - K-Nearest Neighbors
- `svm` - Support Vector Machine

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## License

MIT License - see LICENSE file for details.

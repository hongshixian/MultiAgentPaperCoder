"""Main entry point for the ML pipeline.

This module provides the command-line interface and orchestrates
the complete machine learning workflow.
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

import numpy as np

from src.config import Config, ConfigManager, get_config
from src.logger import setup_logging, get_logger
from src.data_processor import DataProcessor, DataValidationError
from src.model import MLPipeline, SklearnClassifierWrapper
from src.trainer import ModelTrainer
from src.evaluator import ModelEvaluator

logger = get_logger(__name__)


def create_sample_data(output_path: str, n_samples: int = 1000) -> None:
    """Create sample data for testing.
    
    Args:
        output_path: Path to save the sample data.
        n_samples: Number of samples to generate.
    """
    import pandas as pd
    
    np.random.seed(42)
    
    # Generate synthetic data
    data = {
        'feature_1': np.random.randn(n_samples),
        'feature_2': np.random.randn(n_samples),
        'feature_3': np.random.randn(n_samples) * 2,
        'feature_4': np.random.randn(n_samples) + 1,
        'category': np.random.choice(['A', 'B', 'C'], n_samples),
        'target': np.random.choice([0, 1, 2], n_samples)
    }
    
    df = pd.DataFrame(data)
    
    # Add some correlation with target
    df.loc[df['target'] == 0, 'feature_1'] += 1
    df.loc[df['target'] == 1, 'feature_2'] += 1
    df.loc[df['target'] == 2, 'feature_3'] += 1
    
    # Save to file
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False)
    
    logger.info(f"Sample data created at {output_path}")


def run_pipeline(config: Config) -> dict:
    """Run the complete ML pipeline.
    
    Args:
        config: Configuration object.
        
    Returns:
        Dictionary containing pipeline results.
    """
    pipeline_start = datetime.now()
    
    logger.info("="*60)
    logger.info("Starting ML Pipeline")
    logger.info("="*60)
    
    results = {
        'start_time': pipeline_start.isoformat(),
        'config': {
            'model_type': config.model.model_type,
            'test_size': config.data.test_size,
            'cv_folds': config.training.cross_validation_folds
        }
    }
    
    try:
        # Step 1: Data Processing
        logger.info("\n[Step 1/4] Data Processing")
        logger.info("-" * 40)
        
        data_processor = DataProcessor(
            categorical_columns=config.data.categorical_columns,
            numerical_columns=config.data.numerical_columns,
            target_column=config.data.target_column,
            test_size=config.data.test_size,
            validation_size=config.data.validation_size,
            random_state=config.model.random_state
        )
        
        # Check if data file exists, create sample if not
        data_path = Path(config.data.data_path)
        if not data_path.exists():
            logger.warning(f"Data file not found at {data_path}")
            logger.info("Creating sample data for demonstration...")
            create_sample_data(str(data_path))
        
        X_train, X_test, y_train, y_test = data_processor.prepare_data(
            str(data_path),
            validate=True
        )
        
        results['data'] = {
            'n_train': len(X_train),
            'n_test': len(X_test),
            'n_features': X_train.shape[1],
            'feature_names': data_processor.feature_names
        }
        
        # Step 2: Model Creation
        logger.info("\n[Step 2/4] Model Creation")
        logger.info("-" * 40)
        
        model = SklearnClassifierWrapper(
            model_type=config.model.model_type,
            random_state=config.model.random_state,
            **config.model.hyperparameters
        )
        
        # Step 3: Model Training
        logger.info("\n[Step 3/4] Model Training")
        logger.info("-" * 40)
        
        trainer = ModelTrainer(
            model=model,
            cv_folds=config.training.cross_validation_folds,
            scoring=config.training.scoring_metric
        )
        
        training_results = trainer.train(X_train, y_train)
        results['training'] = training_results
        
        # Hyperparameter tuning if enabled
        if config.training.enable_hyperparameter_tuning:
            logger.info("\nPerforming hyperparameter tuning...")
            
            param_grid = _get_param_grid(config.model.model_type)
            best_params, best_score = trainer.hyperparameter_search(
                X_train, y_train,
                param_grid,
                search_type='random',
                n_iter=config.training.n_trials
            )
            
            results['hyperparameter_tuning'] = {
                'best_params': best_params,
                'best_score': best_score
            }
        
        # Step 4: Model Evaluation
        logger.info("\n[Step 4/4] Model Evaluation")
        logger.info("-" * 40)
        
        # Get class names
        if data_processor.label_encoder is not None:
            class_names = data_processor.label_encoder.classes_.tolist()
        else:
            class_names = [str(i) for i in range(len(np.unique(y_test)))]
        
        evaluator = ModelEvaluator(
            model=model,
            class_names=class_names
        )
        
        evaluation_results = evaluator.evaluate(X_test, y_test)
        results['evaluation'] = evaluation_results
        
        # Generate reports
        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        report_path = evaluator.generate_report(
            X_test, y_test,
            str(output_dir / 'evaluation')
        )
        
        # Save model and preprocessor
        model_path = output_dir / 'model.pkl'
        model.save(str(model_path))
        
        preprocessor_path = output_dir / 'preprocessor.pkl'
        data_processor.save_preprocessor(str(preprocessor_path))
        
        # Save feature importance
        feature_importance = trainer.get_feature_importance(
            data_processor.feature_names
        )
        results['feature_importance'] = feature_importance
        
        if feature_importance:
            evaluator.plot_feature_importance(
                data_processor.feature_names,
                save_path=str(output_dir / 'feature_importance.png')
            )
        
        # Save training history
        trainer.save_training_history(str(output_dir / 'training_history.json'))
        
        # Finalize results
        pipeline_end = datetime.now()
        results['end_time'] = pipeline_end.isoformat()
        results['total_time'] = (pipeline_end - pipeline_start).total_seconds()
        results['status'] = 'success'
        results['output_dir'] = str(output_dir)
        
        # Print summary
        _print_summary(results)
        
    except DataValidationError as e:
        logger.error(f"Data validation error: {e}")
        results['status'] = 'failed'
        results['error'] = str(e)
        raise
    
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        results['status'] = 'failed'
        results['error'] = str(e)
        raise
    
    # Save final results
    results_path = output_dir / 'results.json'
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"\nResults saved to {results_path}")
    
    return results


def _get_param_grid(model_type: str) -> dict:
    """Get parameter grid for hyperparameter tuning.
    
    Args:
        model_type: Type of model.
        
    Returns:
        Parameter grid dictionary.
    """
    param_grids = {
        'random_forest': {
            'n_estimators': [50, 100, 200],
            'max_depth': [5, 10, 20, None],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4]
        },
        'logistic_regression': {
            'C': [0.01, 0.1, 1, 10, 100],
            'penalty': ['l1', 'l2'],
            'solver': ['liblinear', 'saga']
        },
        'gradient_boosting': {
            'n_estimators': [50, 100, 200],
            'learning_rate': [0.01, 0.1, 0.3],
            'max_depth': [3, 5, 7]
        },
        'decision_tree': {
            'max_depth': [3, 5, 10, None],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4]
        },
        'knn': {
            'n_neighbors': [3, 5, 7, 11],
            'weights': ['uniform', 'distance'],
            'metric': ['euclidean', 'manhattan']
        },
        'svm': {
            'C': [0.1, 1, 10],
            'kernel': ['rbf', 'linear'],
            'gamma': ['scale', 'auto']
        }
    }
    
    return param_grids.get(model_type, {})


def _print_summary(results: dict) -> None:
    """Print pipeline summary.
    
    Args:
        results: Pipeline results dictionary.
    """
    logger.info("\n" + "="*60)
    logger.info("PIPELINE SUMMARY")
    logger.info("="*60)
    
    logger.info(f"\nStatus: {results['status'].upper()}")
    logger.info(f"Total Time: {results['total_time']:.2f} seconds")
    
    if 'evaluation' in results:
        metrics = results['evaluation']['metrics']
        logger.info("\nModel Performance:")
        logger.info(f"  Accuracy:  {metrics['accuracy']:.4f}")
        logger.info(f"  Precision: {metrics['precision_weighted']:.4f}")
        logger.info(f"  Recall:    {metrics['recall_weighted']:.4f}")
        logger.info(f"  F1 Score:  {metrics['f1_weighted']:.4f}")
    
    if 'cross_validation' in results.get('training', {}):
        cv = results['training']['cross_validation']
        primary_metric = list(results['config']['scoring_metric'] if isinstance(results['config']['scoring_metric'], list) else [results['config']['scoring_metric']])[0]
        logger.info(f"\nCross-Validation ({primary_metric}):")
        logger.info(f"  Mean: {cv.get(f'{primary_metric}_mean', 'N/A'):.4f}")
        logger.info(f"  Std:  {cv.get(f'{primary_metric}_std', 'N/A'):.4f}")
    
    logger.info(f"\nOutputs saved to: {results.get('output_dir', 'N/A')}")
    logger.info("="*60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Machine Learning Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main --config config/config.yaml
  python -m src.main --model random_forest --data data/train.csv
  python -m src.main --create-sample-data --output data/sample.csv
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='config/config.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--model', '-m',
        type=str,
        default='random_forest',
        choices=['random_forest', 'logistic_regression', 'gradient_boosting', 
                 'decision_tree', 'knn', 'svm'],
        help='Model type to use'
    )
    parser.add_argument(
        '--data', '-d',
        type=str,
        help='Path to data file'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='outputs',
        help='Output directory'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )
    parser.add_argument(
        '--create-sample-data',
        action='store_true',
        help='Create sample data for testing'
    )
    parser.add_argument(
        '--tune',
        action='store_true',
        help='Enable hyperparameter tuning'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(
        log_level=args.log_level,
        log_dir='logs' if args.log_level == 'DEBUG' else None
    )
    
    # Handle sample data creation
    if args.create_sample_data:
        output_path = args.data or 'data/sample_data.csv'
        create_sample_data(output_path)
        logger.info(f"Sample data created at {output_path}")
        return 0
    
    # Load or create configuration
    config_manager = ConfigManager(args.config)
    
    try:
        config = config_manager.load_config()
    except FileNotFoundError:
        logger.warning(f"Config file not found, using defaults")
        config = config_manager._create_default_config()
    
    # Override config with command line arguments
    if args.model:
        config.model.model_type = args.model
    if args.data:
        config.data.data_path = args.data
    if args.output:
        config.output_dir = args.output
    if args.tune:
        config.training.enable_hyperparameter_tuning = True
    
    # Run pipeline
    try:
        results = run_pipeline(config)
        return 0 if results['status'] == 'success' else 1
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())

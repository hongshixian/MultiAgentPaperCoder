"""Model evaluation module.

This module provides comprehensive evaluation metrics and visualization
capabilities for assessing model performance.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import json

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
    precision_recall_curve,
    average_precision_score
)

logger = logging.getLogger(__name__)


class ModelEvaluator:
    """Comprehensive model evaluation.
    
    Provides metrics calculation, visualization, and reporting capabilities.
    
    Attributes:
        model: The trained model to evaluate.
        class_names: Names of the target classes.
    
    Example:
        >>> evaluator = ModelEvaluator(model, class_names=['A', 'B'])
        >>> results = evaluator.evaluate(X_test, y_test)
        >>> evaluator.plot_confusion_matrix(X_test, y_test)
    """
    
    def __init__(
        self,
        model,
        class_names: Optional[List[str]] = None
    ):
        """Initialize the ModelEvaluator.
        
        Args:
            model: Trained model instance.
            class_names: Names of target classes.
        """
        self.model = model
        self.class_names = class_names
        self._evaluation_results: Dict[str, Any] = {}
        
        logger.info("ModelEvaluator initialized")
    
    def evaluate(
        self,
        X: np.ndarray,
        y: np.ndarray,
        include_confidence: bool = True
    ) -> Dict[str, Any]:
        """Perform comprehensive model evaluation.
        
        Args:
            X: Test features.
            y: True labels.
            include_confidence: Whether to include confidence metrics.
            
        Returns:
            Dictionary containing all evaluation metrics.
        """
        logger.info(f"Evaluating model on {len(X)} samples")
        
        # Get predictions
        y_pred = self.model.predict(X)
        
        results = {
            'n_samples': len(y),
            'n_classes': len(np.unique(y)),
            'metrics': self._calculate_metrics(y, y_pred)
        }
        
        # Add confusion matrix
        cm = confusion_matrix(y, y_pred)
        results['confusion_matrix'] = cm.tolist()
        
        # Add classification report
        report = classification_report(
            y, y_pred,
            target_names=self.class_names,
            output_dict=True,
            zero_division=0
        )
        results['classification_report'] = report
        
        # Add confidence metrics if available
        if include_confidence:
            try:
                y_proba = self.model.predict_proba(X)
                results['confidence_metrics'] = self._calculate_confidence_metrics(y, y_proba)
                results['roc_metrics'] = self._calculate_roc_metrics(y, y_proba)
            except Exception as e:
                logger.warning(f"Could not calculate confidence metrics: {e}")
        
        self._evaluation_results = results
        
        logger.info(
            f"Evaluation complete - Accuracy: {results['metrics']['accuracy']:.4f}, "
            f"F1: {results['metrics']['f1_weighted']:.4f}"
        )
        
        return results
    
    def _calculate_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray
    ) -> Dict[str, float]:
        """Calculate classification metrics.
        
        Args:
            y_true: True labels.
            y_pred: Predicted labels.
            
        Returns:
            Dictionary of metric scores.
        """
        metrics = {
            'accuracy': accuracy_score(y_true, y_pred),
            'precision_weighted': precision_score(
                y_true, y_pred, average='weighted', zero_division=0
            ),
            'recall_weighted': recall_score(
                y_true, y_pred, average='weighted', zero_division=0
            ),
            'f1_weighted': f1_score(
                y_true, y_pred, average='weighted', zero_division=0
            ),
            'precision_macro': precision_score(
                y_true, y_pred, average='macro', zero_division=0
            ),
            'recall_macro': recall_score(
                y_true, y_pred, average='macro', zero_division=0
            ),
            'f1_macro': f1_score(
                y_true, y_pred, average='macro', zero_division=0
            )
        }
        
        return metrics
    
    def _calculate_confidence_metrics(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray
    ) -> Dict[str, float]:
        """Calculate confidence-based metrics.
        
        Args:
            y_true: True labels.
            y_proba: Predicted probabilities.
            
        Returns:
            Dictionary of confidence metrics.
        """
        # Get max probability for each prediction
        max_proba = np.max(y_proba, axis=1)
        
        metrics = {
            'mean_confidence': float(np.mean(max_proba)),
            'std_confidence': float(np.std(max_proba)),
            'median_confidence': float(np.median(max_proba)),
            'min_confidence': float(np.min(max_proba)),
            'max_confidence': float(np.max(max_proba))
        }
        
        # Calculate confidence calibration
        y_pred = np.argmax(y_proba, axis=1)
        correct_mask = y_pred == y_true
        
        if np.any(correct_mask):
            metrics['mean_confidence_correct'] = float(np.mean(max_proba[correct_mask]))
        if np.any(~correct_mask):
            metrics['mean_confidence_incorrect'] = float(np.mean(max_proba[~correct_mask]))
        
        return metrics
    
    def _calculate_roc_metrics(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray
    ) -> Dict[str, Any]:
        """Calculate ROC and AUC metrics.
        
        Args:
            y_true: True labels.
            y_proba: Predicted probabilities.
            
        Returns:
            Dictionary of ROC metrics.
        """
        n_classes = y_proba.shape[1]
        
        roc_metrics = {}
        
        if n_classes == 2:
            # Binary classification
            roc_metrics['auc_roc'] = roc_auc_score(y_true, y_proba[:, 1])
            fpr, tpr, thresholds = roc_curve(y_true, y_proba[:, 1])
            roc_metrics['fpr'] = fpr.tolist()
            roc_metrics['tpr'] = tpr.tolist()
            roc_metrics['thresholds'] = thresholds.tolist()
        else:
            # Multi-class classification
            try:
                roc_metrics['auc_roc_ovr'] = roc_auc_score(
                    y_true, y_proba, multi_class='ovr', average='weighted'
                )
                roc_metrics['auc_roc_ovo'] = roc_auc_score(
                    y_true, y_proba, multi_class='ovo', average='weighted'
                )
            except Exception as e:
                logger.warning(f"Could not calculate multi-class AUC: {e}")
        
        return roc_metrics
    
    def plot_confusion_matrix(
        self,
        X: np.ndarray,
        y: np.ndarray,
        normalize: bool = False,
        save_path: Optional[str] = None,
        figsize: Tuple[int, int] = (10, 8)
    ) -> None:
        """Plot confusion matrix.
        
        Args:
            X: Test features.
            y: True labels.
            normalize: Whether to normalize the confusion matrix.
            save_path: Path to save the plot.
            figsize: Figure size.
        """
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        y_pred = self.model.predict(X)
        cm = confusion_matrix(y, y_pred)
        
        if normalize:
            cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
            title = 'Normalized Confusion Matrix'
            fmt = '.2f'
        else:
            title = 'Confusion Matrix'
            fmt = 'd'
        
        plt.figure(figsize=figsize)
        sns.heatmap(
            cm,
            annot=True,
            fmt=fmt,
            cmap='Blues',
            xticklabels=self.class_names,
            yticklabels=self.class_names
        )
        plt.title(title)
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
        plt.tight_layout()
        
        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"Confusion matrix saved to {save_path}")
        
        plt.close()
    
    def plot_roc_curve(
        self,
        X: np.ndarray,
        y: np.ndarray,
        save_path: Optional[str] = None,
        figsize: Tuple[int, int] = (10, 8)
    ) -> None:
        """Plot ROC curve.
        
        Args:
            X: Test features.
            y: True labels.
            save_path: Path to save the plot.
            figsize: Figure size.
        """
        import matplotlib.pyplot as plt
        from sklearn.preprocessing import label_binarize
        
        y_proba = self.model.predict_proba(X)
        n_classes = y_proba.shape[1]
        
        plt.figure(figsize=figsize)
        
        if n_classes == 2:
            # Binary classification
            fpr, tpr, _ = roc_curve(y, y_proba[:, 1])
            auc = roc_auc_score(y, y_proba[:, 1])
            plt.plot(fpr, tpr, label=f'ROC curve (AUC = {auc:.3f})')
        else:
            # Multi-class - plot for each class
            y_bin = label_binarize(y, classes=range(n_classes))
            
            for i in range(n_classes):
                fpr, tpr, _ = roc_curve(y_bin[:, i], y_proba[:, i])
                auc = roc_auc_score(y_bin[:, i], y_proba[:, i])
                class_name = self.class_names[i] if self.class_names else f'Class {i}'
                plt.plot(fpr, tpr, label=f'{class_name} (AUC = {auc:.3f})')
        
        plt.plot([0, 1], [0, 1], 'k--', label='Random')
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('Receiver Operating Characteristic (ROC) Curve')
        plt.legend(loc='lower right')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"ROC curve saved to {save_path}")
        
        plt.close()
    
    def plot_feature_importance(
        self,
        feature_names: List[str],
        top_n: int = 20,
        save_path: Optional[str] = None,
        figsize: Tuple[int, int] = (12, 8)
    ) -> None:
        """Plot feature importance.
        
        Args:
            feature_names: Names of features.
            top_n: Number of top features to plot.
            save_path: Path to save the plot.
            figsize: Figure size.
        """
        import matplotlib.pyplot as plt
        
        importance = self.model.get_feature_importance()
        
        if importance is None:
            logger.warning("Feature importance not available")
            return
        
        # Sort and get top features
        indices = np.argsort(importance)[::-1][:top_n]
        
        plt.figure(figsize=figsize)
        plt.barh(
            range(len(indices)),
            importance[indices],
            align='center'
        )
        plt.yticks(
            range(len(indices)),
            [feature_names[i] for i in indices]
        )
        plt.xlabel('Feature Importance')
        plt.ylabel('Feature')
        plt.title(f'Top {top_n} Feature Importance')
        plt.tight_layout()
        
        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"Feature importance plot saved to {save_path}")
        
        plt.close()
    
    def generate_report(
        self,
        X: np.ndarray,
        y: np.ndarray,
        output_dir: str
    ) -> str:
        """Generate comprehensive evaluation report.
        
        Args:
            X: Test features.
            y: True labels.
            output_dir: Directory to save report and plots.
            
        Returns:
            Path to the generated report.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Evaluate model
        results = self.evaluate(X, y)
        
        # Generate plots
        self.plot_confusion_matrix(
            X, y,
            save_path=str(output_path / 'confusion_matrix.png')
        )
        
        try:
            self.plot_roc_curve(
                X, y,
                save_path=str(output_path / 'roc_curve.png')
            )
        except Exception as e:
            logger.warning(f"Could not generate ROC curve: {e}")
        
        # Save metrics to JSON
        metrics_path = output_path / 'metrics.json'
        with open(metrics_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Generate HTML report
        report_path = output_path / 'evaluation_report.html'
        self._generate_html_report(results, report_path)
        
        logger.info(f"Evaluation report generated at {report_path}")
        
        return str(report_path)
    
    def _generate_html_report(
        self,
        results: Dict[str, Any],
        report_path: Path
    ) -> None:
        """Generate HTML evaluation report.
        
        Args:
            results: Evaluation results dictionary.
            report_path: Path to save the HTML report.
        """
        metrics = results['metrics']
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Model Evaluation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; border-bottom: 1px solid #ccc; padding-bottom: 10px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }}
        .metric-card {{ background: #f5f5f5; padding: 20px; border-radius: 8px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #2196F3; }}
        .metric-label {{ color: #666; }}
        .images {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }}
        .images img {{ max-width: 100%; border: 1px solid #ddd; border-radius: 4px; }}
    </style>
</head>
<body>
    <h1>Model Evaluation Report</h1>
    
    <h2>Performance Metrics</h2>
    <div class="metrics">
        <div class="metric-card">
            <div class="metric-value">{metrics['accuracy']:.4f}</div>
            <div class="metric-label">Accuracy</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{metrics['precision_weighted']:.4f}</div>
            <div class="metric-label">Precision (Weighted)</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{metrics['recall_weighted']:.4f}</div>
            <div class="metric-label">Recall (Weighted)</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{metrics['f1_weighted']:.4f}</div>
            <div class="metric-label">F1 Score (Weighted)</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{results['n_samples']}</div>
            <div class="metric-label">Test Samples</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{results['n_classes']}</div>
            <div class="metric-label">Number of Classes</div>
        </div>
    </div>
    
    <h2>Visualizations</h2>
    <div class="images">
        <img src="confusion_matrix.png" alt="Confusion Matrix">
        <img src="roc_curve.png" alt="ROC Curve">
    </div>
</body>
</html>"""
        
        with open(report_path, 'w') as f:
            f.write(html_content)
    
    @property
    def evaluation_results(self) -> Dict[str, Any]:
        """Get the latest evaluation results."""
        return self._evaluation_results

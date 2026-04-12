"""Data processing module for machine learning pipeline.

This module provides comprehensive data preprocessing capabilities including
loading, cleaning, feature engineering, and transformation of datasets.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import warnings

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    LabelEncoder,
    MinMaxScaler,
    OneHotEncoder,
    StandardScaler
)

logger = logging.getLogger(__name__)


class DataValidationError(Exception):
    """Exception raised when data validation fails."""
    pass


class DataProcessor:
    """Handles all data preprocessing operations.
    
    This class provides methods for loading, cleaning, transforming,
    and splitting datasets for machine learning tasks.
    
    Attributes:
        categorical_columns: List of categorical column names.
        numerical_columns: List of numerical column names.
        target_column: Name of the target variable.
        preprocessor: Sklearn ColumnTransformer for preprocessing.
        label_encoder: LabelEncoder for target variable.
    
    Example:
        >>> processor = DataProcessor(
        ...     categorical_columns=['category'],
        ...     numerical_columns=['value'],
        ...     target_column='target'
        ... )
        >>> X_train, X_test, y_train, y_test = processor.prepare_data('data.csv')
    """
    
    def __init__(
        self,
        categorical_columns: Optional[List[str]] = None,
        numerical_columns: Optional[List[str]] = None,
        target_column: str = "target",
        test_size: float = 0.2,
        validation_size: float = 0.2,
        random_state: int = 42
    ):
        """Initialize the DataProcessor.
        
        Args:
            categorical_columns: List of categorical column names.
            numerical_columns: List of numerical column names.
            target_column: Name of the target variable.
            test_size: Proportion of data for testing.
            validation_size: Proportion of training data for validation.
            random_state: Random seed for reproducibility.
        """
        self.categorical_columns = categorical_columns or []
        self.numerical_columns = numerical_columns or []
        self.target_column = target_column
        self.test_size = test_size
        self.validation_size = validation_size
        self.random_state = random_state
        
        self.preprocessor: Optional[ColumnTransformer] = None
        self.label_encoder: Optional[LabelEncoder] = None
        self._is_fitted = False
        self._feature_names: List[str] = []
        
        logger.info("DataProcessor initialized")
    
    def load_data(
        self,
        data_path: str,
        file_type: Optional[str] = None
    ) -> pd.DataFrame:
        """Load data from file.
        
        Supports CSV, Excel, and Parquet file formats.
        
        Args:
            data_path: Path to the data file.
            file_type: File type override. If None, inferred from extension.
            
        Returns:
            Loaded DataFrame.
            
        Raises:
            FileNotFoundError: If the file doesn't exist.
            ValueError: If the file type is not supported.
        """
        path = Path(data_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {data_path}")
        
        # Infer file type from extension
        if file_type is None:
            file_type = path.suffix.lower().replace('.', '')
        
        logger.info(f"Loading data from {data_path}")
        
        try:
            if file_type == 'csv':
                df = pd.read_csv(data_path)
            elif file_type in ['xlsx', 'xls']:
                df = pd.read_excel(data_path)
            elif file_type == 'parquet':
                df = pd.read_parquet(data_path)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            logger.info(f"Data loaded successfully: {df.shape[0]} rows, {df.shape[1]} columns")
            return df
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise
    
    def validate_data(
        self,
        df: pd.DataFrame,
        check_missing: bool = True,
        check_duplicates: bool = True,
        check_target: bool = True
    ) -> Dict[str, Any]:
        """Validate the loaded data.
        
        Performs various data quality checks and returns a report.
        
        Args:
            df: DataFrame to validate.
            check_missing: Whether to check for missing values.
            check_duplicates: Whether to check for duplicate rows.
            check_target: Whether to check if target column exists.
            
        Returns:
            Dictionary containing validation results.
            
        Raises:
            DataValidationError: If critical validation issues are found.
        """
        validation_results = {
            'valid': True,
            'shape': df.shape,
            'issues': []
        }
        
        # Check if DataFrame is empty
        if df.empty:
            validation_results['valid'] = False
            validation_results['issues'].append('DataFrame is empty')
            raise DataValidationError('DataFrame is empty')
        
        # Check target column
        if check_target and self.target_column not in df.columns:
            validation_results['valid'] = False
            validation_results['issues'].append(
                f"Target column '{self.target_column}' not found"
            )
        
        # Check missing values
        if check_missing:
            missing = df.isnull().sum()
            missing_pct = (missing / len(df) * 100).round(2)
            high_missing = missing_pct[missing_pct > 50]
            
            if len(high_missing) > 0:
                validation_results['issues'].append(
                    f"Columns with >50% missing: {high_missing.to_dict()}"
                )
            
            validation_results['missing_values'] = missing[missing > 0].to_dict()
        
        # Check duplicates
        if check_duplicates:
            duplicates = df.duplicated().sum()
            if duplicates > 0:
                validation_results['issues'].append(
                    f"Found {duplicates} duplicate rows ({duplicates/len(df)*100:.2f}%)"
                )
            validation_results['duplicates'] = duplicates
        
        # Log validation results
        if validation_results['issues']:
            logger.warning(f"Data validation issues: {validation_results['issues']}")
        else:
            logger.info("Data validation passed")
        
        return validation_results
    
    def infer_column_types(
        self,
        df: pd.DataFrame,
        max_categories: int = 10
    ) -> Tuple[List[str], List[str]]:
        """Infer categorical and numerical columns.
        
        Args:
            df: Input DataFrame.
            max_categories: Maximum unique values for a column to be considered categorical.
            
        Returns:
            Tuple of (categorical_columns, numerical_columns).
        """
        categorical = []
        numerical = []
        
        for col in df.columns:
            if col == self.target_column:
                continue
            
            if df[col].dtype == 'object' or df[col].nunique() <= max_categories:
                categorical.append(col)
            else:
                numerical.append(col)
        
        logger.info(f"Inferred {len(categorical)} categorical and {len(numerical)} numerical columns")
        return categorical, numerical
    
    def create_preprocessor(
        self,
        numerical_strategy: str = 'median',
        categorical_strategy: str = 'most_frequent',
        scaling: str = 'standard'
    ) -> ColumnTransformer:
        """Create a preprocessing pipeline.
        
        Args:
            numerical_strategy: Strategy for numerical imputation ('mean', 'median', 'constant').
            categorical_strategy: Strategy for categorical imputation.
            scaling: Scaling method ('standard', 'minmax', 'none').
            
        Returns:
            Configured ColumnTransformer.
        """
        # Numerical transformer
        numerical_steps = [
            ('imputer', SimpleImputer(strategy=numerical_strategy))
        ]
        
        if scaling == 'standard':
            numerical_steps.append(('scaler', StandardScaler()))
        elif scaling == 'minmax':
            numerical_steps.append(('scaler', MinMaxScaler()))
        
        numerical_transformer = Pipeline(steps=numerical_steps)
        
        # Categorical transformer
        categorical_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy=categorical_strategy, fill_value='missing')),
            ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
        ])
        
        # Create column transformer
        transformers = []
        
        if self.numerical_columns:
            transformers.append(('num', numerical_transformer, self.numerical_columns))
        
        if self.categorical_columns:
            transformers.append(('cat', categorical_transformer, self.categorical_columns))
        
        self.preprocessor = ColumnTransformer(
            transformers=transformers,
            remainder='drop'
        )
        
        logger.info("Preprocessor created successfully")
        return self.preprocessor
    
    def fit_transform(
        self,
        df: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Fit preprocessor and transform data.
        
        Args:
            df: Input DataFrame.
            
        Returns:
            Tuple of (features, target) arrays.
        """
        # Infer column types if not specified
        if not self.categorical_columns and not self.numerical_columns:
            self.categorical_columns, self.numerical_columns = self.infer_column_types(df)
        
        # Create preprocessor if not exists
        if self.preprocessor is None:
            self.create_preprocessor()
        
        # Separate features and target
        X = df.drop(columns=[self.target_column])
        y = df[self.target_column]
        
        # Encode target if categorical
        if y.dtype == 'object':
            self.label_encoder = LabelEncoder()
            y = self.label_encoder.fit_transform(y)
            logger.info(f"Target encoded: {self.label_encoder.classes_.tolist()}")
        
        # Fit and transform features
        X_transformed = self.preprocessor.fit_transform(X)
        self._is_fitted = True
        
        # Get feature names
        self._feature_names = self._get_feature_names()
        
        logger.info(f"Data transformed: {X_transformed.shape}")
        return X_transformed, y
    
    def transform(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Transform data using fitted preprocessor.
        
        Args:
            df: Input DataFrame.
            
        Returns:
            Tuple of (features, target) arrays.
            
        Raises:
            ValueError: If preprocessor is not fitted.
        """
        if not self._is_fitted:
            raise ValueError("Preprocessor must be fitted before transform")
        
        X = df.drop(columns=[self.target_column])
        y = df[self.target_column]
        
        if self.label_encoder is not None:
            y = self.label_encoder.transform(y)
        
        X_transformed = self.preprocessor.transform(X)
        
        return X_transformed, y
    
    def _get_feature_names(self) -> List[str]:
        """Get feature names after transformation.
        
        Returns:
            List of feature names.
        """
        feature_names = []
        
        for name, transformer, columns in self.preprocessor.transformers_:
            if name == 'remainder' or transformer == 'drop':
                continue
            
            if hasattr(transformer, 'get_feature_names_out'):
                names = transformer.get_feature_names_out(columns)
            else:
                names = columns
            
            feature_names.extend(names)
        
        return feature_names
    
    def split_data(
        self,
        X: np.ndarray,
        y: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Split data into training and testing sets.
        
        Args:
            X: Feature array.
            y: Target array.
            
        Returns:
            Tuple of (X_train, X_test, y_train, y_test).
        """
        from sklearn.model_selection import train_test_split
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=self.test_size,
            random_state=self.random_state,
            stratify=y if len(np.unique(y)) > 1 else None
        )
        
        logger.info(
            f"Data split - Train: {X_train.shape[0]}, Test: {X_test.shape[0]}"
        )
        
        return X_train, X_test, y_train, y_test
    
    def prepare_data(
        self,
        data_path: str,
        validate: bool = True
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Complete data preparation pipeline.
        
        Loads, validates, transforms, and splits data.
        
        Args:
            data_path: Path to the data file.
            validate: Whether to validate data before processing.
            
        Returns:
            Tuple of (X_train, X_test, y_train, y_test).
        """
        # Load data
        df = self.load_data(data_path)
        
        # Validate data
        if validate:
            self.validate_data(df)
        
        # Transform data
        X, y = self.fit_transform(df)
        
        # Split data
        return self.split_data(X, y)
    
    @property
    def feature_names(self) -> List[str]:
        """Get the feature names after transformation."""
        return self._feature_names
    
    def save_preprocessor(self, path: str) -> None:
        """Save the fitted preprocessor to disk.
        
        Args:
            path: Path to save the preprocessor.
        """
        import joblib
        
        if not self._is_fitted:
            raise ValueError("Preprocessor must be fitted before saving")
        
        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        joblib.dump({
            'preprocessor': self.preprocessor,
            'label_encoder': self.label_encoder,
            'feature_names': self._feature_names,
            'categorical_columns': self.categorical_columns,
            'numerical_columns': self.numerical_columns
        }, save_path)
        
        logger.info(f"Preprocessor saved to {path}")
    
    def load_preprocessor(self, path: str) -> None:
        """Load a fitted preprocessor from disk.
        
        Args:
            path: Path to the saved preprocessor.
        """
        import joblib
        
        data = joblib.load(path)
        
        self.preprocessor = data['preprocessor']
        self.label_encoder = data['label_encoder']
        self._feature_names = data['feature_names']
        self.categorical_columns = data['categorical_columns']
        self.numerical_columns = data['numerical_columns']
        self._is_fitted = True
        
        logger.info(f"Preprocessor loaded from {path}")

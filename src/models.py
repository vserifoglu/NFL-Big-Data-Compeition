"""
Machine learning models for execution gap analysis.

Implements logistic regression to predict expected completion rate
and calculate execution gap (actual - expected).
"""

import numpy as np
from sklearn.linear_model import LogisticRegression
from typing import Dict


class ExecutionGapModel:
    """
    Model to predict expected completion rate and calculate execution gap.
    
    Uses logistic regression to model completion probability based on
    positioning metrics (SQI, BAA). Execution gap measures how much
    better or worse the actual outcome was compared to expectation.
    """
    
    def __init__(self):
        self.model = LogisticRegression(random_state=42)
        self.is_fitted = False
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """
        Train the model on historical plays.
        
        Args:
            X: Feature matrix (n_samples, n_features)
            y: Target values (n_samples,) - 1=complete, 0=incomplete
            
        Returns:
            Dictionary with training metrics (accuracy, etc.)
        """
        if len(X) == 0:
            raise ValueError("No valid training data")
        
        # Train model
        self.model.fit(X, y)
        self.is_fitted = True
        
        # Calculate training accuracy
        train_accuracy = self.model.score(X, y)
        
        return {
            'accuracy': train_accuracy,
            'n_samples': len(X)
        }
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Predict completion probability for plays.
        
        Args:
            X: Feature matrix (n_samples, n_features)
            
        Returns:
            Array of completion probabilities (0-1)
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        probabilities = self.model.predict_proba(X)[:, 1]  # Probability of class 1 (completion)
        
        return probabilities
    
    def calculate_execution_gap(
        self, 
        actual_outcomes: np.ndarray,
        expected_outcomes: np.ndarray
    ) -> np.ndarray:
        """
        Calculate execution gap for all plays.
        
        Execution Gap = Actual Outcome - Expected Outcome
        - Positive gap: Over-performance (clutch plays)
        - Negative gap: Under-performance (missed opportunities)
        
        Args:
            actual_outcomes: Array of actual outcomes (1/0)
            expected_outcomes: Array of expected probabilities (0-1)
            
        Returns:
            Array of execution gaps
        """
        return actual_outcomes - expected_outcomes

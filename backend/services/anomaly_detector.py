import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import os

class AnomalyDetector:
    """
    ML-based anomaly detection for code files using Isolation Forest.
    Detects outliers in code metrics (complexity, size, documentation, etc.)
    """
    
    def __init__(self):
        self.model = IsolationForest(
            contamination=0.1,  # Expect 10% of files to be anomalous
            random_state=42,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self.feature_names = []
    
    def extract_features(self, nlp_analyses):
        """
        Extract numerical features from NLP analysis results.
        Returns: feature matrix (n_files x n_features)
        """
        features = []
        
        for analysis in nlp_analyses:
            metrics = analysis.get('metrics', {})
            naming = analysis.get('naming', {})
            semantic = analysis.get('semantic', {})
            
            file_features = [
                metrics.get('total_lines', 0),
                metrics.get('non_empty_lines', 0),
                metrics.get('comment_lines', 0),
                metrics.get('comment_ratio', 0),
                metrics.get('avg_complexity', 0),
                metrics.get('max_complexity', 0),
                metrics.get('maintainability_index', 0),
                metrics.get('halstead_difficulty', 0),
                len(analysis.get('smells', [])),  # Code smell count
                naming.get('consistency_score', 0),
                semantic.get('vocabulary_richness', 0),
                semantic.get('comment_meaningfulness', 0),
            ]
            
            features.append(file_features)
        
        self.feature_names = [
            'total_lines', 'non_empty_lines', 'comment_lines', 'comment_ratio',
            'avg_complexity', 'max_complexity', 'maintainability_index',
            'halstead_difficulty', 'smell_count', 'naming_consistency',
            'vocabulary_richness', 'comment_meaningfulness'
        ]
        
        return np.array(features)
    
    def detect_anomalies(self, nlp_analyses):
        """
        Detect anomalous files based on their metrics.
        Returns: list of anomaly reports
        """
        if not nlp_analyses or len(nlp_analyses) < 3:
            return []  # Need at least 3 files for meaningful anomaly detection
        
        # Extract features
        features = self.extract_features(nlp_analyses)
        
        # Handle missing values
        features = np.nan_to_num(features, nan=0.0)
        
        # Normalize features
        features_scaled = self.scaler.fit_transform(features)
        
        # Fit model and predict
        predictions = self.model.fit_predict(features_scaled)
        anomaly_scores = self.model.score_samples(features_scaled)
        
        # Generate anomaly reports
        anomalies = []
        for i, (pred, score, analysis) in enumerate(zip(predictions, anomaly_scores, nlp_analyses)):
            if pred == -1:  # Anomaly detected
                anomaly = self._create_anomaly_report(
                    analysis, 
                    features[i], 
                    score,
                    features
                )
                anomalies.append(anomaly)
        
        # Sort by severity (most anomalous first)
        anomalies.sort(key=lambda x: x['score'], reverse=True)
        
        return anomalies
    
    def _create_anomaly_report(self, analysis, file_features, anomaly_score, all_features):
        """Create detailed anomaly report for a file."""
        filename = analysis.get('filename', 'unknown')
        
        # Convert anomaly score to 0-100 scale (lower score = more anomalous)
        # Isolation Forest scores are typically between -0.5 and 0.5
        normalized_score = int((1 - (anomaly_score + 0.5)) * 100)
        normalized_score = max(0, min(100, normalized_score))
        
        # Identify specific anomaly types
        anomaly_types = []
        reasons = []
        
        # Calculate feature averages for comparison
        feature_means = np.mean(all_features, axis=0)
        feature_stds = np.std(all_features, axis=0)
        
        for i, (feature_name, value, mean, std) in enumerate(zip(
            self.feature_names, file_features, feature_means, feature_stds
        )):
            if std > 0:
                z_score = abs((value - mean) / std)
                
                if z_score > 2:  # More than 2 standard deviations
                    if feature_name == 'avg_complexity' and value > mean:
                        anomaly_types.append('complexity')
                        reasons.append(f"High complexity ({value:.1f} vs avg {mean:.1f})")
                    elif feature_name == 'total_lines' and value > mean:
                        anomaly_types.append('size')
                        reasons.append(f"Large file ({int(value)} lines vs avg {int(mean)})")
                    elif feature_name == 'comment_ratio' and value < mean:
                        anomaly_types.append('documentation')
                        reasons.append(f"Low documentation ({value:.1%} vs avg {mean:.1%})")
                    elif feature_name == 'naming_consistency' and value < mean:
                        anomaly_types.append('naming')
                        reasons.append(f"Inconsistent naming (score {value:.2f} vs avg {mean:.2f})")
                    elif feature_name == 'smell_count' and value > mean:
                        anomaly_types.append('code_smells')
                        reasons.append(f"Multiple code smells ({int(value)} detected)")
        
        return {
            'file': filename,
            'score': normalized_score,
            'types': anomaly_types if anomaly_types else ['general'],
            'description': '; '.join(reasons) if reasons else 'Statistical outlier in code metrics',
            'metrics': {
                'complexity': file_features[4],
                'lines': int(file_features[0]),
                'comment_ratio': file_features[3],
                'smells': int(file_features[8])
            }
        }

def detect_code_anomalies(nlp_analyses):
    """
    Convenience function to detect anomalies.
    """
    detector = AnomalyDetector()
    return detector.detect_anomalies(nlp_analyses)

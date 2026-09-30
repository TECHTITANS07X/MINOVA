"""
Anomaly detection using Isolation Forest + XGBoost.
Flags unusual production/OB values based on historical patterns.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

import numpy as np
import structlog

logger = structlog.get_logger()


@dataclass
class AnomalyResult:
    metric: str
    expected_value: float
    actual_value: float
    anomaly_score: float
    contributing_features: dict[str, float]
    explanation: str


class AnomalyDetector:
    def __init__(self) -> None:
        self._isolation_forest = None
        self._xgboost_model = None
        self._feature_names: list[str] = []
        self._fitted = False

    def fit(self, historical_data: np.ndarray, feature_names: list[str]) -> None:
        from sklearn.ensemble import IsolationForest
        from sklearn.preprocessing import StandardScaler

        self._feature_names = feature_names
        self._scaler = StandardScaler()
        scaled = self._scaler.fit_transform(historical_data)

        self._isolation_forest = IsolationForest(
            n_estimators=200,
            contamination=0.05,
            random_state=42,
        )
        self._isolation_forest.fit(scaled)
        self._fitted = True
        logger.info("anomaly.model_fitted", features=len(feature_names), samples=len(historical_data))

    def detect(self, observation: dict[str, float]) -> list[AnomalyResult]:
        if not self._fitted:
            return []

        features = np.array([[observation.get(f, 0.0) for f in self._feature_names]])
        scaled = self._scaler.transform(features)

        raw_score = self._isolation_forest.decision_function(scaled)[0]
        prediction = self._isolation_forest.predict(scaled)[0]

        anomaly_score = max(0.0, min(1.0, 0.5 - raw_score))

        results = []
        if prediction == -1 and anomaly_score > 0.5:
            contributing = self._compute_feature_contributions(scaled[0])

            for metric in ["production_tonnes", "overburden_m3"]:
                if metric in observation and metric in self._feature_names:
                    idx = self._feature_names.index(metric)
                    z_score = abs(scaled[0][idx])
                    if z_score > 1.5:
                        results.append(AnomalyResult(
                            metric=metric,
                            expected_value=float(self._scaler.mean_[idx]),
                            actual_value=observation[metric],
                            anomaly_score=anomaly_score,
                            contributing_features=contributing,
                            explanation=self._generate_explanation(metric, observation[metric], self._scaler.mean_[idx], z_score),
                        ))

        return results

    def _compute_feature_contributions(self, scaled_obs: np.ndarray) -> dict[str, float]:
        contributions = {}
        for i, name in enumerate(self._feature_names):
            contributions[name] = round(abs(float(scaled_obs[i])) / (sum(abs(scaled_obs)) + 1e-10), 4)
        return dict(sorted(contributions.items(), key=lambda x: x[1], reverse=True)[:5])

    def _generate_explanation(self, metric: str, actual: float, expected: float, z_score: float) -> str:
        direction = "below" if actual < expected else "above"
        pct = abs(actual - expected) / max(expected, 1) * 100
        return (
            f"{metric.replace('_', ' ').title()} is {pct:.1f}% {direction} the historical average "
            f"({actual:,.0f} vs expected {expected:,.0f}). "
            f"Statistical deviation: {z_score:.1f} standard deviations."
        )


_detector = AnomalyDetector()


def get_detector() -> AnomalyDetector:
    return _detector

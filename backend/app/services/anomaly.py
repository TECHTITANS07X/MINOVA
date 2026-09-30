from __future__ import annotations

import pickle
from dataclasses import dataclass
from typing import Any

import numpy as np
import structlog

logger = structlog.get_logger()


@dataclass
class AnomalyResult:
    is_anomaly: bool
    score: float
    method: str
    explanation: str


def train_model(values: list[float], contamination: float = 0.05) -> bytes:
    from sklearn.ensemble import IsolationForest

    arr = np.array(values).reshape(-1, 1)
    model = IsolationForest(contamination=contamination, random_state=42, n_estimators=100)
    model.fit(arr)
    return pickle.dumps(model)


def detect_anomalies(model_bytes: bytes, values: list[float], threshold: float = -0.3) -> list[dict]:
    model = pickle.loads(model_bytes)  # noqa: S301
    arr = np.array(values).reshape(-1, 1)
    scores = model.decision_function(arr)
    results = []
    for i, (val, score) in enumerate(zip(values, scores)):
        if score < threshold:
            results.append({"index": i, "value": val, "score": float(score), "is_anomaly": True})
    return results


def check_value_zscore(value: float, historical: list[float]) -> AnomalyResult:
    if len(historical) < 5:
        return AnomalyResult(is_anomaly=False, score=0.0, method="insufficient_data", explanation="Need at least 5 historical values")
    arr = np.array(historical)
    mean, std = arr.mean(), arr.std()
    if std < 1e-9:
        return AnomalyResult(is_anomaly=False, score=0.0, method="zscore", explanation="Zero variance in historical data")
    z = (value - mean) / std
    is_anomaly = abs(z) > 3.0
    explanation = f"Z-score={z:.2f} (mean={mean:.1f}, std={std:.1f})"
    if is_anomaly:
        direction = "above" if z > 0 else "below"
        explanation += f" — value is {abs(z):.1f}σ {direction} mean"
    return AnomalyResult(is_anomaly=is_anomaly, score=float(abs(z)), method="zscore", explanation=explanation)


def check_value(value: float, historical: list[float], model_bytes: bytes | None = None) -> AnomalyResult:
    if model_bytes and len(historical) >= 20:
        try:
            model = pickle.loads(model_bytes)  # noqa: S301
            arr = np.array([[value]])
            score = float(model.decision_function(arr)[0])
            is_anomaly = score < -0.3
            return AnomalyResult(
                is_anomaly=is_anomaly,
                score=abs(score),
                method="isolation_forest",
                explanation=f"IF score={score:.3f} {'(anomalous)' if is_anomaly else '(normal)'}",
            )
        except Exception:
            logger.warning("anomaly.if_fallback_to_zscore")
    return check_value_zscore(value, historical)

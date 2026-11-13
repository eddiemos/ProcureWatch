from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from .features import build_feature_frame


RISK_THRESHOLDS = {
    "Low": 0.0,
    "Medium": 25.0,
    "High": 55.0,
    "Critical": 80.0,
}


def _normalise(value: float, low: float, high: float) -> float:
    if high == low:
        return 0.0
    return min(100.0, max(0.0, ((value - low) / (high - low)) * 100.0))


def score_procurements(procurement_df: pd.DataFrame) -> pd.DataFrame:
    if procurement_df.empty:
        return procurement_df.copy()

    features = build_feature_frame(procurement_df)
    numeric_cols = [
        "value_for_analysis",
        "supplier_award_count",
        "buyer_award_count",
        "buyer_supplier_frequency",
        "supplier_share_of_total_value",
        "relative_value_vs_supplier_mean",
        "relative_value_vs_buyer_mean",
        "value_zscore",
    ]
    model_input = features[numeric_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)

    model = IsolationForest(contamination=0.1, random_state=42)
    model.fit(model_input)
    anomaly_scores = -model.score_samples(model_input)
    anomaly_min = float(np.min(anomaly_scores))
    anomaly_max = float(np.max(anomaly_scores))

    features["anomaly_score"] = anomaly_scores
    features["anomaly_percent"] = features["anomaly_score"].apply(
        lambda x: _normalise(float(x), anomaly_min, anomaly_max)
    )
    features["risk_score"] = (
        features["anomaly_percent"] * 0.45
        + features["supplier_share_of_total_value"].clip(upper=1.0) * 100.0 * 0.30
        + features["relative_value_vs_supplier_mean"].clip(upper=10.0) * 10.0 * 0.15
        + features["buyer_supplier_frequency"].rank(pct=True, method="average") * 100.0 * 0.10
    )
    features["risk_score"] = features["risk_score"].clip(lower=0.0, upper=100.0)

    def classify(score: float) -> str:
        if score >= RISK_THRESHOLDS["Critical"]:
            return "Critical"
        if score >= RISK_THRESHOLDS["High"]:
            return "High"
        if score >= RISK_THRESHOLDS["Medium"]:
            return "Medium"
        return "Low"

    features["risk_category"] = features["risk_score"].apply(classify)
    features["risk_explanation"] = features.apply(build_explanation, axis=1)
    return features


def build_explanation(row: pd.Series) -> str:
    supplier = row.get("supplier_name") or row.get("supplier_id") or "Unknown supplier"
    buyer = row.get("buyer_name") or row.get("buyer_id") or "Unknown buyer"
    value = row.get("value_for_analysis") or 0.0
    share = row.get("supplier_share_of_total_value") or 0.0
    anomaly = row.get("anomaly_percent") or 0.0
    return (
        f"{supplier} received a large or unusual award value ({value:,.0f} {row.get('currency', 'KES')}) "
        f"for {buyer}. The record sits at {anomaly:.1f}% of the anomaly profile, "
        f"and the supplier's share of total procurement value is {share * 100:.1f}%."
    )


def build_risk_summary(scored_df: pd.DataFrame) -> dict[str, Any]:
    if scored_df.empty:
        return {"total_records": 0, "flagged_records": 0, "distribution": {}}

    distribution = scored_df["risk_category"].value_counts().to_dict()
    flagged = int(scored_df[scored_df["risk_score"] >= 55].shape[0])
    return {
        "total_records": int(len(scored_df)),
        "flagged_records": flagged,
        "distribution": distribution,
        "average_risk_score": round(float(scored_df["risk_score"].mean()), 2),
    }

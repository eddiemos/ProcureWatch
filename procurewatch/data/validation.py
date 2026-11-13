from __future__ import annotations

from typing import Any

import pandas as pd
import pandera.pandas as pa


PROCUREMENT_SCHEMA = pa.DataFrameSchema(
    {
        "ocid": pa.Column(pa.String, nullable=False),
        "buyer_name": pa.Column(pa.String, nullable=True),
        "buyer_id": pa.Column(pa.String, nullable=True),
        "supplier_name": pa.Column(pa.String, nullable=True),
        "supplier_id": pa.Column(pa.String, nullable=True),
        "award_value": pa.Column(pa.Float, nullable=True),
        "contract_value": pa.Column(pa.Float, nullable=True),
        "currency": pa.Column(pa.String, nullable=True),
        "award_date": pa.Column(pa.String, nullable=True),
        "procurement_method": pa.Column(pa.String, nullable=True),
        "category": pa.Column(pa.String, nullable=True),
        "source_file": pa.Column(pa.String, nullable=True),
        "raw_record": pa.Column(pa.String, nullable=True),
    },
    strict=False,
    coerce=True,
)


def validate_procurement_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    if df.empty:
        return df.copy(), {"row_count": 0, "valid_rows": 0, "invalid_rows": 0, "missing_ratio": 0.0}

    working = df.copy()
    working["ocid"] = working["ocid"].fillna("missing-ocid")
    working["award_value"] = pd.to_numeric(working.get("award_value"), errors="coerce")
    working["contract_value"] = pd.to_numeric(working.get("contract_value"), errors="coerce")

    missing = working.isna().mean().to_dict()
    valid = working[working["ocid"].astype(str).str.strip() != "missing-ocid"].copy()
    invalid = working[working["ocid"].astype(str).str.strip() == "missing-ocid"].copy()
    report = {
        "row_count": int(len(working)),
        "valid_rows": int(len(valid)),
        "invalid_rows": int(len(invalid)),
        "missing_ratio": float(working.isna().sum().sum() / (working.shape[0] * working.shape[1])) if working.shape[0] else 0.0,
        "missing_by_column": missing,
    }

    try:
        valid = PROCUREMENT_SCHEMA.validate(valid, lazy=True)
    except pa.errors.SchemaError as exc:
        report["schema_error"] = str(exc)
    return valid, report


def data_quality_summary(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {"row_count": 0, "quality_score": 100.0, "missing_values": {}}
    summary = df.isna().sum().to_dict()
    quality_score = max(0.0, 100.0 - (sum(summary.values()) / (len(df) * max(1, len(df.columns))) * 100.0))
    return {"row_count": int(len(df)), "quality_score": round(float(quality_score), 2), "missing_values": summary}

from __future__ import annotations

import numpy as np
import pandas as pd


def build_feature_frame(procurement_df: pd.DataFrame) -> pd.DataFrame:
    if procurement_df.empty:
        return procurement_df.copy()

    frame = procurement_df.copy()
    frame["award_value"] = pd.to_numeric(frame.get("award_value"), errors="coerce").fillna(0.0)
    frame["contract_value"] = pd.to_numeric(frame.get("contract_value"), errors="coerce").fillna(0.0)
    frame["value_for_analysis"] = frame[["award_value", "contract_value"]].max(axis=1)

    frame["supplier_award_count"] = frame.groupby("supplier_id")["ocid"].transform("count")
    frame["buyer_award_count"] = frame.groupby("buyer_id")["ocid"].transform("count")
    frame["buyer_supplier_frequency"] = frame.groupby(["buyer_id", "supplier_id"])["ocid"].transform("count")
    frame["supplier_total_value"] = frame.groupby("supplier_id")["value_for_analysis"].transform("sum")
    frame["buyer_total_value"] = frame.groupby("buyer_id")["value_for_analysis"].transform("sum")
    frame["supplier_mean_value"] = frame.groupby("supplier_id")["value_for_analysis"].transform("mean")
    frame["buyer_mean_value"] = frame.groupby("buyer_id")["value_for_analysis"].transform("mean")
    frame["supplier_share_of_total_value"] = frame["value_for_analysis"] / frame["supplier_total_value"].replace(0, np.nan)
    frame["relative_value_vs_supplier_mean"] = frame["value_for_analysis"] / frame["supplier_mean_value"].replace(0, np.nan)
    frame["relative_value_vs_buyer_mean"] = frame["value_for_analysis"] / frame["buyer_mean_value"].replace(0, np.nan)
    value_std = float(frame["value_for_analysis"].std(ddof=0))
    frame["value_zscore"] = (frame["value_for_analysis"] - frame["value_for_analysis"].mean()) / (value_std if value_std else np.nan)

    frame["supplier_share_of_total_value"] = frame["supplier_share_of_total_value"].fillna(0.0)
    frame["relative_value_vs_supplier_mean"] = frame["relative_value_vs_supplier_mean"].fillna(1.0)
    frame["relative_value_vs_buyer_mean"] = frame["relative_value_vs_buyer_mean"].fillna(1.0)
    frame["value_zscore"] = frame["value_zscore"].fillna(0.0)
    return frame

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from procurewatch.analysis import build_risk_summary, score_procurements
from procurewatch.config import DATA_DIR
from procurewatch.data import load_procurement_dataframe, validate_procurement_dataframe
from procurewatch.data.ingestion import normalise_procurement_record


def _find_dataset() -> str | None:
    for filename in ("2024.jsonl", "procurements.jsonl"):
        path = DATA_DIR / filename
        if path.exists():
            return str(path)
    return None


def demo_data() -> pd.DataFrame:
    records = [
        {
            "ocid": "ocds-101",
            "buyer": {"name": "Ministry of Transport", "id": "buyer-a"},
            "tender": {"procurementMethod": "Open Tender", "mainProcurementCategory": "Transport"},
            "awards": [{"date": "2024-02-15", "value": {"amount": 1200000, "currency": "KES"}, "suppliers": [{"name": "RoadWorks Ltd", "id": "supplier-a"}]}],
            "contracts": [{"value": {"amount": 1200000, "currency": "KES"}}],
        },
        {
            "ocid": "ocds-102",
            "buyer": {"name": "Ministry of Transport", "id": "buyer-a"},
            "tender": {"procurementMethod": "Open Tender", "mainProcurementCategory": "Transport"},
            "awards": [{"date": "2024-03-18", "value": {"amount": 1800000, "currency": "KES"}, "suppliers": [{"name": "RoadWorks Ltd", "id": "supplier-a"}]}],
            "contracts": [{"value": {"amount": 1800000, "currency": "KES"}}],
        },
        {
            "ocid": "ocds-103",
            "buyer": {"name": "Aviation Authority", "id": "buyer-b"},
            "tender": {"procurementMethod": "Open Tender", "mainProcurementCategory": "Infrastructure"},
            "awards": [{"date": "2024-05-10", "value": {"amount": 45000000, "currency": "KES"}, "suppliers": [{"name": "SkyBuild Kenya", "id": "supplier-b"}]}],
            "contracts": [{"value": {"amount": 45000000, "currency": "KES"}}],
        },
    ]
    return pd.DataFrame([normalise_procurement_record(r) for r in records])


@st.cache_resource(show_spinner="Loading and analysing procurement data...")
def load_dashboard_data(data_path: str | None, modified_at: float | None) -> tuple[pd.DataFrame, dict]:
    dataset = load_procurement_dataframe(data_path) if data_path else demo_data()
    cleaned, report = validate_procurement_dataframe(dataset)
    return score_procurements(cleaned), report


def main() -> None:
    st.set_page_config(page_title="ProcureWatch Dashboard", page_icon="📊", layout="wide")
    st.title("ProcureWatch Dashboard")

    data_path = _find_dataset()
    modified_at = Path(data_path).stat().st_mtime if data_path else None
    scored, report = load_dashboard_data(data_path, modified_at)
    summary = build_risk_summary(scored)
    if data_path:
        st.caption(f"Data source: `{data_path}`")
    else:
        st.warning("No procurement JSONL file found in the data folder; showing demonstration records.")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Procurement records", len(scored))
    col2.metric("High risk", summary["flagged_records"])
    col3.metric("Average risk score", f"{summary['average_risk_score']:.1f}")
    col4.metric("Data quality", f"{report['missing_ratio'] * 100:.1f}% missing")

    tabs = st.tabs(["Overview", "Risk monitoring", "Procurement explorer", "Data quality"])
    with tabs[0]:
        st.subheader("Overview")
        st.bar_chart(scored["risk_category"].value_counts().rename_axis("Risk category").reset_index(name="count"))
    with tabs[1]:
        st.subheader("Flagged transactions")
        st.dataframe(scored.sort_values("risk_score", ascending=False)[["ocid", "buyer_name", "supplier_name", "value_for_analysis", "risk_score", "risk_category"]])
    with tabs[2]:
        st.subheader("Explorer")
        st.dataframe(scored[["ocid", "buyer_name", "supplier_name", "currency", "value_for_analysis", "risk_score", "risk_category"]])
    with tabs[3]:
        st.subheader("Data quality")
        st.json(report)


if __name__ == "__main__":
    main()

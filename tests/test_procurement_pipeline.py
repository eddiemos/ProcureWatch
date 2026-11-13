from __future__ import annotations

import pandas as pd

from procurewatch.analysis import build_risk_summary, score_procurements
from procurewatch.analysis.features import build_feature_frame
from procurewatch.data import normalise_procurement_record, validate_procurement_dataframe


def _build_sample_data() -> list[dict]:
    return [
        {
            "ocid": "ocds-010",
            "buyer": {"name": "Ministry of Health", "id": "buyer-1"},
            "tender": {"procurementMethod": "Open Tender", "mainProcurementCategory": "Medical"},
            "awards": [{"date": "2024-04-01", "value": {"amount": 500000, "currency": "KES"}, "suppliers": [{"name": "Alpha Medics", "id": "supplier-1"}]}],
            "contracts": [{"value": {"amount": 500000, "currency": "KES"}}],
        },
        {
            "ocid": "ocds-011",
            "buyer": {"name": "Ministry of Health", "id": "buyer-1"},
            "tender": {"procurementMethod": "Open Tender", "mainProcurementCategory": "Medical"},
            "awards": [{"date": "2024-04-02", "value": {"amount": 600000, "currency": "KES"}, "suppliers": [{"name": "Alpha Medics", "id": "supplier-1"}]}],
            "contracts": [{"value": {"amount": 600000, "currency": "KES"}}],
        },
        {
            "ocid": "ocds-012",
            "buyer": {"name": "County Government", "id": "buyer-2"},
            "tender": {"procurementMethod": "Open Tender", "mainProcurementCategory": "Infrastructure"},
            "awards": [{"date": "2024-04-05", "value": {"amount": 3000000, "currency": "KES"}, "suppliers": [{"name": "BuildFast Ltd", "id": "supplier-2"}]}],
            "contracts": [{"value": {"amount": 3000000, "currency": "KES"}}],
        },
        {
            "ocid": "ocds-013",
            "buyer": {"name": "County Government", "id": "buyer-2"},
            "tender": {"procurementMethod": "Direct", "mainProcurementCategory": "Infrastructure"},
            "awards": [{"date": "2024-04-09", "value": {"amount": 18000000, "currency": "KES"}, "suppliers": [{"name": "BuildFast Ltd", "id": "supplier-2"}]}],
            "contracts": [{"value": {"amount": 18000000, "currency": "KES"}}],
        },
    ]


def test_normalise_procurement_record() -> None:
    record = _build_sample_data()[0]
    normalised = normalise_procurement_record(record)

    assert normalised["buyer_name"] == "Ministry of Health"
    assert normalised["supplier_name"] == "Alpha Medics"
    assert normalised["award_value"] == 500000.0
    assert normalised["currency"] == "KES"


def test_validation_and_risk_scoring() -> None:
    records = [normalise_procurement_record(raw) for raw in _build_sample_data()]
    df = pd.DataFrame(records)
    valid_df, report = validate_procurement_dataframe(df)

    assert len(valid_df) == 4
    assert "missing_ratio" in report

    features = build_feature_frame(valid_df)
    scored = score_procurements(valid_df)
    summary = build_risk_summary(scored)

    assert set(["risk_score", "risk_category", "risk_explanation"]).issubset(scored.columns)
    assert summary["total_records"] == 4
    assert scored["risk_score"].between(0, 100).all()

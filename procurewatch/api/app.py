from __future__ import annotations

from functools import lru_cache
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query

from procurewatch.analysis import build_risk_summary, score_procurements
from procurewatch.analysis.features import build_feature_frame
from procurewatch.config import DATA_DIR
from procurewatch.data import (
    load_procurement_dataframe,
    normalise_procurement_record,
    validate_procurement_dataframe,
)


def _build_demo_records() -> list[dict[str, Any]]:
    return [
        {
            "ocid": "ocds-001",
            "buyer": {"name": "Ministry of Health", "id": "buyer-1"},
            "tender": {"procurementMethod": "Open Tender", "mainProcurementCategory": "Medical Supplies"},
            "awards": [{"date": "2024-02-01", "value": {"amount": 150000, "currency": "KES"}, "suppliers": [{"name": "Alpha Medics", "id": "supplier-1"}]}],
            "contracts": [{"value": {"amount": 150000, "currency": "KES"}}],
        },
        {
            "ocid": "ocds-002",
            "buyer": {"name": "Ministry of Health", "id": "buyer-1"},
            "tender": {"procurementMethod": "Framework", "mainProcurementCategory": "Medical Supplies"},
            "awards": [{"date": "2024-03-15", "value": {"amount": 180000, "currency": "KES"}, "suppliers": [{"name": "Alpha Medics", "id": "supplier-1"}]}],
            "contracts": [{"value": {"amount": 180000, "currency": "KES"}}],
        },
        {
            "ocid": "ocds-003",
            "buyer": {"name": "County Government", "id": "buyer-2"},
            "tender": {"procurementMethod": "Open Tender", "mainProcurementCategory": "Infrastructure"},
            "awards": [{"date": "2024-01-22", "value": {"amount": 2500000, "currency": "KES"}, "suppliers": [{"name": "BuildFast Ltd", "id": "supplier-2"}]}],
            "contracts": [{"value": {"amount": 2500000, "currency": "KES"}}],
        },
        {
            "ocid": "ocds-004",
            "buyer": {"name": "County Government", "id": "buyer-2"},
            "tender": {"procurementMethod": "Direct", "mainProcurementCategory": "Infrastructure"},
            "awards": [{"date": "2024-04-02", "value": {"amount": 18000000, "currency": "KES"}, "suppliers": [{"name": "BuildFast Ltd", "id": "supplier-2"}]}],
            "contracts": [{"value": {"amount": 18000000, "currency": "KES"}}],
        },
    ]


def _load_procurements() -> pd.DataFrame:
    for filename in ("2024.jsonl", "procurements.jsonl"):
        data_path = DATA_DIR / filename
        if data_path.exists():
            return load_procurement_dataframe(data_path)
    return pd.DataFrame([normalise_procurement_record(record) for record in _build_demo_records()])


@lru_cache(maxsize=1)
def _prepare_dataframe() -> tuple:
    records = _load_procurements()
    df = records
    clean_df, report = validate_procurement_dataframe(df)
    scored = score_procurements(clean_df)
    feature_frame = build_feature_frame(clean_df)
    risk_summary = build_risk_summary(scored)
    return clean_df, feature_frame, scored, report, risk_summary


def create_app() -> FastAPI:
    app = FastAPI(title="ProcureWatch API", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "service": "ProcureWatch"}

    @app.get("/stats")
    def stats() -> dict[str, Any]:
        _, _, scored, report, summary = _prepare_dataframe()
        return {"total_procurements": int(len(scored)), "risk_summary": summary, "data_quality": report}

    @app.get("/procurements")
    def procurement_search(
        page: int = Query(1, ge=1),
        per_page: int = Query(25, ge=1, le=100),
        supplier: str | None = None,
        buyer: str | None = None,
    ) -> dict[str, Any]:
        _, _, scored, _, _ = _prepare_dataframe()
        filtered = scored.copy()
        if supplier:
            filtered = filtered[filtered["supplier_name"].astype(str).str.lower().str.contains(supplier.lower())]
        if buyer:
            filtered = filtered[filtered["buyer_name"].astype(str).str.lower().str.contains(buyer.lower())]
        start = (page - 1) * per_page
        end = start + per_page
        return {"page": page, "per_page": per_page, "records": filtered.iloc[start:end].to_dict(orient="records")}

    @app.get("/procurements/{ocid}")
    def procurement_detail(ocid: str) -> dict[str, Any]:
        _, _, scored, _, _ = _prepare_dataframe()
        match = scored[scored["ocid"].astype(str) == ocid]
        if match.empty:
            raise HTTPException(status_code=404, detail="Procurement record not found")
        return match.iloc[0].to_dict()

    @app.get("/suppliers/{supplier_id}")
    def supplier_profile(supplier_id: str) -> dict[str, Any]:
        _, _, scored, _, _ = _prepare_dataframe()
        subset = scored[scored["supplier_id"].astype(str) == supplier_id]
        if subset.empty:
            raise HTTPException(status_code=404, detail="Supplier not found")
        return {
            "supplier_id": supplier_id,
            "supplier_name": subset.iloc[0]["supplier_name"],
            "records": subset.to_dict(orient="records"),
        }

    @app.get("/buyers/{buyer_id}")
    def buyer_profile(buyer_id: str) -> dict[str, Any]:
        _, _, scored, _, _ = _prepare_dataframe()
        subset = scored[scored["buyer_id"].astype(str) == buyer_id]
        if subset.empty:
            raise HTTPException(status_code=404, detail="Buyer not found")
        return {
            "buyer_id": buyer_id,
            "buyer_name": subset.iloc[0]["buyer_name"],
            "records": subset.to_dict(orient="records"),
        }

    @app.get("/high-risk")
    def high_risk_records() -> dict[str, Any]:
        _, _, scored, _, _ = _prepare_dataframe()
        flagged = scored[scored["risk_score"] >= 55].sort_values("risk_score", ascending=False)
        return {"records": flagged.to_dict(orient="records")}

    @app.get("/quality")
    def quality_summary() -> dict[str, Any]:
        _, _, _, report, _ = _prepare_dataframe()
        return {"quality": report}

    return app


app = create_app()

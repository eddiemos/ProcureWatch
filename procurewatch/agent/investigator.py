from __future__ import annotations

from typing import Any

import pandas as pd

try:
    from langgraph.graph import END, START, StateGraph
except ImportError:  # pragma: no cover
    StateGraph = None
    START = END = None


class InvestigationAssistant:
    def __init__(self, procurement_df: pd.DataFrame):
        self.procurement_df = procurement_df.copy()

    def retrieve_record(self, ocid: str) -> dict[str, Any]:
        match = self.procurement_df[self.procurement_df["ocid"].astype(str) == ocid]
        if match.empty:
            return {"facts": [], "status": "no evidence found"}
        return match.iloc[0].to_dict()

    def examine_supplier_history(self, supplier_id: str) -> list[dict[str, Any]]:
        if "supplier_id" not in self.procurement_df.columns:
            return []
        return self.procurement_df[self.procurement_df["supplier_id"].astype(str) == supplier_id].to_dict(orient="records")

    def examine_relationships(self, buyer_id: str, supplier_id: str) -> list[dict[str, Any]]:
        if {"buyer_id", "supplier_id"}.difference(self.procurement_df.columns):
            return []
        mask = (
            self.procurement_df["buyer_id"].astype(str) == buyer_id
        ) & (
            self.procurement_df["supplier_id"].astype(str) == supplier_id
        )
        return self.procurement_df[mask].to_dict(orient="records")

    def generate_summary(self, ocid: str) -> dict[str, Any]:
        record = self.retrieve_record(ocid)
        if not record or record.get("status") == "no evidence found":
            return {"ocid": ocid, "facts": [], "hypotheses": ["No procurement evidence was found for this identifier."], "risk_summary": "No evidence available."}

        if "risk_score" not in record:
            record["risk_score"] = 0.0
        supplier_id = record.get("supplier_id") or "unknown"
        buyer_id = record.get("buyer_id") or "unknown"
        return {
            "ocid": ocid,
            "facts": [
                f"Buyer: {record.get('buyer_name') or buyer_id}",
                f"Supplier: {record.get('supplier_name') or supplier_id}",
                f"Award value: {record.get('value_for_analysis') or record.get('award_value') or 0} {record.get('currency') or 'KES'}",
                f"Risk score: {record.get('risk_score', 0):.1f}",
            ],
            "supporting_records": {
                "supplier_history": self.examine_supplier_history(supplier_id),
                "buyer_supplier_relationships": self.examine_relationships(buyer_id, supplier_id),
            },
            "risk_summary": "This summary is evidence-based and does not assert wrongdoing. It reports the recorded award value, supplier and buyer relationships, and the calculated risk behaviour observed in the dataset.",
            "hypotheses": ["The award stands out relative to supplier or buyer history.", "The buyer-supplier link may be repeated or concentrated."],
        }


def build_investigation_graph() -> Any | None:
    if StateGraph is None:
        return None
    workflow = StateGraph(dict)
    workflow.add_node("retrieve_record", lambda state: {**state, "record": state.get("record")})
    workflow.add_node("analyse_supplier_history", lambda state: {**state, "supplier_history": []})
    workflow.add_node("summarise", lambda state: {**state, "summary": state})
    workflow.add_edge("retrieve_record", "analyse_supplier_history")
    workflow.add_edge("analyse_supplier_history", "summarise")
    workflow.add_edge("summarise", END)
    return workflow.compile()

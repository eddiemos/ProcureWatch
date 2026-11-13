from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Iterator

import pandas as pd

logger = logging.getLogger(__name__)


def _coerce_scalar(value: Any, default: str = "") -> str:
    if value is None or pd.isna(value):
        return default
    return str(value)


def iter_jsonl_records(path: str | Path) -> Iterator[dict[str, Any]]:
    source_path = Path(path)
    with source_path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning("Skipping malformed JSONL record at %s:%d: %s", source_path, line_number, exc)
                continue
            if isinstance(payload, dict):
                yield payload
            else:
                logger.warning("Skipping non-object JSONL record at %s:%d", source_path, line_number)


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return list(iter_jsonl_records(path))


def _read_csv(path: str | Path) -> list[dict[str, Any]]:
    df = pd.read_csv(path)
    return df.to_dict(orient="records")


def load_records(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".jsonl":
        return _read_jsonl(path)
    if suffix == ".csv":
        return _read_csv(path)
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict) and "records" in payload:
            return payload["records"]
    raise ValueError(f"Unsupported procurement source: {path}")


def load_procurement_dataframe(path: str | Path) -> pd.DataFrame:
    source_path = Path(path)
    if source_path.suffix.lower() != ".jsonl":
        raise ValueError(f"Expected a JSONL procurement source: {source_path}")

    records = []
    for raw_record in iter_jsonl_records(source_path):
        normalised = normalise_procurement_record(raw_record)
        normalised["source_file"] = str(source_path)
        records.append(normalised)
    return pd.DataFrame.from_records(records)


def normalise_procurement_record(record: dict[str, Any]) -> dict[str, Any]:
    buyer = record.get("buyer") or {}
    tender = record.get("tender") or {}
    awards = record.get("awards") or []
    contracts = record.get("contracts") or []
    parties = record.get("parties") or []

    if not isinstance(awards, list):
        awards = []
    if not isinstance(contracts, list):
        contracts = []
    if not isinstance(parties, list):
        parties = []

    if isinstance(awards, list) and awards:
        first_award = awards[0]
    else:
        first_award = {}

    if isinstance(contracts, list) and contracts:
        first_contract = contracts[0]
    else:
        first_contract = {}

    buyer_name = _coerce_scalar(buyer.get("name") or buyer.get("buyerName") or buyer.get("identifier", {}).get("legalName"))
    buyer_id = _coerce_scalar(
        buyer.get("id")
        or buyer.get("identifier", {}).get("id")
        or buyer.get("identifier", {}).get("scheme")
        or buyer.get("name")
    )
    supplier = first_award.get("suppliers", [{}])[0] if isinstance(first_award.get("suppliers"), list) and first_award.get("suppliers") else {}
    if not supplier and parties:
        supplier = next((p for p in parties if p.get("roles") and "supplier" in p.get("roles", [])), {})
    supplier_name = _coerce_scalar(supplier.get("name") or supplier.get("identifier", {}).get("legalName"))
    supplier_id = _coerce_scalar(supplier.get("id") or supplier.get("identifier", {}).get("id") or supplier.get("name"))

    award_value = first_award.get("value", {}).get("amount") if isinstance(first_award.get("value"), dict) else first_award.get("amount")
    contract_value = first_contract.get("value", {}).get("amount") if isinstance(first_contract.get("value"), dict) else first_contract.get("amount")
    award_currency = (first_award.get("value") or {}).get("currency") if isinstance(first_award.get("value"), dict) else (first_contract.get("value") or {}).get("currency")
    award_date = record.get("date") or first_award.get("date") or first_contract.get("date") or tender.get("tenderPeriod", {}).get("startDate")

    if award_value is None:
        award_value = contract_value
    if award_currency is None:
        award_currency = "KES"

    normalised = {
        "ocid": _coerce_scalar(record.get("ocid")),
        "buyer_name": buyer_name,
        "buyer_id": buyer_id,
        "supplier_name": supplier_name,
        "supplier_id": supplier_id,
        "award_value": float(award_value) if award_value not in (None, "", "N/A") else None,
        "contract_value": float(contract_value) if contract_value not in (None, "", "N/A") else None,
        "currency": _coerce_scalar(award_currency).upper() or "KES",
        "award_date": _coerce_scalar(award_date),
        "procurement_method": _coerce_scalar(tender.get("procurementMethod") or tender.get("procurementMethodDetails")),
        "category": _coerce_scalar(tender.get("mainProcurementCategory") or record.get("category")),
        "source_file": _coerce_scalar(record.get("source_file")),
        "raw_record": json.dumps(record, default=str),
    }
    return normalised

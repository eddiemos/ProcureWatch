CREATE TABLE IF NOT EXISTS buyers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    buyer_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS suppliers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    sector TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS procurements (
    ocid TEXT PRIMARY KEY,
    buyer_id TEXT REFERENCES buyers(id),
    supplier_id TEXT REFERENCES suppliers(id),
    procurement_method TEXT,
    category TEXT,
    award_value NUMERIC,
    currency TEXT,
    award_date DATE,
    raw_record JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS flags (
    id SERIAL PRIMARY KEY,
    ocid TEXT REFERENCES procurements(ocid),
    risk_score NUMERIC,
    risk_category TEXT,
    explanation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_procurements_buyer ON procurements (buyer_id);
CREATE INDEX IF NOT EXISTS idx_procurements_supplier ON procurements (supplier_id);
CREATE INDEX IF NOT EXISTS idx_procurements_award_date ON procurements (award_date);
CREATE INDEX IF NOT EXISTS idx_flags_risk_score ON flags (risk_score);

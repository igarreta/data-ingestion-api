-- 001_initial_schema.sql

CREATE TABLE entities (
    id          TEXT PRIMARY KEY,
    unit        TEXT,
    description TEXT,
    device      TEXT
);

CREATE TABLE measurements (
    id          BIGSERIAL PRIMARY KEY,
    timestamp   TIMESTAMPTZ NOT NULL,
    entity_id   TEXT NOT NULL REFERENCES entities(id),
    value       NUMERIC NOT NULL,
    source      TEXT
);

CREATE INDEX idx_measurements_entity_time
    ON measurements (entity_id, timestamp DESC);

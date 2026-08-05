-- OptiScale Core Database Schema (TimescaleDB / PostgreSQL)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 1. Infrastructure Target Registry
CREATE TABLE IF NOT EXISTS target_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instance_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    provider VARCHAR(50) DEFAULT 'AWS',
    public_ip VARCHAR(45),
    instance_type VARCHAR(50),
    region VARCHAR(50) DEFAULT 'us-east-1',
    state VARCHAR(50) DEFAULT 'running',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Telemetry Time-Series Hypertable
CREATE TABLE IF NOT EXISTS node_telemetry (
    time TIMESTAMPTZ NOT NULL,
    instance_id VARCHAR(100) NOT NULL,
    active_tcp_connections INT DEFAULT 0,
    load_1m NUMERIC(5,2) DEFAULT 0.0,
    load_5m NUMERIC(5,2) DEFAULT 0.0,
    load_15m NUMERIC(5,2) DEFAULT 0.0,
    uptime_seconds NUMERIC(12,2) DEFAULT 0.0,
    is_idle BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (instance_id) REFERENCES target_nodes(instance_id) ON DELETE CASCADE
);

-- Convert node_telemetry into a TimescaleDB hypertable partitioned by time
SELECT create_hypertable('node_telemetry', 'time', if_not_exists => TRUE);

-- Index for fast time-series lookup per instance
CREATE INDEX IF NOT EXISTS idx_node_telemetry_instance_time 
ON node_telemetry (instance_id, time DESC);

-- 3. Optimization Action Audit Log
CREATE TABLE IF NOT EXISTS optimization_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instance_id VARCHAR(100) NOT NULL,
    action_type VARCHAR(50) NOT NULL, -- e.g., 'STOP', 'START', 'PAUSE'
    status VARCHAR(50) NOT NULL,      -- e.g., 'PENDING_APPROVAL', 'EXECUTED', 'CANCELLED'
    reason TEXT,
    cost_saved_usd NUMERIC(10,4) DEFAULT 0.00,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

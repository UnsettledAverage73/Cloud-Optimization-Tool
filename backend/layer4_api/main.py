import os
import sys
import asyncpg
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.layer2_intelligence.analyzer import IdleAnalyzer
from backend.layer3_remediation.executor import RemediationExecutor

load_dotenv(override=True)

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:postgrespassword@localhost:5432/optiscale"
)

app = FastAPI(
    title="OptiScale API",
    description="Engineered Cloud Cost Optimization Control Plane",
    version="1.0.0"
)

@app.get("/health")
async def health_check():
    return {"status": "HEALTHY", "service": "OptiScale Control Plane"}

@app.get("/api/v1/nodes")
async def list_nodes():
    """Returns list of registered target cloud nodes."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch("SELECT * FROM target_nodes ORDER BY created_at DESC;")
        return [dict(row) for row in rows]
    finally:
        await conn.close()

@app.get("/api/v1/telemetry/{instance_id}")
async def get_telemetry(instance_id: str, limit: int = Query(default=20, le=100)):
    """Fetches recent time-series telemetry records for a target instance."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch(
            "SELECT * FROM node_telemetry WHERE instance_id = $1 ORDER BY time DESC LIMIT $2;",
            instance_id, limit
        )
        return [dict(row) for row in rows]
    finally:
        await conn.close()

@app.post("/api/v1/analyze")
async def run_analysis(window_minutes: int = 15):
    """Triggers Layer 2 intelligence engine across all active nodes."""
    analyzer = IdleAnalyzer()
    reports = await analyzer.run_analysis(window_minutes=window_minutes)
    return {"status": "SUCCESS", "reports": reports}

@app.post("/api/v1/remediate/{instance_id}")
async def remediate_node(instance_id: str, dry_run: bool = True):
    """Executes or dry-runs remediation (stop) on a specific target node."""
    executor = RemediationExecutor()
    result = executor.stop_node(instance_id=instance_id, dry_run=dry_run)
    if result["status"] == "FAILED":
        raise HTTPException(status_code=500, detail=result.get("error", "Remediation failed"))
    return result

import sys
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.layer2_intelligence.cost_engine import CostEngine

load_dotenv(override=True)

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:postgrespassword@localhost:5432/optiscale"
)

class IdleAnalyzer:
    """Analyzes telemetry streams in TimescaleDB to classify targets as active or idle."""

    def __init__(self, db_url: str = DATABASE_URL):
        self.db_url = db_url

    async def analyze_instance(self, conn, instance_id: str, instance_type: str, window_minutes: int = 15):
        """Evaluates telemetry data over a rolling time window for a single instance."""
        query = """
            SELECT 
                COUNT(*) as total_ticks,
                COUNT(*) FILTER (WHERE is_idle = TRUE) as idle_ticks,
                AVG(load_1m) as avg_load_1m,
                AVG(active_tcp_connections) as avg_connections
            FROM node_telemetry
            WHERE instance_id = $1 
              AND time >= NOW() - ($2 || ' minutes')::INTERVAL;
        """
        row = await conn.fetchrow(query, instance_id, str(window_minutes))

        if not row or row["total_ticks"] == 0:
            return {
                "instance_id": instance_id,
                "status": "INSUFFICIENT_DATA",
                "reason": "No telemetry ticks recorded in window."
            }

        total_ticks = row["total_ticks"]
        idle_ticks = row["idle_ticks"]
        idle_ratio = idle_ticks / total_ticks if total_ticks > 0 else 0.0

        # Mark as CANDIDATE_FOR_SHUTDOWN if >80% of ticks in window are idle
        is_candidate = idle_ratio >= 0.8

        cost_metrics = CostEngine.calculate_savings(
            instance_type=instance_type, 
            idle_hours=window_minutes / 60.0
        )

        return {
            "instance_id": instance_id,
            "instance_type": instance_type,
            "window_minutes": window_minutes,
            "total_ticks": total_ticks,
            "idle_ratio": round(idle_ratio, 2),
            "avg_load_1m": float(row["avg_load_1m"] or 0.0),
            "avg_connections": float(row["avg_connections"] or 0.0),
            "recommendation": "STOP" if is_candidate else "KEEP_RUNNING",
            "cost_analysis": cost_metrics
        }

    async def run_analysis(self, window_minutes: int = 15):
        """Analyzes all registered running nodes in target_nodes table."""
        conn = await asyncpg.connect(self.db_url)
        try:
            nodes = await conn.fetch("SELECT instance_id, instance_type, name FROM target_nodes WHERE state = 'running'")
            print(f"📊 Running Idle Analysis for {len(nodes)} active node(s)...")

            reports = []
            for node in nodes:
                report = await self.analyze_instance(
                    conn, 
                    node["instance_id"], 
                    node["instance_type"], 
                    window_minutes
                )
                reports.append(report)
                recommendation = report.get('recommendation', report.get('action', 'NO_ACTION'))
                idle_ratio = report.get('idle_ratio', 0.0)

                print(f"🔎 Node {node['name']} ({node['instance_id']}): {recommendation} (Idle Ratio: {idle_ratio})")


            return reports
        finally:
            await conn.close()


if __name__ == "__main__":
    analyzer = IdleAnalyzer()
    asyncio.run(analyzer.run_analysis())


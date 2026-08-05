import os
import sys
import asyncio
from datetime import datetime, timezone
import asyncpg
from dotenv import load_dotenv

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.layer1_telemetry.cloud_connectors import AWSCloudConnector
from backend.layer1_telemetry.collector import AgentlessSSHCollector

load_dotenv(override=True)

# Database connection fallback (matching docker-compose credentials)
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:postgrespassword@localhost:5432/optiscale"
)

class TelemetryIngestionService:
    """Orchestrates discovery, SSH telemetry collection, and TimescaleDB storage"""

    def __init__(self, key_filename: str = "optiscale.pem"):
        self.cloud_connector = AWSCloudConnector()
        self.ssh_collector = AgentlessSSHCollector(key_filename=key_filename)

    async def _get_db_pool(self):
        """Creates an async connection pool to PostgreSQL/TimescaleDB"""
        return await asyncpg.create_pool(dsn=DATABASE_URL)

    async def sync_target_nodes(self, pool, instances):
        """Upserts discovered EC2 instances into target_nodes registry table"""
        async with pool.acquire() as conn:
            query = """
                INSERT INTO target_nodes (instance_id, name, provider, public_ip, instance_type, region, state)
                VALUES ($1, $2, 'AWS', $3, $4, $5, $6)
                ON CONFLICT (instance_id) 
                DO UPDATE SET 
                    public_ip = EXCLUDED.public_ip,
                    state = EXCLUDED.state,
                    updated_at = NOW();
            """
            for inst in instances:
                await conn.execute(
                    query,
                    inst["instance_id"],
                    inst["name"],
                    inst["public_ip"],
                    inst["instance_type"],
                    self.cloud_connector.region,
                    inst["state"]
                )
        print(f"✅ Synced {len(instances)} nodes into target_nodes registry.")

    async def ingest_telemetry_tick(self, pool, instance_id: str, telemetry: dict):
        """Inserts a single metric tick into the node_telemetry hypertable"""
        if telemetry.get("status") != "HEALTHY":
            print(f"⚠️ Skipping metrics write for {instance_id}: Node unreachable.")
            return

        async with pool.acquire() as conn:
            query = """
                INSERT INTO node_telemetry 
                (time, instance_id, active_tcp_connections, load_1m, load_5m, load_15m, uptime_seconds, is_idle)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8);
            """
            await conn.execute(
                query,
                datetime.now(timezone.utc),
                instance_id,
                telemetry["active_tcp_connections"],
                telemetry["load_1m"],
                telemetry["load_5m"],
                telemetry["load_15m"],
                telemetry["uptime_seconds"],
                telemetry["is_idle"]
            )
        print(f"⚡ Ingested telemetry tick for node {instance_id} into TimescaleDB.")

    async def run_pipeline(self):
        """Executes full discovery + SSH telemetry + DB write pipeline"""
        print("🚀 Starting Telemetry Ingestion Pipeline...")
        pool = await self._get_db_pool()

        try:
            # Step 1: Discover AWS Instances
            instances = self.cloud_connector.discover_instances()
            await self.sync_target_nodes(pool, instances)

            # Step 2: Collect & Ingest Telemetry for active nodes
            for inst in instances:
                if inst["state"] == "running" and inst["public_ip"] != "N/A":
                    print(f"📡 Collecting metrics from {inst['name']} ({inst['public_ip']})...")
                    telemetry = self.ssh_collector.collect_telemetry(inst["public_ip"])
                    await self.ingest_telemetry_tick(pool, inst["instance_id"], telemetry)

        finally:
            await pool.close()
            print("🏁 Pipeline execution complete. Connection pool closed.")


if __name__ == "__main__":
    service = TelemetryIngestionService()
    asyncio.run(service.run_pipeline())

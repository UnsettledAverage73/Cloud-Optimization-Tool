import paramiko
import os
import re
from typing import Dict, Any, Optional
import sys

# Ensure project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Now import relative or absolute modules
from backend.layer1_telemetry.cloud_connectors import AWSCloudConnector

class AgentlessSSHCollector:
    """Agentless telemetry collector using Paramiko over SSH socket"""

    def __init__(self, key_filename: str = "optiscale.pem", username: str = "ec2-user"):
        self.key_filename = os.path.abspath(key_filename)
        self.username = username

    def _get_ssh_client(self, host: str, port: int = 22) -> paramiko.SSHClient:
        """Establishes a secure Paramiko SSH session"""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        if not os.path.exists(self.key_filename):
            raise FileNotFoundError(f"SSH key not found at {self.key_filename}")

        client.connect(
            hostname=host,
            port=port,
            username=self.username,
            key_filename=self.key_filename,
            timeout=10
        )
        return client

    def collect_telemetry(self, host: str, username_override: Optional[str] = None) -> Dict[str, Any]:
        """Collects active socket connections, CPU load average, and uptime"""
        user = username_override or self.username
        client = None
        
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=host,
                port=22,
                username=user,
                key_filename=self.key_filename,
                timeout=10
            )

            # Command 1: Get active established TCP connections (excluding SSH port 22)
            # Counts incoming/outgoing active app traffic
            _, stdout_conn, _ = client.exec_command(
                "ss -tuna | grep ESTAB | grep -v ':22 ' | wc -l"
            )
            active_connections = int(stdout_conn.read().decode().strip() or "0")

            # Command 2: Read 1-min, 5-min, 15-min Load Averages from /proc/loadavg
            _, stdout_load, _ = client.exec_command("cat /proc/loadavg")
            load_raw = stdout_load.read().decode().strip().split()
            load_1m, load_5m, load_15m = float(load_raw[0]), float(load_raw[1]), float(load_raw[2])

            # Command 3: System Uptime in seconds
            _, stdout_uptime, _ = client.exec_command("cat /proc/uptime")
            uptime_seconds = float(stdout_uptime.read().decode().strip().split()[0])

            return {
                "host": host,
                "status": "HEALTHY",
                "active_tcp_connections": active_connections,
                "load_1m": load_1m,
                "load_5m": load_5m,
                "load_15m": load_15m,
                "uptime_seconds": uptime_seconds,
                "is_idle": active_connections == 0 and load_1m < 0.10
            }

        except Exception as e:
            return {
                "host": host,
                "status": "UNREACHABLE",
                "error": str(e)
            }
        finally:
            if client:
                client.close()


if __name__ == "__main__":
    # Test SSH inspection against OptiScale-Target-01
    import sys
    from backend.layer1_telemetry.cloud_connectors import AWSCloudConnector

    print("🔎 Fetching live instances to inspect...")
    connector = AWSCloudConnector()
    instances = connector.discover_instances()

    target_ip = None
    for inst in instances:
        if inst["state"] == "running" and inst["public_ip"] != "N/A":
            target_ip = inst["public_ip"]
            print(f"🎯 Target Found: {inst['name']} ({inst['instance_id']}) @ {target_ip}")
            break

    if not target_ip:
        print("❌ No running EC2 instance with public IP found.")
        sys.exit(1)

    # Note: AWS Amazon Linux uses 'ec2-user', Ubuntu uses 'ubuntu'
    collector = AgentlessSSHCollector(key_filename="optiscale.pem", username="ec2-user")
    
    print(f"\n📡 Connecting via Agentless SSH to {target_ip}...")
    telemetry = collector.collect_telemetry(target_ip)
    
    print("\n⚡ Live SSH Telemetry Collected:")
    print(telemetry)

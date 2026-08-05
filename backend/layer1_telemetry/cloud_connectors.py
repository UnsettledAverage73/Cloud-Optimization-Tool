import os
import boto3
from typing import List, Dict, Any
from dotenv import load_dotenv

# 1. Load environment variables first
load_dotenv(override=True)

class AWSCloudConnector:
    """Discovers and inspects EC2 instances via Boto3 SDK"""

    def __init__(self, region: str = None):
        # Default region fallback
        self.region = region or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        
        # boto3 automatically reads AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
        # and AWS_SESSION_TOKEN directly from environment variables.
        self.ec2 = boto3.client("ec2", region_name=self.region)

    def discover_instances(self) -> List[Dict[str, Any]]:
        """Fetch all running/stopped EC2 instances in the region"""
        response = self.ec2.describe_instances()
        discovered = []

        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                instance_id = instance.get("InstanceId")
                state = instance.get("State", {}).get("Name")
                public_ip = instance.get("PublicIpAddress", "N/A")
                
                name = "Unnamed"
                for tag in instance.get("Tags", []):
                    if tag["Key"] == "Name":
                        name = tag["Value"]
                        break

                discovered.append({
                    "instance_id": instance_id,
                    "name": name,
                    "state": state,
                    "public_ip": public_ip,
                    "instance_type": instance.get("InstanceType"),
                    "launch_time": instance.get("LaunchTime").isoformat() if instance.get("LaunchTime") else None
                })

        return discovered

if __name__ == "__main__":
    connector = AWSCloudConnector()
    instances = connector.discover_instances()
    print("\n✅ Successfully connected to AWS!")
    print("Discovered Instances:", instances)

import os
import sys
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

load_dotenv(override=True)

class RemediationExecutor:
    """Executes safe cloud state transitions based on Layer 2 intelligence reports."""

    def __init__(self, region_name: str = None):
        self.region = region_name or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        self.ec2 = boto3.client("ec2", region_name=self.region)

    def stop_node(self, instance_id: str, dry_run: bool = False) -> dict:
        """Stops an EC2 instance given its instance ID."""
        print(f"🛑 ['DRY-RUN' if dry_run else 'ACTION'] Stopping instance {instance_id} in {self.region}...")

        try:
            response = self.ec2.stop_instances(
                InstanceIds=[instance_id],
                DryRun=dry_run
            )
            stopping_instances = response.get("StoppingInstances", [])
            state = stopping_instances[0]["CurrentState"]["Name"] if stopping_instances else "unknown"
            return {
                "instance_id": instance_id,
                "status": "SUCCESS",
                "current_state": state,
                "dry_run": dry_run
            }
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if dry_run and error_code == "DryRunOperation":
                print(f"✅ Dry-run validation successful for {instance_id}. Action is permissible.")
                return {
                    "instance_id": instance_id,
                    "status": "DRY_RUN_PASSED",
                    "dry_run": True
                }
            print(f"❌ Failed to stop instance {instance_id}: {e}")
            return {
                "instance_id": instance_id,
                "status": "FAILED",
                "error": str(e),
                "dry_run": dry_run
            }
        except BotoCoreError as e:
            print(f"❌ AWS Core error on instance {instance_id}: {e}")
            return {
                "instance_id": instance_id,
                "status": "FAILED",
                "error": str(e),
                "dry_run": dry_run
            }

if __name__ == "__main__":
    executor = RemediationExecutor()
    # Test dry-run safety validation
    result = executor.stop_node("i-0627aa556b3b1cc07", dry_run=True)
    print("Remediation Dry-Run Result:", result)

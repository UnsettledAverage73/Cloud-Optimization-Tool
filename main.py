import asyncio
from backend.layer2_intelligence.analyzer import IdleAnalyzer
from backend.layer3_remediation.executor import RemediationExecutor

async def run_optiscale_pipeline(auto_remediate: bool = False, dry_run: bool = True):
    print("==================================================")
    print("🌐 OPTISCALE: END-TO-END CLOUD OPTIMIZATION CYCLE")
    print("==================================================")

    # 1. Run Intelligence Analyzer
    analyzer = IdleAnalyzer()
    reports = await analyzer.run_analysis(window_minutes=15)

    executor = RemediationExecutor()

    # 2. Process Recommendations
    for report in reports:
        instance_id = report["instance_id"]
        recommendation = report["recommendation"]
        savings = report.get("cost_analysis", {}).get("monthly_projected_savings_usd", 0.0)

        print(f"\n📋 Node: {instance_id}")
        print(f"   Recommendation : {recommendation}")
        print(f"   Monthly Waste  : ${savings} USD")

        if recommendation == "STOP":
            if auto_remediate:
                print(f"⚡ Auto-Remediation active. Executing shutdown...")
                res = executor.stop_node(instance_id, dry_run=dry_run)
                print(f"   Remediation Result: {res['status']}")
            else:
                print("ℹ️ Auto-Remediation flag disabled. Skipping shutdown action.")

if __name__ == "__main__":
    # Runs in safety Dry-Run mode by default
    asyncio.run(run_optiscale_pipeline(auto_remediate=True, dry_run=True))

"""
AWS Pricing Reference & Cost Calculation Engine
"""

# Standard AWS hourly rate card (us-east-1 On-Demand reference)
AWS_HOURLY_RATES = {
    "t2.nano": 0.0058,
    "t2.micro": 0.0116,
    "t2.small": 0.023,
    "t3.nano": 0.0052,
    "t3.micro": 0.0104,
    "t3.small": 0.0208,
    "t3.medium": 0.0416,
    "c5.large": 0.085,
    "m5.large": 0.096,
}

class CostEngine:
    """Calculates potential waste and projected savings for idle cloud targets."""

    @staticmethod
    def get_hourly_rate(instance_type: str, provider: str = "AWS") -> float:
        """Returns hourly cost for an instance type; defaults to t3.micro rate if unknown."""
        return AWS_HOURLY_RATES.get(instance_type.lower(), 0.0104)

    @classmethod
    def calculate_savings(cls, instance_type: str, idle_hours: float) -> dict:
        """Calculates USD saved for a given idle duration."""
        rate = cls.get_hourly_rate(instance_type)
        hourly_savings = round(rate, 4)
        total_saved_usd = round(idle_hours * rate, 4)
        monthly_projected_usd = round(730 * rate, 2)  # 730 hours in an average month

        return {
            "hourly_rate_usd": hourly_savings,
            "realized_savings_usd": total_saved_usd,
            "monthly_projected_savings_usd": monthly_projected_usd,
        }

"""Budget monitoring and alerting for LLM Gate usage."""

import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple

import structlog
from prometheus_client import Counter, Gauge

from langhook.subscriptions.config import subscription_settings


logger = structlog.get_logger("langhook")

# Prometheus metrics for budget monitoring
gate_daily_cost = Gauge(
    "langhook_gate_daily_cost_usd",
    "Daily LLM gate cost in USD",
    ["date"]
)

gate_budget_alerts = Counter(
    "langhook_gate_budget_alerts_total",
    "Total number of budget alerts sent",
    ["alert_type"]
)


class LLMGateBudgetMonitor:
    """Monitor and alert on LLM Gate spending."""

    def __init__(self) -> None:
        """Initialize the budget monitor."""
        self.daily_costs: Dict[str, float] = {}  # date -> cost
        self.last_alert_time: Dict[str, float] = {}  # alert_type -> timestamp
        self.alert_cooldown = 3600  # 1 hour cooldown between alerts
        logger.info("LLM Gate budget monitor initialized")

    def record_cost(self, cost_usd: float, subscription_id: int) -> None:
        """
        Record a cost and check if alerts need to be sent.

        Args:
            cost_usd: Cost in USD for the LLM evaluation
            subscription_id: ID of the subscription
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        # Track daily costs
        if today not in self.daily_costs:
            self.daily_costs[today] = 0.0
        
        self.daily_costs[today] += cost_usd
        
        # Update Prometheus metric
        gate_daily_cost.labels(date=today).set(self.daily_costs[today])
        
        # Check for budget alerts
        self._check_budget_alerts(today)
        
        logger.debug(
            "LLM gate cost recorded",
            cost_usd=cost_usd,
            subscription_id=subscription_id,
            daily_total=self.daily_costs[today],
            date=today
        )

    def _check_budget_alerts(self, date: str) -> None:
        """Check if budget alerts should be sent."""
        daily_cost = self.daily_costs.get(date, 0.0)
        limit = subscription_settings.gate_daily_cost_limit_usd
        threshold = subscription_settings.gate_cost_alert_threshold
        
        # Check threshold alert (80% by default)
        threshold_amount = limit * threshold
        if daily_cost >= threshold_amount:
            self._send_alert(
                "threshold_reached",
                f"Daily LLM gate spending has reached {threshold*100:.0f}% of limit",
                daily_cost,
                limit,
                date
            )
        
        # Check limit exceeded alert
        if daily_cost >= limit:
            self._send_alert(
                "limit_exceeded",
                "Daily LLM gate spending limit exceeded",
                daily_cost,
                limit,
                date
            )

    def _send_alert(
        self, 
        alert_type: str, 
        message: str, 
        current_cost: float, 
        limit: float,
        date: str
    ) -> None:
        """
        Send a budget alert if not in cooldown period.

        Args:
            alert_type: Type of alert (threshold_reached, limit_exceeded)
            message: Alert message
            current_cost: Current daily cost
            limit: Daily limit
            date: Date of the alert
        """
        now = time.time()
        cooldown_key = f"{alert_type}_{date}"
        
        # Check if we're in cooldown period
        if cooldown_key in self.last_alert_time:
            if now - self.last_alert_time[cooldown_key] < self.alert_cooldown:
                return  # Still in cooldown
        
        # Record alert time
        self.last_alert_time[cooldown_key] = now
        
        # Update Prometheus counter
        gate_budget_alerts.labels(alert_type=alert_type).inc()
        
        # Log the alert
        logger.warning(
            "LLM Gate budget alert",
            alert_type=alert_type,
            message=message,
            current_cost_usd=current_cost,
            daily_limit_usd=limit,
            percentage_used=f"{(current_cost / limit) * 100:.1f}%",
            date=date
        )
        
        # TODO: Send alert to external systems (email, Slack, etc.)
        # This would be configured based on user preferences

    def get_daily_cost(self, date: str = None) -> float:
        """Get daily cost for a specific date or today."""
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.daily_costs.get(date, 0.0)

    def get_weekly_costs(self) -> List[Tuple[str, float]]:
        """Get costs for the last 7 days."""
        costs = []
        today = datetime.now(timezone.utc)
        
        for i in range(7):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            cost = self.daily_costs.get(date, 0.0)
            costs.append((date, cost))
        
        return costs

    def get_monthly_total(self) -> float:
        """Get total cost for the current month."""
        today = datetime.now(timezone.utc)
        month_prefix = today.strftime("%Y-%m")
        
        total = 0.0
        for date, cost in self.daily_costs.items():
            if date.startswith(month_prefix):
                total += cost
        
        return total

    def reset_daily_costs_before_date(self, before_date: str) -> None:
        """Reset daily costs before a certain date to manage memory."""
        to_remove = [date for date in self.daily_costs.keys() if date < before_date]
        for date in to_remove:
            del self.daily_costs[date]
        
        logger.info(f"Cleaned up {len(to_remove)} old daily cost records")

    def get_budget_status(self) -> Dict[str, any]:
        """Get current budget status summary."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily_cost = self.get_daily_cost(today)
        limit = subscription_settings.gate_daily_cost_limit_usd
        threshold = subscription_settings.gate_cost_alert_threshold
        
        return {
            "date": today,
            "daily_cost_usd": daily_cost,
            "daily_limit_usd": limit,
            "percentage_used": (daily_cost / limit) * 100 if limit > 0 else 0,
            "threshold_percentage": threshold * 100,
            "weekly_costs": self.get_weekly_costs(),
            "monthly_total_usd": self.get_monthly_total(),
            "status": self._get_status_text(daily_cost, limit, threshold)
        }

    def _get_status_text(self, cost: float, limit: float, threshold: float) -> str:
        """Get human-readable status text."""
        if cost >= limit:
            return "LIMIT_EXCEEDED"
        elif cost >= limit * threshold:
            return "THRESHOLD_REACHED"
        elif cost >= limit * 0.5:
            return "MODERATE_USAGE"
        else:
            return "LOW_USAGE"


# Global budget monitor instance
budget_monitor = LLMGateBudgetMonitor()
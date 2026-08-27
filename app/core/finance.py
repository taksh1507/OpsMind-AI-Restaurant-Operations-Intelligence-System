"""Finance & Currency Utilities for Margin Analysis

Handles real-time currency conversion, landed cost calculations, and margin assessments
for dishes with imported ingredients.

Exchange rate source:
- If a USD_TO_INR_RATE env var is set (or app setting usd_to_inr_rate), that is used.
- Otherwise, a live public FX API is queried at startup (see refresh_exchange_rate).
- On any failure, a configured fallback rate is used so margin analysis never hard-fails.
"""

from decimal import Decimal
from typing import Optional, Dict

from app.core.config import Settings

# 1 USD = <rate> INR. Warmed at startup from settings/live source.
_exchange_rate: Optional[Decimal] = None


def _default_rate() -> Decimal:
    """Return the configured default/fallback exchange rate from settings."""
    try:
        return Settings().usd_to_inr_rate
    except Exception:
        return Decimal("94.05")


async def refresh_exchange_rate_from_live_source() -> Decimal:
    """Fetch the latest USD -> INR rate from a public FX API.

    Uses the free https://open.er-api.com/v6/latest/USD endpoint (no API key needed).
    On any failure (network, bad payload, absurd value) the configured fallback rate
    is used, so margin analysis never hard-fails.

    Returns:
        The effective exchange rate (1 USD in INR) as a Decimal.
    """
    fallback = _default_rate()

    try:
        import httpx

        settings_snapshot = Settings()
        if not settings_snapshot.fx_live_enabled:
            CurrencyManager.refresh_exchange_rate(
                CurrencyManager._clean_live_rate(float(fallback)) or fallback
            )
            return fallback

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("https://open.er-api.com/v6/latest/USD")
            resp.raise_for_status()
            data = resp.json()

        raw_rate = (data.get("rates") or {}).get("INR")
        cleaned = CurrencyManager._clean_live_rate(
            float(raw_rate) if raw_rate is not None else None
        )

        rate = cleaned if cleaned is not None else fallback
        CurrencyManager.refresh_exchange_rate(rate)
        return rate
    except Exception:
        CurrencyManager.refresh_exchange_rate(fallback)
        return fallback


def get_margin_alert_message(
    item_name: str,
    import_cost_usd: Decimal,
    current_price: Decimal,
    landed_cost_inr: Decimal,
    current_margin: Decimal,
    required_price: Decimal,
    exchange_rate: Decimal,
) -> str:
    """Generate human-readable margin alert message.

    Args:
        item_name: Name of the menu item
        import_cost_usd: Cost in USD
        current_price: Current selling price in INR
        landed_cost_inr: Calculated landed cost in INR
        current_margin: Current profit margin percentage
        required_price: Required price to maintain target margin
        exchange_rate: Current exchange rate

    Returns:
        Formatted alert message
    """
    price_increase = required_price - current_price

    return (
        f"⚠️ MARGIN ALERT: {item_name}\n\n"
        f"The USD/INR exchange rate has moved to ₹{exchange_rate:.2f}.\n\n"
        f"Original Import Cost: ${import_cost_usd:.2f}\n"
        f"Landed Cost in INR: ₹{landed_cost_inr:.2f}\n"
        f"Current Selling Price: ₹{current_price:.2f}\n"
        f"Current Profit Margin: {current_margin:.1f}%\n\n"
        f"To maintain a 30% margin, increase price by ₹{price_increase:.2f}\n"
        f"Recommended New Price: ₹{required_price:.2f}"
    )


class CurrencyManager:
    """Manages currency conversion and landed cost calculations."""

    @staticmethod
    def get_current_usd_to_inr_rate(custom_rate: Optional[Decimal] = None) -> Decimal:
        """Get current USD to INR exchange rate.

        Uses the startup-refreshed live rate (or the configured default), unless an
        explicit override is provided (used mainly in tests).

        Args:
            custom_rate: Override rate for testing (normally use live rate)

        Returns:
            Exchange rate as Decimal (e.g., 94.05)
        """
        if custom_rate is not None:
            return custom_rate
        return _exchange_rate or _default_rate()

    @staticmethod
    def refresh_exchange_rate(rate: Decimal) -> None:
        """Set the in-memory exchange rate (used at startup or by the live fetcher)."""
        global _exchange_rate
        _exchange_rate = rate

    @staticmethod
    def _clean_live_rate(rate: Optional[float]) -> Optional[Decimal]:
        """Sanitize a raw rate from an external source into a usable Decimal (or None)."""
        if rate is None:
            return None
        try:
            value = Decimal(str(rate))
        except Exception:
            return None
        # Reject absurd values that would indicate a garbage response.
        if value <= 0 or value > 1000:
            return None
        # Normalize to 2 decimal places.
        return value.quantize(Decimal("0.01"))

    @staticmethod
    def convert_usd_to_inr(
        usd_amount: Decimal, rate: Optional[Decimal] = None
    ) -> Decimal:
        """Convert USD amount to INR using current rate.

        Args:
            usd_amount: Amount in USD
            rate: Override exchange rate for testing

        Returns:
            Amount in INR
        """
        rate = CurrencyManager.get_current_usd_to_inr_rate(rate)
        return (usd_amount * rate).quantize(Decimal("0.01"))

    @staticmethod
    def calculate_landed_cost_inr(
        import_cost_usd: Decimal,
        markup_percentage: Decimal = Decimal("5"),
        rate: Optional[Decimal] = None,
    ) -> Decimal:
        """Calculate landed cost in INR for imported ingredient.

        Landed cost = (Cost in USD * Exchange Rate) + Shipping/Import Markup

        Args:
            import_cost_usd: Cost in USD
            markup_percentage: Added percentage for import taxes/shipping (default 5%)
            rate: Override exchange rate

        Returns:
            Total landed cost in INR
        """
        rate = CurrencyManager.get_current_usd_to_inr_rate(rate)

        # Convert USD to INR
        inr_cost = import_cost_usd * rate

        # Add import markup (shipping, customs, etc.)
        markup = inr_cost * (markup_percentage / Decimal("100"))

        return (inr_cost + markup).quantize(Decimal("0.01"))


class MarginAnalyzer:
    """Analyzes profit margins and identifies risk zones."""

    SAFE_MARGIN_THRESHOLD = Decimal("30")  # 30% is healthy
    DANGER_MARGIN_THRESHOLD = Decimal("20")  # Below 20% is risky
    CRITICAL_MARGIN_THRESHOLD = Decimal("10")  # Below 10% is critical

    @staticmethod
    def calculate_margin_percentage(
        selling_price: Decimal, cost_price: Decimal
    ) -> Decimal:
        """Calculate profit margin as percentage.

        Args:
            selling_price: Item's selling price in INR
            cost_price: Item's cost price in INR

        Returns:
            Margin as percentage (0-100)
        """
        if selling_price <= 0:
            return Decimal("0")

        return ((selling_price - cost_price) / selling_price * Decimal("100")).quantize(
            Decimal("0.01")
        )

    @staticmethod
    def get_margin_status(margin: Decimal) -> str:
        """Determine margin health status.

        Args:
            margin: Margin percentage

        Returns:
            Status: 'healthy' | 'warning' | 'danger' | 'critical'
        """
        if margin >= MarginAnalyzer.SAFE_MARGIN_THRESHOLD:
            return "healthy"
        elif margin >= MarginAnalyzer.DANGER_MARGIN_THRESHOLD:
            return "warning"
        elif margin >= MarginAnalyzer.CRITICAL_MARGIN_THRESHOLD:
            return "danger"
        else:
            return "critical"

    @staticmethod
    def calculate_required_price(
        cost_price: Decimal, target_margin: Decimal
    ) -> Decimal:
        """Calculate selling price needed to achieve target margin.

        Formula: Price = Cost / (1 - Target Margin%)

        Args:
            cost_price: Item's cost in INR
            target_margin: Desired margin percentage (e.g., 30 for 30%)

        Returns:
            Required selling price in INR
        """
        if target_margin >= Decimal("100"):
            target_margin = Decimal("99.99")

        margin_ratio = Decimal("1") - (target_margin / Decimal("100"))

        if margin_ratio <= 0:
            return cost_price * Decimal("2")  # Default: 2x cost

        return (cost_price / margin_ratio).quantize(Decimal("0.01"))

    @staticmethod
    def analyze_imported_item(
        selling_price: Decimal,
        import_cost_usd: Decimal,
        exchange_rate: Optional[Decimal] = None,
        target_margin: Decimal = Decimal("30"),
    ) -> Dict:
        """Comprehensive analysis for an imported menu item.

        Args:
            selling_price: Current selling price in INR
            import_cost_usd: Cost in USD
            exchange_rate: Override exchange rate
            target_margin: Target profit margin

        Returns:
            Dictionary with analysis results
        """
        # Calculate landed cost
        landed_cost_inr = CurrencyManager.calculate_landed_cost_inr(
            import_cost_usd, rate=exchange_rate
        )

        # Calculate current margin
        current_margin = MarginAnalyzer.calculate_margin_percentage(
            selling_price, landed_cost_inr
        )

        # Calculate required price
        required_price = MarginAnalyzer.calculate_required_price(
            landed_cost_inr, target_margin
        )

        # Determine status
        status = MarginAnalyzer.get_margin_status(current_margin)

        # Price adjustment needed
        price_adjustment = required_price - selling_price
        adjustment_percentage = (
            (price_adjustment / selling_price * Decimal("100")).quantize(
                Decimal("0.01")
            )
            if selling_price > 0
            else Decimal("0")
        )

        return {
            "landed_cost_inr": float(landed_cost_inr),
            "current_margin_percentage": float(current_margin),
            "margin_status": status,
            "current_price": float(selling_price),
            "required_price": float(required_price),
            "price_adjustment_inr": float(price_adjustment),
            "price_adjustment_percentage": float(adjustment_percentage),
            "exchange_rate": float(
                exchange_rate or CurrencyManager.get_current_usd_to_inr_rate()
            ),
            "at_risk": status in ["warning", "danger", "critical"],
        }

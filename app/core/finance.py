"""Finance & Currency Utilities for Margin Analysis

Handles real-time currency conversion, landed cost calculations, and margin assessments
for dishes with imported ingredients.
"""

from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict, Tuple


# As of March 25, 2026 - INR to USD exchange rate
# In production, this would come from a real-time API
CURRENT_EXCHANGE_RATE = Decimal("94.05")  # 1 USD = ₹94.05


class CurrencyManager:
    """Manages currency conversion and landed cost calculations."""
    
    @staticmethod
    def get_current_usd_to_inr_rate(custom_rate: Optional[Decimal] = None) -> Decimal:
        """Get current USD to INR exchange rate.
        
        Args:
            custom_rate: Override rate for testing (normally use live rate)
            
        Returns:
            Exchange rate as Decimal (e.g., 94.05)
        """
        return custom_rate or CURRENT_EXCHANGE_RATE
    
    @staticmethod
    def convert_usd_to_inr(usd_amount: Decimal, rate: Optional[Decimal] = None) -> Decimal:
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
        rate: Optional[Decimal] = None
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
        selling_price: Decimal,
        cost_price: Decimal
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
        
        return ((selling_price - cost_price) / selling_price * Decimal("100")).quantize(Decimal("0.01"))
    
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
        cost_price: Decimal,
        target_margin: Decimal
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
        target_margin: Decimal = Decimal("30")
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
            import_cost_usd,
            rate=exchange_rate
        )
        
        # Calculate current margin
        current_margin = MarginAnalyzer.calculate_margin_percentage(
            selling_price,
            landed_cost_inr
        )
        
        # Calculate required price
        required_price = MarginAnalyzer.calculate_required_price(
            landed_cost_inr,
            target_margin
        )
        
        # Determine status
        status = MarginAnalyzer.get_margin_status(current_margin)
        
        # Price adjustment needed
        price_adjustment = required_price - selling_price
        adjustment_percentage = (
            (price_adjustment / selling_price * Decimal("100")).quantize(Decimal("0.01"))
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
            "exchange_rate": float(exchange_rate or CurrencyManager.get_current_usd_to_inr_rate()),
            "at_risk": status in ["warning", "danger", "critical"]
        }


def get_margin_alert_message(
    item_name: str,
    import_cost_usd: Decimal,
    current_price: Decimal,
    landed_cost_inr: Decimal,
    current_margin: Decimal,
    required_price: Decimal,
    exchange_rate: Decimal
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

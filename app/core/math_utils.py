"""
Mathematical utilities for trend analysis and forecasting.
Uses Linear Regression and statistical measures to ground AI forecasts in mathematical reality.
"""

from typing import Dict, Tuple
import statistics


def calculate_trend_slope(data: list[float]) -> float:
    """
    Calculate linear regression slope for sales data trend.
    
    Uses simple linear regression: y = mx + b
    where slope (m) indicates growth rate per time period.
    
    Args:
        data: List of sales values over time periods
        
    Returns:
        float: Slope value
            - Positive: revenue growing
            - Negative: revenue declining
            - Near 0: stable/flat trend
            
    Example:
        >>> data = [100, 120, 150, 180, 200]
        >>> slope = calculate_trend_slope(data)
        >>> print(slope)  # ~25 (average growth of $25/day)
    """
    if not data or len(data) < 2:
        return 0.0
    
    n = len(data)
    
    # x values are indices: 0, 1, 2, ..., n-1
    x_values = list(range(n))
    y_values = data
    
    # Linear regression formula: slope = (n*Σ(xy) - Σ(x)*Σ(y)) / (n*Σ(x²) - (Σ(x))²)
    sum_x = sum(x_values)
    sum_y = sum(y_values)
    sum_xy = sum(x * y for x, y in zip(x_values, y_values))
    sum_x_squared = sum(x ** 2 for x in x_values)
    
    denominator = n * sum_x_squared - sum_x ** 2
    
    # Avoid division by zero
    if denominator == 0:
        return 0.0
    
    slope = (n * sum_xy - sum_x * sum_y) / denominator
    return slope


def calculate_trend_metrics(data: list[float]) -> Dict[str, float]:
    """
    Calculate comprehensive trend metrics for data analysis.
    
    Returns:
        Dict containing:
            - slope: Linear regression slope (growth rate)
            - r_squared: Goodness of fit (0-1, higher is better)
            - variance: Data spread/consistency
            - std_dev: Standard deviation
            - mean: Average value
    """
    if not data or len(data) < 2:
        return {
            "slope": 0.0,
            "r_squared": 0.0,
            "variance": 0.0,
            "std_dev": 0.0,
            "mean": 0.0,
        }
    
    n = len(data)
    x_values = list(range(n))
    y_values = data
    
    # Calculate slope
    slope = calculate_trend_slope(data)
    
    # Calculate mean
    mean_y = statistics.mean(y_values)
    mean_x = statistics.mean(x_values)
    
    # Calculate intercept: b = mean_y - slope * mean_x
    intercept = mean_y - slope * mean_x
    
    # Calculate R-squared: 1 - (SS_residual / SS_total)
    ss_total = sum((y - mean_y) ** 2 for y in y_values)
    ss_residual = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(x_values, y_values))
    
    if ss_total == 0:
        r_squared = 0.0
    else:
        r_squared = 1 - (ss_residual / ss_total)
        # Clamp to valid range [0, 1]
        r_squared = max(0.0, min(1.0, r_squared))
    
    # Calculate variance and std dev
    variance = statistics.variance(y_values) if len(y_values) > 1 else 0.0
    std_dev = statistics.stdev(y_values) if len(y_values) > 1 else 0.0
    
    return {
        "slope": round(slope, 2),
        "r_squared": round(r_squared, 3),
        "variance": round(variance, 2),
        "std_dev": round(std_dev, 2),
        "mean": round(mean_y, 2),
    }


def calculate_confidence_score(data: list[float]) -> Tuple[str, float]:
    """
    Calculate confidence score for predictions based on data consistency.
    
    Lower variance = higher confidence (data is stable and predictable)
    Higher variance = lower confidence (data is volatile and unpredictable)
    
    Args:
        data: List of sales values
        
    Returns:
        Tuple of (confidence_level, confidence_percentage)
            - confidence_level: "High" (>75%), "Medium" (50-75%), "Low" (<50%)
            - confidence_percentage: 0-100 float value
    """
    if not data or len(data) < 2:
        return ("Low", 30.0)
    
    metrics = calculate_trend_metrics(data)
    
    # Confidence based on R-squared (fit quality) and variance ratio
    # Higher R-squared = more predictable
    r_squared = metrics["r_squared"]
    mean_val = metrics["mean"]
    std_dev = metrics["std_dev"]
    
    # Calculate coefficient of variation (CV) - std_dev as % of mean
    # Lower CV = more stable, higher confidence
    if mean_val == 0:
        cv_ratio = 0.5  # Neutral
    else:
        cv_ratio = min(1.0, abs(std_dev / mean_val))  # Clamp to 1.0
    
    # Confidence = combination of fit quality (R²) and stability (inverse of CV)
    # 70% weight on R-squared, 30% weight on stability
    confidence_percentage = (r_squared * 0.7 + (1 - cv_ratio) * 0.3) * 100
    confidence_percentage = round(confidence_percentage, 1)
    
    # Categorize confidence level
    if confidence_percentage >= 75:
        confidence_level = "High"
    elif confidence_percentage >= 50:
        confidence_level = "Medium"
    else:
        confidence_level = "Low"
    
    return (confidence_level, confidence_percentage)


def forecast_next_values(
    data: list[float],
    periods_ahead: int = 3
) -> list[float]:
    """
    Simple linear regression forecast for next N periods.
    
    Uses the trend slope to extrapolate future values.
    
    Args:
        data: Historical sales data
        periods_ahead: Number of periods to forecast
        
    Returns:
        List of forecasted values
    """
    if not data or len(data) < 2:
        return [0.0] * periods_ahead
    
    metrics = calculate_trend_metrics(data)
    slope = metrics["slope"]
    mean_y = metrics["mean"]
    
    # Calculate intercept
    n = len(data)
    x_values = list(range(n))
    mean_x = statistics.mean(x_values)
    intercept = mean_y - slope * mean_x
    
    # Forecast next periods
    forecast = []
    for i in range(1, periods_ahead + 1):
        next_x = n - 1 + i  # Continue from last point
        forecast_value = slope * next_x + intercept
        forecast.append(max(0, forecast_value))  # No negative sales
    
    return [round(v, 2) for v in forecast]


def generate_trend_description(slope: float, confidence: str) -> str:
    """
    Generate human-readable description of trend direction.
    
    Args:
        slope: Trend slope value
        confidence: Confidence level ("High", "Medium", "Low")
        
    Returns:
        String description of trend
    """
    if slope > 100:
        trend = "rapidly growing"
    elif slope > 20:
        trend = "growing"
    elif slope > 5:
        trend = "slowly growing"
    elif slope > -5:
        trend = "stable"
    elif slope > -20:
        trend = "slowly declining"
    elif slope > -100:
        trend = "declining"
    else:
        trend = "rapidly declining"
    
    confidence_word = "very" if confidence == "High" else "somewhat" if confidence == "Medium" else "not very"
    
    return f"Revenue is {trend} with {confidence_word} {confidence.lower()} confidence"

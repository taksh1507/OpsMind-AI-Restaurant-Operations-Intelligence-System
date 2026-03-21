"""Weather Service - Environmental Context for AI Decision Making.

Integrates with OpenWeatherMap API to provide weather data that influences
restaurant sales patterns and AI decision-making.

This allows OpsMind AI to understand external factors:
- Rainy days → Higher delivery orders
- Hot days → Cold beverage promotion
- Cold days → Hot drink promotion
- Clear days → Patio seating recommendations
"""

import httpx
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from app.core.config import Settings

# Simple in-memory cache (in production, use Redis)
_weather_cache: Dict[str, Dict[str, Any]] = {}
_cache_duration = timedelta(minutes=30)  # Cache weather for 30 minutes


async def get_current_weather(city: str) -> Dict[str, Any]:
    """
    Fetch current weather data for a given city.
    
    Uses OpenWeatherMap API (free tier) to get temperature, humidity, 
    weather condition, and other environmental data that affects sales.
    
    Args:
        city: City name (e.g., "New York", "San Francisco")
        
    Returns:
        Dictionary with:
            - temperature: float (in Celsius)
            - humidity: int (0-100)
            - condition: str (e.g., "Rain", "Sunny", "Cloudy", "Snow")
            - description: str (detailed weather description)
            - wind_speed: float (m/s)
            - feels_like: float (perceived temperature)
            - is_rainy: bool (quick check)
            - is_hot: bool (temp > 28°C)
            - is_cold: bool (temp < 10°C)
            - suggestion: str (menu/operation suggestion)
    
    Example:
        >>> weather = await get_current_weather("Mumbai")
        >>> print(weather['temperature'])  # 32.5
        >>> print(weather['suggestion'])   # "Promote cold beverages"
    """
    
    # Check cache
    cache_key = city.lower()
    if cache_key in _weather_cache:
        cached_data, timestamp = _weather_cache[cache_key]
        if datetime.now() - timestamp < _cache_duration:
            return cached_data
    
    settings = Settings()
    
    if not settings.openweather_api_key:
        return _create_fallback_weather(city)
    
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": settings.openweather_api_key,
            "units": "metric"  # Celsius
        }
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            weather_data = _parse_weather_response(data, city)
            
            # Cache the result
            _weather_cache[cache_key] = (weather_data, datetime.now())
            
            return weather_data
    
    except httpx.HTTPError as e:
        print(f"[Weather API Error] Failed to fetch weather for {city}: {str(e)}")
        return _create_fallback_weather(city)
    except Exception as e:
        print(f"[Weather Service Error] {str(e)}")
        return _create_fallback_weather(city)


def _parse_weather_response(data: Dict[str, Any], city: str) -> Dict[str, Any]:
    """Parse OpenWeatherMap API response and extract relevant data."""
    
    try:
        main = data.get("main", {})
        weather = data.get("weather", [{}])[0]
        wind = data.get("wind", {})
        
        temperature = main.get("temp", 20)
        humidity = main.get("humidity", 50)
        feels_like = main.get("feels_like", temperature)
        condition = weather.get("main", "Unknown")  # Rain, Clouds, Clear, Snow, etc.
        description = weather.get("description", "").title()
        wind_speed = wind.get("speed", 0)
        
        # Quick boolean checks for decision-making
        is_rainy = condition.lower() in ["rain", "drizzle", "thunderstorm"]
        is_hot = temperature > 28
        is_cold = temperature < 10
        
        # Generate contextual suggestion for restaurant
        suggestion = _generate_weather_suggestion(
            temperature, condition, humidity, is_rainy, is_hot, is_cold
        )
        
        return {
            "city": city,
            "temperature": round(temperature, 1),
            "humidity": humidity,
            "condition": condition,
            "description": description,
            "wind_speed": round(wind_speed, 1),
            "feels_like": round(feels_like, 1),
            "is_rainy": is_rainy,
            "is_hot": is_hot,
            "is_cold": is_cold,
            "suggestion": suggestion,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
    
    except Exception as e:
        print(f"[Weather Parse Error] {str(e)}")
        return _create_fallback_weather(city)


def _generate_weather_suggestion(
    temperature: float,
    condition: str,
    humidity: int,
    is_rainy: bool,
    is_hot: bool,
    is_cold: bool
) -> str:
    """Generate contextual suggestion for restaurant based on weather."""
    
    suggestions = []
    
    if is_rainy:
        suggestions.append("Push delivery orders - rainy weather reduces foot traffic")
        suggestions.append("Promote comfort food (soups, hot drinks)")
    elif is_hot:
        suggestions.append("Promotme cold beverages and ice creams")
        suggestions.append("Offer cold salads and lighter menu items")
        if humidity > 70:
            suggestions.append("Highlight refreshing drinks with high margins")
    elif is_cold:
        suggestions.append("Promote hot drinks and comfort food")
        suggestions.append("Feature warming beverages (hot chocolate, tea, coffee)")
    
    if condition.lower() == "clear":
        suggestions.append("Encourage outdoor/patio seating if available")
    elif condition.lower() == "clouds":
        suggestions.append("Good weather for all operations - balanced approach")
    
    if temperature < 5:
        suggestions.append("Stock up on hot beverages")
    elif temperature > 35:
        suggestions.append("Ensure cold storage capacity - high demand for chilled items")
    
    return " | ".join(suggestions) if suggestions else "Monitor sales patterns for this weather"


def _create_fallback_weather(city: str) -> Dict[str, Any]:
    """Create fallback weather data when API is unavailable."""
    
    return {
        "city": city,
        "temperature": 22.0,
        "humidity": 60,
        "condition": "Unknown",
        "description": "Weather data unavailable",
        "wind_speed": 0.0,
        "feels_like": 22.0,
        "is_rainy": False,
        "is_hot": False,
        "is_cold": False,
        "suggestion": "Weather API unavailable - using default strategy",
        "timestamp": datetime.now().isoformat(),
        "status": "fallback"
    }


async def correlate_weather_with_sales(
    weather_data: Dict[str, Any],
    sales_summary: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analyze correlation between current weather and historical sales patterns.
    
    Helps AI understand how weather impacts specific menu items and foot traffic.
    
    Args:
        weather_data: Current weather from get_current_weather()
        sales_summary: Sales data with item breakdowns (from analytics service)
        
    Returns:
        Dictionary with:
            - weather_impact: Estimated % change in foot traffic
            - high_demand_items: Items likely to sell well in this weather
            - low_demand_items: Items likely to underperform
            - staff_recommendation: Suggested staffing level
            - inventory_recommendation: What to stock up on
    """
    
    condition = weather_data.get("condition", "").lower()
    temperature = weather_data.get("temperature", 20)
    is_rainy = weather_data.get("is_rainy", False)
    is_hot = weather_data.get("is_hot", False)
    is_cold = weather_data.get("is_cold", False)
    
    impact_results = {
        "weather": weather_data.get("condition"),
        "temperature": temperature,
        "weather_impact_on_foottraffic": 0,
        "high_demand_items": [],
        "low_demand_items": [],
        "staff_recommendation": "Normal",
        "inventory_recommendation": []
    }
    
    # Rainy weather correlation
    if is_rainy:
        impact_results["weather_impact_on_foottraffic"] = -25  # -25% foot traffic
        impact_results["high_demand_items"] = [
            "Delivery items",
            "Hot beverages",
            "Soups",
            "Comfort food"
        ]
        impact_results["low_demand_items"] = [
            "Outdoor seating items",
            "Cold salads",
            "Ice cream"
        ]
        impact_results["staff_recommendation"] = "Increase delivery staff"
        impact_results["inventory_recommendation"] = [
            "Hot beverages (tea, coffee, hot chocolate)",
            "Delivery containers and packaging"
        ]
    
    # Hot weather correlation
    elif is_hot:
        impact_results["weather_impact_on_foottraffic"] = 15  # +15% foot traffic
        impact_results["high_demand_items"] = [
            "Cold beverages",
            "Ice cream",
            "Cold salads",
            "Frozen drinks",
            "Light menu items"
        ]
        impact_results["low_demand_items"] = [
            "Hot soups",
            "Warm beverages",
            "Heavy meat dishes"
        ]
        impact_results["staff_recommendation"] = "Increase front-of-house, focus on beverage service"
        impact_results["inventory_recommendation"] = [
            "Ice (high demand)",
            "Cold beverages",
            "Fresh fruits and cold items"
        ]
    
    # Cold weather correlation
    elif is_cold:
        impact_results["weather_impact_on_foottraffic"] = -15  # -15% foot traffic
        impact_results["high_demand_items"] = [
            "Hot beverages",
            "Soups",
            "Comfort food",
            "Hot chocolate",
            "Warm desserts"
        ]
        impact_results["low_demand_items"] = [
            "Cold salads",
            "Ice cream",
            "Cold beverages"
        ]
        impact_results["staff_recommendation"] = "Normal with hot beverage focus"
        impact_results["inventory_recommendation"] = [
            "Hot beverages (coffee, tea, chocolate)",
            "Comfort food ingredients"
        ]
    
    # Sunny/Clear weather
    else:
        impact_results["weather_impact_on_foottraffic"] = 10  # +10% foot traffic
        impact_results["high_demand_items"] = ["All items perform well"]
        impact_results["low_demand_items"] = []
        impact_results["staff_recommendation"] = "Standard staffing, good for all operations"
        impact_results["inventory_recommendation"] = ["Balanced inventory"]
    
    return impact_results


def get_weather_context_string(weather_data: Dict[str, Any]) -> str:
    """
    Generate a natural language context string describing the weather.
    
    Used to feed into AI prompts so the agent understands the environment.
    
    Args:
        weather_data: Current weather from get_current_weather()
        
    Returns:
        String describing weather in business context
    """
    
    if weather_data.get("status") == "fallback":
        return "Weather data unavailable - proceeding with default strategy"
    
    city = weather_data.get("city", "Local area")
    temp = weather_data.get("temperature", 20)
    condition = weather_data.get("condition", "Unknown")
    humidity = weather_data.get("humidity", 50)
    feels_like = weather_data.get("feels_like", temp)
    
    context = f"Current weather in {city}: {condition}, {temp}°C (feels like {feels_like}°C), {humidity}% humidity"
    
    if weather_data.get("is_rainy"):
        context += ". Light foot traffic expected due to rain."
    elif weather_data.get("is_hot"):
        context += ". High customer volume expected due to heat."
    elif weather_data.get("is_cold"):
        context += ". Reduced foot traffic likely due to cold."
    else:
        context += ". Normal customer volume expected."
    
    return context

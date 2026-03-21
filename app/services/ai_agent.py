"""AI Agent Service - Autonomous Restaurant Consultant

Uses Google Gemini 1.5 Flash to analyze restaurant performance data
and provide expert consulting recommendations with structured reasoning.

The AI Service implements a "Consultant Mode" that:
1. Analyzes revenue, profit, and cost structures
2. Identifies star dishes and underperformers
3. Suggests specific price adjustments with impact predictions
4. Recommends inventory/cost savings
5. Provides overall health assessment and actionable next steps

All responses are structured as JSON for frontend integration.
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import google.generativeai as genai
from app.core.math_utils import calculate_trend_slope, calculate_trend_metrics
from app.core.config import settings


class AIConsultant:
    """Agentic AI that analyzes restaurant data and provides strategic advice."""
    
    def __init__(self):
        """Initialize Gemini API with the configured API key."""
        api_key = os.getenv("GOOGLE_API_KEY", settings.google_api_key)
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY environment variable not set. "
                "Please configure your Google Gemini API key."
            )
        
        genai.configure(api_key=api_key)
        # Use gemini-2.0-flash (latest) or gemini-pro as fallback
        try:
            self.model = genai.GenerativeModel("gemini-2.0-flash")
        except:
            # Fallback to gemini-pro if latest version not available
            self.model = genai.GenerativeModel("gemini-pro")
    
    async def generate_strategy(
        self,
        performance_data: Dict[str, Any],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate strategic recommendations based on restaurant performance.
        
        Takes a JSON summary of restaurant performance (Revenue, Profit, Top Items)
        and uses AI reasoning to identify business opportunities and problems.
        
        Args:
            performance_data: Dictionary containing:
                - total_revenue: Total revenue in period
                - total_profit: Total profit in period
                - profit_margin_percent: Profit margin percentage
                - cost_of_goods_sold: Cost of goods sold
                - transaction_count: Number of transactions
                - total_items_sold: Total items sold
                - top_selling_items: List of best-selling menu items
                - period: Date range of the analysis
                - tenant_id: Restaurant identifier
            system_prompt: Custom system prompt. If None, uses default consultant prompt.
            
        Returns:
            Dictionary with AI-generated strategic recommendations:
            - star_dish: Identified top performer
            - underperformer: Item with low profit/high volume
            - price_recommendation: Suggested price change with rationale
            - inventory_saving: Cost-saving opportunity
            - overall_health: Restaurant health assessment
            - actionable_insights: List of immediate actions
        """
        
        if system_prompt is None:
            system_prompt = self._get_default_consultant_prompt()
        
        # Build the user message with performance data
        user_message = self._build_analysis_message(performance_data)
        
        try:
            # Call Gemini with structured reasoning
            response = self.model.generate_content(
                [
                    {"role": "user", "parts": [system_prompt]},
                    {"role": "user", "parts": [user_message]}
                ],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    top_p=0.95,
                    top_k=40,
                    max_output_tokens=2048
                )
            )
            
            # Parse the AI response
            ai_response = response.text
            strategy = self._parse_strategy_response(ai_response, performance_data)
            
            return {
                "status": "success",
                "strategy": strategy,
                "reasoning": ai_response,
                "timestamp": performance_data.get("period", {}).get("end_date", "")
            }
        
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to generate strategy: {str(e)}",
                "strategy": None
            }
    
    def _get_default_consultant_prompt(self) -> str:
        """Return the default system prompt for restaurant consulting.
        
        This prompt teaches the AI to find "Hidden Problems" in restaurant data
        by identifying operational and strategic gaps that owners often miss.
        """
        return """You are a world-class restaurant consultant with 20+ years of experience in multi-unit restaurant operations.
Your expertise spans profit optimization, menu engineering, inventory management, and operational efficiency.

CONSULTING MISSION:
Analyze the provided restaurant performance data and identify hidden problems and opportunities.
Your goal is to provide the owner with exactly what they need to do TODAY to improve profitability.

REQUIRED ANALYSIS - Find These 4 Things:
1. STAR DISH: What's your best performer? Why? (High volume AND good margin)
2. UNDERPERFORMER: What item has HIGH volume but LOW profit? This is money being left on the table.
3. PRICE OPTIMIZATION: There's exactly ONE menu item that needs a price change. Identify it with specific numbers.
4. COST SAVING: Every restaurant has waste. Identify ONE specific area to reduce costs (portion size, waste reduction, supplier negotiation, etc).

HIDDEN PROBLEMS TO FIND:
- Items selling in high volume but at razor-thin margins
- Dishes that cost more to produce than customers expect to pay
- Labor/prep waste opportunities
- Supplier inefficiencies
- Menu items cannibalizing higher-margin alternatives

DATABASE CONTEXT:
You receive complete financial data including:
- Total revenue and profit
- Profit margins by item
- Sales volume by dish
- Cost of goods (COGS)
- Historical trends

OUTPUT FORMAT - MUST BE VALID JSON:
Always respond with ONLY valid JSON (no explanatory text). Use this exact structure:
{
    "star_dish": {
        "name": "String - dish name",
        "quantity_sold": number,
        "revenue_generated": number,
        "profit_contribution": number,
        "reason": "Why this is your best performer"
    },
    "underperformer": {
        "name": "String - dish name",
        "quantity_sold": number,
        "revenue_generated": number,
        "margin_percent": number,
        "reason": "Why this item is leaving money on the table",
        "problem": "Specific issue (high volume + low margin, supply cost too high, etc)"
    },
    "price_recommendation": {
        "item": "String - exact menu item name",
        "current_price": number,
        "current_margin_percent": number,
        "suggested_price": number,
        "price_change_percent": number,
        "price_change_dollars": number,
        "expected_weekly_impact": "String - e.g. '+$400 weekly profit if demand stays flat'",
        "rationale": "Specific business reason for this price point",
        "risk_level": "Low|Medium|High (demand sensitivity)"
    },
    "inventory_saving": {
        "area": "String - specific area (portion control, waste reduction, supplier change, etc)",
        "current_monthly_cost": "String - e.g. '$2,400'",
        "proposed_change": "String - exactly what to do",
        "estimated_monthly_savings": "String - e.g. '$400-600'",
        "implementation_difficulty": "Easy|Medium|Hard",
        "one_sentence_action": "Actionable step for today"
    },
    "overall_health": {
        "rating": "Excellent|Good|Fair|Needs Attention",
        "current_margin_percent": number,
        "margin_target": number,
        "margin_gap": number,
        "key_finding": "Most important insight",
        "trajectory": "String - are things improving or declining?"
    },
    "top_priorities": [
        {"priority": 1, "action": "Exact action to take", "expected_result": "Specific improvement"},
        {"priority": 2, "action": "Exact action to take", "expected_result": "Specific improvement"},
        {"priority": 3, "action": "Exact action to take", "expected_result": "Specific improvement"}
    ]
}

TONE & STYLE:
- Be direct and specific - no vague recommendations
- Use actual numbers from the data
- Focus on what's actionable TODAY
- Explain the "why" behind each recommendation
- Prioritize by impact (biggest profit opportunity first)

CRITICAL RULES:
- ALWAYS output valid JSON only
- NEVER include explanatory text before or after JSON
- Use null for unknown values, not empty strings
- All financial numbers must be numeric (not string)
- All percentages in decimal form (e.g., 35.5 for 35.5%)
- Every recommendation must reference actual menu items from the data"""
    
    
    def _build_analysis_message(self, performance_data: Dict[str, Any]) -> str:
        """Build the user message with formatted performance data."""
        return f"""Please analyze the following restaurant performance data and provide strategic recommendations:

PERFORMANCE DATA:
{json.dumps(performance_data, indent=2, default=str)}

Based on this data, identify:
1. Which menu item is your star performer
2. Which item is underperforming (high volume, low profit)
3. One specific price adjustment recommendation
4. One inventory cost-saving opportunity
5. Overall restaurant health and recommended actions

Provide your response as valid JSON."""
    
    def _parse_strategy_response(
        self,
        ai_response: str,
        performance_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse the AI's JSON response into structured data."""
        try:
            # Try to extract JSON from the response
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                # No JSON found, return a default structure
                return self._create_fallback_strategy(performance_data)
            
            json_str = ai_response[json_start:json_end]
            strategy = json.loads(json_str)
            
            return strategy
        
        except (json.JSONDecodeError, ValueError):
            # If parsing fails, create a structured fallback
            return self._create_fallback_strategy(performance_data)
    
    def _create_fallback_strategy(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a fallback strategy structure when AI parsing fails.
        
        This provides sensible defaults based on the actual data when 
        AI service is unavailable or returns invalid JSON.
        """
        top_items = performance_data.get("top_selling_items", [])
        total_revenue = float(performance_data.get("total_revenue", 0))
        total_profit = float(performance_data.get("total_profit", 0))
        margin = float(performance_data.get("profit_margin_percent", 0))
        
        star = top_items[0] if top_items else {}
        underperformer = top_items[-1] if len(top_items) > 1 else top_items[0] if top_items else {}
        
        current_price = float(star.get("revenue_generated", 0) / max(star.get("quantity_sold", 1), 1))
        price_increase = current_price * 0.08
        weekly_impact = price_increase * max(star.get("quantity_sold", 1), 0) / 4  # Rough weekly estimate
        
        return {
            "star_dish": {
                "name": star.get("name", "Top Seller"),
                "quantity_sold": star.get("quantity_sold", 0),
                "revenue_generated": star.get("revenue_generated", 0),
                "profit_contribution": star.get("revenue_generated", 0) * (margin / 100) if margin > 0 else 0,
                "reason": "Highest revenue generator in current period"
            },
            "underperformer": {
                "name": underperformer.get("name", "Bottom Item"),
                "quantity_sold": underperformer.get("quantity_sold", 0),
                "revenue_generated": underperformer.get("revenue_generated", 0),
                "margin_percent": margin * 0.7 if margin > 0 else 15.0,
                "reason": "Lowest margin or volume contributor",
                "problem": "Requires detailed analysis for optimization opportunity"
            },
            "price_recommendation": {
                "item": star.get("name", "Featured Item"),
                "current_price": current_price,
                "current_margin_percent": margin,
                "suggested_price": current_price * 1.08,
                "price_change_percent": 8.0,
                "price_change_dollars": price_increase,
                "expected_weekly_impact": f"+${weekly_impact:.0f} if demand stable",
                "rationale": "Top performer can support modest price increase",
                "risk_level": "Low"
            },
            "inventory_saving": {
                "area": "Waste reduction and portion control audit",
                "current_monthly_cost": f"${total_revenue * 0.7:.2f}",
                "proposed_change": "Conduct full inventory audit to identify waste opportunities",
                "estimated_monthly_savings": f"${total_revenue * 0.03:.2f}",
                "implementation_difficulty": "Medium",
                "one_sentence_action": "Schedule inventory audit with management this week"
            },
            "overall_health": {
                "rating": "Good" if margin > 30 else "Fair" if margin > 20 else "Needs Attention",
                "current_margin_percent": margin,
                "margin_target": 35.0,
                "margin_gap": max(0, 35.0 - margin),
                "key_finding": f"Current margin is {margin:.1f}%, target is 35%",
                "trajectory": "Review historical data to assess trend"
            },
            "top_priorities": [
                {
                    "priority": 1,
                    "action": f"Price audit on {star.get('name', 'top item')} - test +8% increase",
                    "expected_result": "$400-600 weekly profit impact"
                },
                {
                    "priority": 2,
                    "action": "Conduct full inventory waste audit",
                    "expected_result": "3-5% cost reduction monthly"
                },
                {
                    "priority": 3,
                    "action": f"Review {underperformer.get('name', 'bottom item')} profitability",
                    "expected_result": "Menu optimization opportunity"
                }
            ]
        }
    
    async def predict_revenue(
        self,
        trend_data: Dict[str, float]
    ) -> Dict[str, Any]:
        """Predict revenue for the next 3 days based on historical trends.
        
        Uses AI to analyze 14-day sales patterns and predict future revenue.
        Provides growth/decline rates and confidence scoring based on data consistency.
        
        Args:
            trend_data: Dictionary mapping date strings to daily revenue floats
                       (e.g., {"2026-03-19": 450.0, "2026-03-20": 510.0, ...})
        
        Returns:
            Dictionary with:
            - status: "success" or "error"
            - predictions: List of 3 days with predicted revenue
            - confidence_score: 0-100 score based on data consistency
            - growth_rate: Average daily growth/decline percentage
            - analysis: AI's textual analysis of trends and business impact
            - business_impact: Human-readable summary (e.g., "Expect 15% surge Saturday")
        """
        if not trend_data:
            return {
                "status": "error",
                "message": "No historical trend data provided"
            }
        
        system_prompt = self._get_forecasting_system_prompt()
        user_message = self._build_forecasting_message(trend_data)
        
        try:
            response = self.model.generate_content(
                [
                    {"role": "user", "parts": [system_prompt]},
                    {"role": "user", "parts": [user_message]}
                ],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    top_p=0.95,
                    top_k=40,
                    max_output_tokens=1500
                )
            )
            
            ai_response = response.text
            forecast = self._parse_forecast_response(ai_response, trend_data)
            
            return {
                "status": "success",
                "forecast": forecast,
                "reasoning": ai_response,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to generate revenue forecast: {str(e)}",
                "forecast": None
            }
    
    def _get_forecasting_system_prompt(self) -> str:
        """Return the system prompt for revenue forecasting grounded in mathematical analysis."""
        return """You are an expert revenue forecaster and time-series analyst for restaurants.
Your expertise includes:
- Identifying daily revenue patterns (weekday vs weekend trends)
- Detecting growth/decline trajectories using data science
- Predicting short-term revenue fluctuations with mathematical rigor
- Quantifying forecast confidence based on data consistency
- Grounding AI predictions in observed mathematical trends (Linear Regression slopes)

MATHEMATICAL GROUNDING:
You will receive a Linear Regression slope value. This is an OBJECTIVE mathematical measure of the revenue trend.
- Positive slope: Revenue is mathematically proven to be growing
- Negative slope: Revenue is mathematically proven to be declining
- Slope value tells you the rate of change (dollars per day)
- R² value tells you how reliably this slope explains the data (0-1, higher = more reliable)

YOUR ANALYSIS SHOULD INCLUDE:
1. Daily Revenue Predictions: Specific dollar amounts for the next 3 days
   - BASE these on the provided slope or derived trend
   - ADJUST for detected day-of-week patterns (weekends typically busier)
   - Predictions should explain how slope influenced the forecast
2. Confidence Score: 0-100 indicating your confidence in predictions
   - Higher R² from slope = More confidence
   - Consistent patterns = More confidence
   - Volatility = Less confidence
3. Growth/Decline Rate: Overall percentage change pattern tied to the mathematical slope
4. Business Impact: Key actionable insight derived from the trend (e.g., "Slope of +$25/day indicates strong growth trajectory")
5. Pattern Analysis: What trend you observe + how it aligns with the mathematical slope

CRITICAL INSTRUCTION:
Always explain how you used the provided slope in your forecast.
Do NOT ignore the mathematical slope - incorporate it into your reasoning.
If slope conflicts with day-of-week patterns, explain the conflict and how you weighted each factor.

CONFIDENCE FACTORS:
- Mathematical fit (R²): How well does the slope capture historical data?
- Data consistency: How similar are recent days?
- Clear trends: Is the slope stable or changing?
- Special days: Do you detect weekday patterns that align/conflict with slope?

OUTPUT FORMAT - MUST BE VALID JSON:
Always respond with ONLY valid JSON (no explanatory text). Use this exact structure:
{
    "next_day_1_revenue": number (predicted revenue for tomorrow, explain how slope influenced this),
    "next_day_2_revenue": number (predicted revenue for day after tomorrow),
    "next_day_3_revenue": number (predicted revenue for 3 days from now),
    "confidence_score": number (0-100),
    "confidence_reasoning": "Brief explanation of confidence level - reference the slope R² value and data consistency",
    "growth_rate_percent": number (e.g., 2.5 for +2.5% daily, -1.8 for -1.8%),
    "growth_direction": "Up|Down|Stable",
    "pattern_detected": "String describing the pattern (e.g., 'Weekend spike pattern', 'Steady decline per slope', 'High volatility')",
    "business_impact": "String with actionable insight - mention the slope and what it means for business (e.g., 'Mathematical slope shows +$25/day growth, indicating strong upward trajectory')",
    "mathematical_reasoning": "Explain how you used the provided slope to arrive at these predictions",
    "risk_factors": "List of potential risks to forecast accuracy"
}

CRITICAL RULES:
- ALWAYS output valid JSON only
- NEVER include explanatory text before or after JSON
- Predictions must be reasonable (within 30% of average historical revenue)
- All numbers must be numeric (not strings)
- Confidence score must be 0-100
- ALWAYS reference the slope and R² value in your reasoning"""
    
    def _build_forecasting_message(self, trend_data: Dict[str, float]) -> str:
        """Build the user message for forecasting with mathematical trend analysis."""
        dates = sorted(trend_data.keys())
        revenues = [trend_data[d] for d in dates]
        
        avg_revenue = sum(revenues) / len(revenues) if revenues else 0
        max_revenue = max(revenues) if revenues else 0
        min_revenue = min(revenues) if revenues else 0
        
        # Calculate mathematical trend metrics
        metrics = calculate_trend_metrics(revenues)
        slope = metrics["slope"]
        r_squared = metrics["r_squared"]
        
        # Determine trend direction
        if slope > 50:
            trend_direction = "RAPIDLY GROWING"
        elif slope > 10:
            trend_direction = "GROWING"
        elif slope > 0:
            trend_direction = "SLIGHTLY GROWING"
        elif slope > -10:
            trend_direction = "STABLE"
        elif slope > -50:
            trend_direction = "DECLINING"
        else:
            trend_direction = "RAPIDLY DECLINING"
        
        return f"""Analyze this {len(trend_data)}-day historical revenue data and predict the next 3 days:

HISTORICAL DATA:
{json.dumps(trend_data, indent=2)}

MATHEMATICAL TREND ANALYSIS (Linear Regression):
- Growth Slope: ${slope:.2f} per day (this is the mathematical trend)
- Fit Quality (R²): {r_squared:.3f} (1.0 = perfect fit, closer to 1.0 = more reliable trend)
- Trend Direction: {trend_direction}

SUMMARY STATISTICS:
- Average Daily Revenue: ${avg_revenue:.2f}
- Max Daily Revenue: ${max_revenue:.2f}
- Min Daily Revenue: ${min_revenue:.2f}
- Total Period Revenue: ${sum(revenues):.2f}
- Data Points: {len(revenues)} days

IMPORTANT: Use the mathematical slope (${slope:.2f} per day) to ground your predictions.
This is calculated using linear regression and provides an objective basis for your forecast.
If the slope is positive, revenue is growing at ${slope:.2f} per day.
If the slope is negative, revenue is declining at ${abs(slope):.2f} per day.

Analyze patterns (especially weekday vs weekend differences) and predict tomorrow, day after, and 3 days from now.
Use the slope as a foundation for your forecasts - adjust based on day-of-week patterns if evident.
Include your confidence score and business impact assessment.

Respond with ONLY valid JSON."""
    
    def _parse_forecast_response(
        self,
        ai_response: str,
        trend_data: Dict[str, float]
    ) -> Dict[str, Any]:
        """Parse the AI's JSON forecast response."""
        try:
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                return self._create_fallback_forecast(trend_data)
            
            json_str = ai_response[json_start:json_end]
            forecast = json.loads(json_str)
            
            return forecast
        
        except (json.JSONDecodeError, ValueError):
            return self._create_fallback_forecast(trend_data)
    
    def _create_fallback_forecast(self, trend_data: Dict[str, float]) -> Dict[str, Any]:
        """Create a fallback forecast when AI parsing fails."""
        revenues = list(trend_data.values())
        
        if not revenues:
            return {
                "next_day_1_revenue": 0,
                "next_day_2_revenue": 0,
                "next_day_3_revenue": 0,
                "confidence_score": 0,
                "confidence_reasoning": "Insufficient data for forecast",
                "growth_rate_percent": 0,
                "growth_direction": "Stable",
                "pattern_detected": "No data available",
                "business_impact": "Unable to generate forecast - no historical data",
                "risk_factors": ["No historical data provided"]
            }
        
        # Calculate simple statistics
        avg_revenue = sum(revenues) / len(revenues)
        recent_avg = sum(revenues[-3:]) / 3 if len(revenues) >= 3 else avg_revenue
        
        # Estimate trend (last 3 days vs previous average)
        if len(revenues) >= 3:
            overall_avg = sum(revenues[:-3]) / (len(revenues) - 3)
            growth_rate = ((recent_avg - overall_avg) / overall_avg * 100) if overall_avg > 0 else 0
        else:
            growth_rate = 0
        
        # Generate basic predictions
        prediction_1 = recent_avg * (1 + growth_rate / 100)
        prediction_2 = prediction_1 * (1 + growth_rate / 100)
        prediction_3 = prediction_2 * (1 + growth_rate / 100)
        
        # Calculate volatility for confidence
        if len(revenues) > 1:
            variance = sum((r - avg_revenue) ** 2 for r in revenues) / len(revenues)
            std_dev = variance ** 0.5
            volatility_ratio = std_dev / avg_revenue if avg_revenue > 0 else 0
            confidence = max(0, 100 - (volatility_ratio * 100))
        else:
            confidence = 50
        
        return {
            "next_day_1_revenue": round(prediction_1, 2),
            "next_day_2_revenue": round(prediction_2, 2),
            "next_day_3_revenue": round(prediction_3, 2),
            "confidence_score": round(confidence),
            "confidence_reasoning": "Based on recent trend and volatility analysis",
            "growth_rate_percent": round(growth_rate, 1),
            "growth_direction": "Up" if growth_rate > 0.5 else "Down" if growth_rate < -0.5 else "Stable",
            "pattern_detected": "Trend-based forecast (limited data)",
            "business_impact": f"Average revenue: ${avg_revenue:.2f}. Current trend: {'Growing' if growth_rate > 0 else 'Declining'}",
            "risk_factors": ["Limited historical data for accurate forecasting", "No pattern detection available"]
        }
    
    async def check_profit_margins(
        self,
        menu_items_with_costs: list[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze menu item profit margins and identify pricing dangers.
        
        Evaluates each menu item's margin health:
        - If price < 3x cost: Flag as "Low Margin Risk"
        - Suggests price adjustments or cheaper ingredient alternatives
        - Provides AI-powered optimization recommendations
        
        Args:
            menu_items_with_costs: List of menu items with:
                {
                    "id": int,
                    "name": str,
                    "price": float,
                    "cost_of_goods": float,
                    "margin_percent": float
                }
        
        Returns:
            Dictionary with:
            - status: "success" or "error"
            - risk_items: List of items with low margins
            - total_at_risk_revenue: Estimated revenue from risky items
            - optimization_plan: AI-generated improvement recommendations
        """
        if not menu_items_with_costs:
            return {
                "status": "error",
                "message": "No menu items provided for margin analysis"
            }
        
        system_prompt = self._get_margin_analysis_prompt()
        user_message = self._build_margin_analysis_message(menu_items_with_costs)
        
        try:
            response = self.model.generate_content(
                [
                    {"role": "user", "parts": [system_prompt]},
                    {"role": "user", "parts": [user_message]}
                ],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    top_p=0.95,
                    top_k=40,
                    max_output_tokens=2000
                )
            )
            
            ai_response = response.text
            margin_analysis = self._parse_margin_response(ai_response, menu_items_with_costs)
            
            return {
                "status": "success",
                "analysis": margin_analysis,
                "reasoning": ai_response,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to analyze margins: {str(e)}",
                "analysis": None
            }
    
    def _get_margin_analysis_prompt(self) -> str:
        """System prompt for margin analysis and danger zone detection."""
        return """You are a restaurant financial analyst specializing in profit margin optimization.
Your expertise includes:
- Identifying underpriced menu items (pricing danger zones)
- COGS (Cost of Goods Sold) analysis
- Margin health assessment
- Strategic pricing recommendations
- Cost reduction opportunities

MARGIN ANALYSIS MISSION:
Analyze the provided menu items and their costs. Identify which items are priced dangerously low.

DANGER ZONE DEFINITION:
- LOW MARGIN RISK: Price-to-Cost Ratio < 3:1 (i.e., selling price less than 3x the cost)
  Example: If cost is $3.00 and price is $8.00 (ratio 2.67:1), this is a danger zone
- These items are losing money when overhead costs are considered
- Even seemingly healthy margins can hide profitability issues

YOUR ANALYSIS MUST:
1. Identify all items with price < 3x cost
2. Calculate the financial impact (lost profit per item)
3. Estimate total revenue at risk from low-margin items
4. Suggest specific remedies:
   - Price increase: How much can this item support without losing customers?
   - Cost reduction: Can ingredients be substituted? Portion sizes adjusted?
   - Discontinuation: Is it better to remove this item entirely?

OUTPUT FORMAT - MUST BE VALID JSON:
{
    "risk_items": [
        {
            "item_name": "String - exact menu item name",
            "current_price": number,
            "cost_of_goods": number,
            "price_to_cost_ratio": number (e.g., 2.5 means price is 2.5x cost),
            "margin_percent": number,
            "danger_level": "Critical|High|Medium",
            "estimated_loss_per_item": number (estimated loss considering overhead),
            "recommendation": "Specific action (price increase X%, reduce ingredient cost Y, or discontinue)",
            "suggested_price": number (if price increase recommended),
            "price_increase_percent": number,
            "alternative_action": "String describing cost reduction opportunity"
        }
    ],
    "healthy_items": [
        {
            "item_name": "String",
            "margin_percent": number,
            "price_to_cost_ratio": number
        }
    ],
    "optimization_plan": {
        "total_items_analyzed": number,
        "items_at_risk": number,
        "total_current_revenue_at_risk": number,
        "potential_monthly_margin_improvement": number,
        "top_3_actions": [
            {"action": "Exact action", "expected_monthly_impact": "String with $amount"},
            {"action": "Exact action", "expected_monthly_impact": "String with $amount"},
            {"action": "Exact action", "expected_monthly_impact": "String with $amount"}
        ],
        "executive_summary": "One paragraph summary of findings and recommendations"
    },
    "cost_strategies": [
        {
            "ingredient_name_or_item": "String",
            "current_strategy": "Current approach",
            "proposed_change": "What to change",
            "estimated_savings": "String with $ amount per month",
            "implementation": "How to execute"
        }
    ]
}

CRITICAL RULES:
- ALWAYS output valid JSON only
- Price-to-cost ratio = selling_price / cost_of_goods
- All financial numbers MUST be numeric (not strings)
- Flag items where ratio < 3.0 as danger zones
- Suggest specific prices, not ranges
- Consider pricing psychology (customers expect "nice" prices like $9.99)
- Every recommendation must be actionable TODAY"""
    
    def _build_margin_analysis_message(self, menu_items_with_costs: list[Dict[str, Any]]) -> str:
        """Build the user message for margin analysis."""
        total_items = len(menu_items_with_costs)
        total_revenue = sum(float(item.get("price", 0)) for item in menu_items_with_costs)
        
        danger_count = 0
        for item in menu_items_with_costs:
            price = float(item.get("price", 0))
            cogs = float(item.get("cost_of_goods", 0))
            if cogs > 0 and price / cogs < 3.0:
                danger_count += 1
        
        return f"""Analyze the following {total_items} menu items and their cost of goods sold (COGS).
Identify which items are in the "Danger Zone" (price less than 3x cost) and recommend actions.

MENU ITEMS WITH COSTS:
{json.dumps(menu_items_with_costs, indent=2, default=str)}

SUMMARY:
- Total items: {total_items}
- Combined daily selling price total: ${total_revenue:.2f}
- Items potentially in danger zone: {danger_count}

Analyze margin health, identify danger zones, and provide specific recommendations.
Calculate price-to-cost ratios and determine which items need immediate action.

RESPOND WITH VALID JSON ONLY."""
    
    def _parse_margin_response(
        self,
        ai_response: str,
        menu_items_with_costs: list[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Parse the AI's margin analysis response."""
        try:
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                return self._create_fallback_margin_analysis(menu_items_with_costs)
            
            json_str = ai_response[json_start:json_end]
            analysis = json.loads(json_str)
            
            return analysis
        
        except (json.JSONDecodeError, ValueError):
            return self._create_fallback_margin_analysis(menu_items_with_costs)
    
    def _create_fallback_margin_analysis(self, menu_items_with_costs: list[Dict[str, Any]]) -> Dict[str, Any]:
        """Create fallback margin analysis."""
        risk_items = []
        healthy_items = []
        total_revenue_at_risk = 0.0
        total_improvement = 0.0
        
        for item in menu_items_with_costs:
            name = item.get("name", "Unknown Item")
            price = float(item.get("price", 0))
            cogs = float(item.get("cost_of_goods", 0))
            margin = float(item.get("margin_percent", 0))
            
            if cogs > 0:
                ratio = price / cogs
                if ratio < 3.0:
                    suggested_price = cogs * 3.2  # 3.2x multiplier adds margin
                    increase = ((suggested_price - price) / price) * 100
                    potential_gain = (suggested_price - price)
                    total_revenue_at_risk += price
                    total_improvement += potential_gain
                    
                    risk_items.append({
                        "item_name": name,
                        "current_price": price,
                        "cost_of_goods": cogs,
                        "price_to_cost_ratio": round(ratio, 2),
                        "margin_percent": margin,
                        "danger_level": "Critical" if ratio < 2.0 else "High" if ratio < 2.5 else "Medium",
                        "estimated_loss_per_item": round(cogs * 0.5, 2),
                        "recommendation": f"Increase price by {increase:.0f}%",
                        "suggested_price": round(suggested_price, 2),
                        "price_increase_percent": round(increase, 1),
                        "alternative_action": "Review ingredient sourcing to reduce COGS"
                    })
                else:
                    healthy_items.append({
                        "item_name": name,
                        "margin_percent": margin,
                        "price_to_cost_ratio": round(ratio, 2)
                    })
        
        return {
            "risk_items": risk_items,
            "healthy_items": healthy_items,
            "optimization_plan": {
                "total_items_analyzed": len(menu_items_with_costs),
                "items_at_risk": len(risk_items),
                "total_current_revenue_at_risk": round(total_revenue_at_risk, 2),
                "potential_monthly_margin_improvement": round(total_improvement * 30, 2),  # Rough estimate
                "top_3_actions": [
                    {
                        "action": f"Price adjustment for {min(3, len(risk_items))} high-risk items" if risk_items else "Review menu pricing",
                        "expected_monthly_impact": f"${round(total_improvement * 30, 2)}"
                    },
                    {
                        "action": "Conduct supplier negotiation for top 5 ingredients",
                        "expected_monthly_impact": "$500-$1000"
                    },
                    {
                        "action": "Review portion sizes on COGS-heavy items",
                        "expected_monthly_impact": "$300-$500"
                    }
                ],
                "executive_summary": f"Analysis of {len(menu_items_with_costs)} menu items identified {len(risk_items)} items with margin concerns. These items are priced below the healthy 3:1 cost-to-price ratio. Immediate price increases on top items could improve monthly margins by ${round(total_improvement * 30, 2)}."
            },
            "cost_strategies": []
        }
    
    async def process_review(self, customer_comment: str) -> Dict[str, Any]:
        """Analyze a customer review for sentiment and actionable insights.
        
        Uses Gemini to perform comprehensive review analysis:
        1. Assign sentiment score (-1.0 to 1.0)
        2. Extract key topics/keywords
        3. Generate actionable recommendation for manager
        4. Create one-sentence summary
        
        Args:
            customer_comment: The full text of the customer's review/feedback
            
        Returns:
            Dictionary with:
            - status: "success" or "error"
            - sentiment_score: Float from -1.0 (very negative) to 1.0 (very positive)
            - sentiment_label: "positive", "neutral", or "negative"
            - keywords: List of key topics mentioned
            - ai_summary: One-sentence executive summary
            - action_item: Specific actionable recommendation
            - reasoning: Full AI analysis text
        """
        system_prompt = self._get_sentiment_analysis_prompt()
        user_message = f"""Please analyze this customer review:

"{customer_comment}"

Provide your response as valid JSON with the following structure:
{{
    "sentiment_score": <float from -1.0 to 1.0>,
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "ai_summary": "One sentence summary of the review's main point",
    "action_item": "Specific actionable recommendation for the manager"
}}"""
        
        try:
            response = self.model.generate_content(
                [
                    {"role": "user", "parts": [system_prompt]},
                    {"role": "user", "parts": [user_message]}
                ],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.5,
                    top_p=0.95,
                    top_k=40,
                    max_output_tokens=500
                )
            )
            
            ai_response = response.text
            analysis = self._parse_sentiment_response(ai_response)
            
            return {
                "status": "success",
                "sentiment_score": analysis.get("sentiment_score", 0.0),
                "sentiment_label": self._get_sentiment_label(analysis.get("sentiment_score", 0.0)),
                "keywords": analysis.get("keywords", []),
                "ai_summary": analysis.get("ai_summary", ""),
                "action_item": analysis.get("action_item", ""),
                "reasoning": ai_response,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to analyze review sentiment: {str(e)}",
                "sentiment_score": 0.0,
                "sentiment_label": "neutral"
            }
    
    def _get_sentiment_analysis_prompt(self) -> str:
        """System prompt for comprehensive sentiment analysis of customer reviews."""
        return """You are an expert restaurant sentiment analyst with deep expertise in:
- Customer sentiment analysis and emotional intelligence
- Restaurant operations and service quality issues
- Food quality assessment and common complaints
- Service excellence standards
- Problem identification and resolution

SENTIMENT ANALYSIS MISSION:
Analyze the provided customer review and extract:

1. SENTIMENT SCORE (-1.0 to 1.0):
   - 1.0: Extremely positive (delighted customer)
   - 0.5: Positive (good experience)
   - 0.0: Neutral (balanced positive and negative)
   - -0.5: Negative (problems experienced)
   - -1.0: Extremely negative (very upset customer)

2. KEYWORDS: Extract 3-5 key topics mentioned (e.g., "cold food", "great service", "slow service", "friendly staff")

3. AI SUMMARY: Create ONE sentence that captures the essence of the feedback

4. ACTION ITEM: Provide ONE specific, actionable recommendation for the restaurant manager.
   - If positive: How to replicate this success?
   - If negative: What specific problem to fix?
   - Example: "Check the heating lamp in the kitchen as burgers were served cold"
   - Example: "Server training session on upselling wine pairings"

CRITICAL RULES:
- ONLY output valid JSON, no other text
- sentiment_score must be a number between -1.0 and 1.0
- keywords must be a simple list of strings
- action_item must be a single, specific, actionable sentence
- ai_summary must be exactly one sentence
- Never output markdown, just pure JSON"""
    
    def _parse_sentiment_response(self, ai_response: str) -> Dict[str, Any]:
        """Parse the AI's JSON sentiment analysis response."""
        try:
            # Try to extract JSON from the response
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                return self._create_fallback_sentiment(ai_response)
            
            json_str = ai_response[json_start:json_end]
            analysis = json.loads(json_str)
            
            return analysis
        
        except (json.JSONDecodeError, ValueError):
            return self._create_fallback_sentiment(ai_response)
    
    def _create_fallback_sentiment(self, text: str) -> Dict[str, Any]:
        """Create fallback sentiment analysis when parsing fails."""
        # Simple heuristic-based fallback
        text_lower = text.lower()
        
        # Positive keywords
        positive_words = ["great", "excellent", "amazing", "love", "perfect", "best", "awesome", "wonderful", "fantastic"]
        # Negative keywords
        negative_words = ["bad", "terrible", "awful", "hate", "worst", "poor", "disappointed", "horrible", "disgusting"]
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        # Calculate simple sentiment
        if positive_count > negative_count:
            sentiment = 0.5 + (positive_count * 0.1)
        elif negative_count > positive_count:
            sentiment = -0.5 - (negative_count * 0.1)
        else:
            sentiment = 0.0
        
        sentiment = max(-1.0, min(1.0, sentiment))
        
        return {
            "sentiment_score": sentiment,
            "keywords": ["review analysis pending"],
            "ai_summary": "Review received and flagged for analysis",
            "action_item": "Manager review required for detailed assessment"
        }
    
    def _get_sentiment_label(self, score: float) -> str:
        """Convert sentiment score to label."""
        if score >= 0.5:
            return "positive"
        elif score <= -0.5:
            return "negative"
        else:
            return "neutral"
    
    async def calculate_labor_efficiency(
        self,
        hourly_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze labor cost vs. sales volume to identify staffing inefficiencies.
        
        Compares hourly labor costs against hourly sales to identify:
        1. Inefficient hours (labor > 30% of sales)
        2. Burnout risks (high sales with low staffing)
        3. Optimal staffing recommendations
        
        Args:
            hourly_data: Dictionary with hourly breakdown:
            {
                "date": "YYYY-MM-DD",
                "hours": [
                    {
                        "hour": 0-23,
                        "sales_amount": float,
                        "labor_cost": float,
                        "staff_count": int,
                        "average_table_occupancy": float
                    },
                    ...
                ],
                "daily_total_sales": float,
                "daily_total_labor": float,
                "staff_scheduled": int
            }
            
        Returns:
            Dictionary with:
            - status: "success" or "error"
            - efficiency_score: 0-100 (100 = optimal)
            - efficiency_label: "Excellent", "Good", "Fair", "Poor"
            - inefficient_hours: List of problematic hours
            - burnout_risks: List of high-volume, low-staff hours
            - optimization_suggestions: AI-powered recommendations
            - recommended_actions: Specific staffing changes
        """
        system_prompt = self._get_labor_efficiency_prompt()
        user_message = f"""Please analyze this hourly labor-to-sales data:

{json.dumps(hourly_data, indent=2, default=str)}

Identify:
1. Hours where labor cost > 30% of sales (inefficient)
2. Hours with high sales but low staffing (burnout risk)
3. Overstaffed vs understaffed patterns
4. Recommended staffing changes for next week

Provide response as valid JSON."""
        
        try:
            response = self.model.generate_content(
                [
                    {"role": "user", "parts": [system_prompt]},
                    {"role": "user", "parts": [user_message]}
                ],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.6,
                    top_p=0.95,
                    top_k=40,
                    max_output_tokens=1500
                )
            )
            
            ai_response = response.text
            analysis = self._parse_labor_efficiency_response(ai_response, hourly_data)
            
            return {
                "status": "success",
                "efficiency_analysis": analysis,
                "reasoning": ai_response,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to analyze labor efficiency: {str(e)}",
                "efficiency_analysis": None
            }
    
    def _get_labor_efficiency_prompt(self) -> str:
        """System prompt for labor efficiency and staffing analysis."""
        return """You are a restaurant operations expert specializing in labor optimization and staffing.
Your expertise includes:
- Labor cost as percentage of sales
- Staff productivity metrics
- Burnout detection and prevention
- Schedule optimization
- Peak vs. off-peak hour management

LABOR EFFICIENCY MISSION:
Analyze the provided hourly labor and sales data to identify:

1. INEFFICIENCY DETECTION:
   - If Labor Cost > 30% of Sales in an hour, flag as "Inefficient"
   - Example: $500 sales with $200 labor = 40% (TOO HIGH)
   - These are hours with too many people working

2. BURNOUT RISK DETECTION:
   - If Sales are HIGH but Staff Count is LOW in an hour, flag as "Burnout Risk"
   - Example: $2000 sales with only 2 staff members
   - These are high-pressure hours that will exhaust your team

3. STAFFING RECOMMENDATIONS:
   - Which hours are overstaffed? (potential cost savings)
   - Which hours are understaffed? (risk of poor service)
   - Which staff can be moved to busier shifts?

METRICS TO CALCULATE:
- Labor cost as percentage of sales (should be 20-30%)
- Sales per staff member (higher is better, but not if too high)
- Overall efficiency score (0-100)

OUTPUT FORMAT - MUST BE VALID JSON:"""
    
    def _parse_labor_efficiency_response(
        self,
        ai_response: str,
        hourly_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse AI labor efficiency analysis response."""
        try:
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                return self._create_fallback_labor_analysis(hourly_data)
            
            json_str = ai_response[json_start:json_end]
            analysis = json.loads(json_str)
            return analysis
        
        except (json.JSONDecodeError, ValueError):
            return self._create_fallback_labor_analysis(hourly_data)
    
    def _create_fallback_labor_analysis(
        self,
        hourly_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create fallback labor efficiency analysis when AI fails."""
        hours = hourly_data.get("hours", [])
        
        inefficient_hours = []
        burnout_risks = []
        total_efficiency = 0
        
        for hour_data in hours:
            sales = float(hour_data.get("sales_amount", 0))
            labor = float(hour_data.get("labor_cost", 0))
            staff = int(hour_data.get("staff_count", 0))
            
            # Calculate labor percentage
            if sales > 0:
                labor_percent = (labor / sales) * 100
                if labor_percent > 30:
                    inefficient_hours.append({
                        "hour": hour_data.get("hour", 0),
                        "sales": sales,
                        "labor": labor,
                        "labor_percent": round(labor_percent, 1),
                        "issue": "Overstaffed - Labor > 30% of sales"
                    })
            
            # Detect burnout risk
            if sales > 1000 and staff < 3:
                burnout_risks.append({
                    "hour": hour_data.get("hour", 0),
                    "sales": sales,
                    "staff_count": staff,
                    "sales_per_staff": round(sales / staff, 2) if staff > 0 else sales,
                    "issue": "High sales with low staffing - burnout risk"
                })
            
            # Accumulate for efficiency score
            if sales > 0 and labor > 0:
                labor_percent = (labor / sales) * 100
                # Ideal is 25%
                if labor_percent <= 25:
                    total_efficiency += 100
                elif labor_percent <= 30:
                    total_efficiency += 80
                elif labor_percent <= 35:
                    total_efficiency += 60
                else:
                    total_efficiency += 40
        
        avg_efficiency = int(total_efficiency / len(hours)) if hours else 50
        
        return {
            "efficiency_score": avg_efficiency,
            "efficiency_label": "Excellent" if avg_efficiency >= 80 else
                                "Good" if avg_efficiency >= 60 else
                                "Fair" if avg_efficiency >= 40 else "Poor",
            "inefficient_hours": inefficient_hours,
            "burnout_risks": burnout_risks,
            "optimization_suggestions": [
                f"Reduce staff by 1-2 people in {len(inefficient_hours)} overstaffed hours"
                if inefficient_hours else "Overall staffing looks good",
                f"Increase staff or improve service speed in {len(burnout_risks)} high-volume hours"
                if burnout_risks else "No extreme burnout risks detected"
            ],
            "recommended_actions": [
                "Review staffing for hours with labor > 30% of sales",
                "Consider cross-training for flexibility in peak hours",
                "Analyze if lower-traffic hours can function with fewer staff"
            ]
        }


# Global instance
_consultant: Optional[AIConsultant] = None


def get_ai_consultant() -> AIConsultant:
    """Get or create the AI consultant instance."""
    global _consultant
    if _consultant is None:
        _consultant = AIConsultant()
    return _consultant


async def generate_restaurant_strategy(
    performance_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Convenience function to generate strategy using the global consultant."""
    consultant = get_ai_consultant()
    return await consultant.generate_strategy(performance_data)


async def forecast_revenue(
    trend_data: Dict[str, float]
) -> Dict[str, Any]:
    """Convenience function to generate revenue forecast using the global consultant."""
    consultant = get_ai_consultant()
    return await consultant.predict_revenue(trend_data)


async def analyze_profit_margins(
    menu_items_with_costs: list[Dict[str, Any]]
) -> Dict[str, Any]:
    """Convenience function to analyze profit margins using the global consultant."""
    consultant = get_ai_consultant()
    return await consultant.check_profit_margins(menu_items_with_costs)


async def process_review(customer_comment: str) -> Dict[str, Any]:
    """Convenience function to analyze review sentiment using the global consultant."""
    consultant = get_ai_consultant()
    return await consultant.process_review(customer_comment)


async def calculate_labor_efficiency(hourly_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to analyze labor efficiency using the global consultant."""
    consultant = get_ai_consultant()
    return await consultant.calculate_labor_efficiency(hourly_data)

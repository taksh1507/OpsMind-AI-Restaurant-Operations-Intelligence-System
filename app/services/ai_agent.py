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
from typing import Dict, Any, Optional
import google.generativeai as genai
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
        self.model = genai.GenerativeModel("gemini-1.5-flash")
    
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

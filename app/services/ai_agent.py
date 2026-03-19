"""AI Agent Service - Autonomous Restaurant Consultant

Uses Google Gemini 1.5 Flash to analyze restaurant performance data
and provide expert consulting recommendations.
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
        """Return the default system prompt for restaurant consulting."""
        return """You are a world-class restaurant consultant with 20+ years of experience.
Your role is to analyze restaurant performance data and provide expert, actionable insights.

When given performance metrics, you must:
1. Identify the 'Star' dish - what's performing exceptionally well
2. Identify the 'Underperformer' - any dish with low profit margins but high volume
3. Suggest ONE specific price adjustment that could improve profitability
4. Suggest ONE concrete inventory/cost-saving opportunity
5. Provide an overall health assessment of the business

Always be specific with numbers and percentages. Avoid vague recommendations.
Focus on what the owner can DO TODAY, not abstract concepts.

You will receive detailed performance data. Analyze it thoroughly and provide structured recommendations.
Format your response as valid JSON with these exact keys:
{
    "star_dish": {"name": string, "reason": string, "current_performance": string},
    "underperformer": {"name": string, "reason": string, "volume_units": number},
    "price_recommendation": {
        "item": string,
        "current_price": number,
        "suggested_price": number,
        "price_change_percent": number,
        "expected_impact": string,
        "rationale": string
    },
    "inventory_saving": {
        "area": string,
        "current_cost": string,
        "estimated_savings": string,
        "action": string
    },
    "overall_health": {
        "rating": string,  // "Excellent", "Good", "Fair", "Needs Attention"
        "margin_assessment": string,
        "volume_assessment": string
    },
    "actionable_insights": [
        {"priority": "High|Medium|Low", "action": string, "expected_result": string}
    ]
}"""
    
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
        """Create a fallback strategy structure when AI parsing fails."""
        top_items = performance_data.get("top_selling_items", [])
        
        return {
            "star_dish": {
                "name": top_items[0]["name"] if top_items else "Unknown",
                "reason": "Top seller by revenue",
                "current_performance": f"${top_items[0].get('revenue_generated', 0):.2f} generated"
            },
            "underperformer": {
                "name": top_items[-1]["name"] if top_items else "Unknown",
                "reason": "Lower performer in product mix",
                "volume_units": top_items[-1].get("quantity_sold", 0) if top_items else 0
            },
            "price_recommendation": {
                "item": "Review popular items for price optimization",
                "expected_impact": "Recommend professional analysis"
            },
            "inventory_saving": {
                "area": "Conduct full inventory audit",
                "estimated_savings": "Requires detailed analysis"
            },
            "overall_health": {
                "rating": "Good" if performance_data.get("profit_margin_percent", 0) > 30 else "Fair",
                "margin_assessment": f"Current margin: {performance_data.get('profit_margin_percent', 0):.1f}%"
            },
            "actionable_insights": [
                {
                    "priority": "High",
                    "action": "Review pricing strategy for top sellers",
                    "expected_result": "Improved profitability"
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

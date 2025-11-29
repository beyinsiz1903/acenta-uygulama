"""
AI Intelligence Service for Hotel Management System
Provides AI-powered insights, predictions, and recommendations
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import asyncio
from dotenv import load_dotenv
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    _AI_BACKEND_AVAILABLE = True
except Exception:
    LlmChat = None
    UserMessage = None
    _AI_BACKEND_AVAILABLE = False

# Load environment variables
load_dotenv()

class AIService:
    def __init__(self):
        if not _AI_BACKEND_AVAILABLE:
            # Fallback mode: no external LLM backend available
            self.api_key = None
        else:
            self.api_key = os.getenv('EMERGENT_LLM_KEY')
            if not self.api_key:
                raise ValueError("EMERGENT_LLM_KEY not found in environment variables")
    
    def _create_chat(self, system_message: str, session_id: str = "default") -> LlmChat:
        """Create a new chat instance with the specified system message.
        If LLM backend is not available, raise a clear error so callers can
        fallback to heuristic logic instead of crashing the app.
        """
        if not _AI_BACKEND_AVAILABLE or not self.api_key or LlmChat is None:
            raise RuntimeError("LLM backend not available")

        chat = LlmChat(
            api_key=self.api_key,
            session_id=session_id,
            system_message=system_message
        )
        # Use GPT-4o-mini for fast, cost-effective responses
        chat.with_model("openai", "gpt-4o-mini")
        return chat
    
    async def generate_daily_briefing(
        self, 
        hotel_name: str,
        total_rooms: int,
        occupied_rooms: int,
        today_checkins: int,
        today_checkouts: int,
        pending_invoices: int,
        monthly_revenue: float,
        weather: str = "clear"
    ) -> str:
        """
        Generate a natural language daily briefing for the dashboard
        """
        system_message = """You are a hotel management AI assistant. 
        Provide concise, friendly, and actionable daily briefings for hotel managers.
        Focus on key metrics, trends, and actionable insights.
        Keep responses under 100 words."""
        
        chat = self._create_chat(system_message, session_id=f"briefing_{datetime.now().strftime('%Y%m%d')}")
        
        occupancy_rate = (occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0
        
        prompt = f"""Generate a morning briefing for {hotel_name}:
        
Current Status:
- Total Rooms: {total_rooms}
- Occupied: {occupied_rooms} ({occupancy_rate:.1f}% occupancy)
- Today's Check-ins: {today_checkins}
- Today's Check-outs: {today_checkouts}
- Pending Invoices: {pending_invoices}
- Monthly Revenue: ${monthly_revenue:,.2f}
- Weather: {weather}

Provide a friendly greeting, highlight key metrics, and give 1-2 actionable insights or predictions for today."""
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        return response
    
    async def predict_occupancy(
        self,
        historical_data: List[Dict[str, Any]],
        current_occupancy: float,
        upcoming_bookings: int,
        season: str = "normal"
    ) -> Dict[str, Any]:
        """
        Predict occupancy trends and patterns for PMS
        """
        system_message = """You are a hotel revenue management AI.
        Analyze occupancy data and provide predictions with confidence levels.
        Be data-driven and provide specific numbers."""
        
        chat = self._create_chat(system_message, session_id="occupancy_prediction")
        
        prompt = f"""Analyze this hotel occupancy data:

Current occupancy: {current_occupancy}%
Upcoming bookings (next 7 days): {upcoming_bookings}
Season: {season}
Historical data points: {len(historical_data)}

Based on this data:
1. Predict tomorrow's occupancy percentage
2. Predict next week's average occupancy
3. Identify any concerning patterns
4. Provide 1-2 actionable recommendations

Format your response as JSON with keys: tomorrow_prediction, next_week_prediction, patterns, recommendations"""
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        # Try to parse as JSON, fallback to text response
        try:
            import json
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                return json.loads(response[json_start:json_end])
        except:
            pass
        
        return {
            "prediction": response,
            "confidence": "medium"
        }
    
    async def analyze_guest_patterns(
        self,
        checkin_times: List[str],
        checkout_times: List[str],
        guest_count: int
    ) -> str:
        """
        Analyze check-in/check-out patterns for staffing optimization
        """
        system_message = """You are a hotel operations AI.
        Analyze guest patterns to optimize staffing and operations."""
        
        chat = self._create_chat(system_message, session_id="pattern_analysis")
        
        prompt = f"""Analyze these guest patterns:

Check-in times: {', '.join(checkin_times[:10])}
Check-out times: {', '.join(checkout_times[:10])}
Total guests: {guest_count}

Identify:
1. Peak check-in/check-out hours
2. Staffing recommendations
3. Any unusual patterns

Keep response concise (under 80 words)."""
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        return response
    
    async def categorize_expense(
        self,
        description: str,
        amount: float,
        vendor: str = ""
    ) -> Dict[str, str]:
        """
        Automatically categorize expenses for invoicing
        """
        system_message = """You are a hotel accounting AI.
        Categorize expenses accurately based on description and amount.
        Categories: Utilities, Supplies, Maintenance, Food & Beverage, Marketing, Staff, Other"""
        
        chat = self._create_chat(system_message, session_id="expense_categorization")
        
        prompt = f"""Categorize this expense:

Description: {description}
Amount: ${amount}
Vendor: {vendor}

Respond with just the category name and a confidence level (high/medium/low).
Format: Category: [category], Confidence: [level]"""
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        # Parse response
        category = "Other"
        confidence = "medium"
        
        if "Category:" in response:
            try:
                parts = response.split(',')
                category = parts[0].split(':')[1].strip()
                if len(parts) > 1:
                    confidence = parts[1].split(':')[1].strip().lower()
            except:
                pass
        
        return {
            "category": category,
            "confidence": confidence,
            "raw_response": response
        }
    
    async def detect_invoice_anomalies(
        self,
        invoices: List[Dict[str, Any]],
        average_amount: float
    ) -> List[Dict[str, Any]]:
        """
        Detect unusual patterns in invoices
        """
        system_message = """You are a financial analysis AI for hotels.
        Detect anomalies, unusual patterns, or potential issues in invoice data."""
        
        chat = self._create_chat(system_message, session_id="invoice_analysis")
        
        # Summarize invoice data
        invoice_summary = []
        for inv in invoices[:10]:  # Analyze last 10
            invoice_summary.append(f"${inv.get('total', 0):.2f} - {inv.get('customer_name', 'Unknown')}")
        
        prompt = f"""Analyze these recent invoices:

{chr(10).join(invoice_summary)}

Average invoice amount: ${average_amount:.2f}

Identify:
1. Any unusually high/low amounts
2. Potential duplicate invoices
3. Any concerning patterns

List only genuine anomalies. Be concise."""
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        return [{
            "type": "analysis",
            "message": response
        }]
    
    async def segment_guests(
        self,
        guests: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Segment guests for loyalty program targeting
        """
        system_message = """You are a hotel marketing AI.
        Segment guests into categories for targeted marketing and loyalty programs."""
        
        chat = self._create_chat(system_message, session_id="guest_segmentation")
        
        # Create guest summary
        guest_summary = f"Total guests: {len(guests)}\n"
        if len(guests) > 0:
            # Sample some guest data
            sample_guests = guests[:5]
            for g in sample_guests:
                guest_summary += f"- {g.get('name', 'Guest')}: {g.get('total_stays', 0)} stays, ${g.get('total_spent', 0):.2f} spent\n"
        
        prompt = f"""Analyze this guest data and create segments:

{guest_summary}

Create 3-4 guest segments (e.g., VIP, Regular, New, At-Risk) with:
1. Segment criteria
2. Marketing strategy for each
3. Predicted lifetime value

Format as JSON with segments array."""
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        return {
            "segments_analysis": response,
            "total_guests": len(guests)
        }
    
    async def predict_churn_risk(
        self,
        guest_id: str,
        last_visit_days: int,
        total_visits: int,
        average_spend: float
    ) -> Dict[str, Any]:
        """
        Predict if a guest is at risk of churning
        """
        system_message = """You are a customer retention AI for hotels.
        Predict churn risk and recommend retention strategies."""
        
        chat = self._create_chat(system_message, session_id=f"churn_{guest_id}")
        
        prompt = f"""Assess churn risk for this guest:

Last visit: {last_visit_days} days ago
Total visits: {total_visits}
Average spend per visit: ${average_spend:.2f}

Provide:
1. Churn risk level (low/medium/high)
2. Key risk factors
3. 1-2 retention recommendations

Be concise (under 60 words)."""
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        # Determine risk level from response
        risk_level = "medium"
        if "high" in response.lower():
            risk_level = "high"
        elif "low" in response.lower():
            risk_level = "low"
        
        return {
            "risk_level": risk_level,
            "analysis": response
        }
    
    async def recommend_products(
        self,
        inventory: List[Dict[str, Any]],
        recent_orders: List[Dict[str, Any]],
        season: str = "normal"
    ) -> List[Dict[str, Any]]:
        """
        Recommend products to order based on usage patterns
        """
        system_message = """You are a hotel procurement AI.
        Recommend products to order based on inventory levels and usage patterns."""
        
        chat = self._create_chat(system_message, session_id="product_recommendations")
        
        # Summarize inventory
        low_stock_items = [item for item in inventory if item.get('quantity', 0) < item.get('reorder_level', 10)]
        
        prompt = f"""Analyze inventory and recommend orders:

Low stock items: {len(low_stock_items)}
Recent orders (last month): {len(recent_orders)}
Season: {season}

Based on typical hotel needs and the season, recommend:
1. Top 3 items to reorder immediately
2. Quantities for each
3. Any seasonal items to stock up on

Keep it concise and practical."""
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        return [{
            "type": "recommendation",
            "message": response,
            "low_stock_count": len(low_stock_items)
        }]
    
    async def analyze_revenue_trends(
        self,
        revenue_data: List[Dict[str, Any]],
        current_month_revenue: float,
        last_month_revenue: float
    ) -> str:
        """
        Analyze revenue trends for RMS insights
        """
        system_message = """You are a hotel revenue management AI.
        Analyze revenue trends and provide strategic insights."""
        
        chat = self._create_chat(system_message, session_id="revenue_analysis")
        
        change_percent = ((current_month_revenue - last_month_revenue) / last_month_revenue * 100) if last_month_revenue > 0 else 0
        
        prompt = f"""Analyze revenue trends:

Current month: ${current_month_revenue:,.2f}
Last month: ${last_month_revenue:,.2f}
Change: {change_percent:+.1f}%

Data points: {len(revenue_data)}

Provide:
1. Trend analysis
2. Contributing factors
3. 1-2 pricing recommendations

Keep under 80 words."""
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        return response


# Lazy-loaded singleton instance
_ai_service_instance = None

def get_ai_service():
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AIService()
    return _ai_service_instance

# For backwards compatibility
ai_service = None  # Will be initialized on first use

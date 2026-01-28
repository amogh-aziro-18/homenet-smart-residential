"""
Forecast Agent - LLM-powered demand forecasting analysis with LangGraph
INTEGRATED WITH AMOGH'S ML MODEL
"""
import sys
import os
from datetime import datetime, timedelta

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from agents.state import AgentState
from agents.llm_config import get_llm
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage


def forecast_agent_node(state: AgentState) -> dict:
    """
    LLM-powered Forecast Agent with REAL ML predictions
    Analyzes demand forecasts and makes capacity decisions
    """
    building_id = state.get("building_id")
    
    new_messages = [AIMessage(content=f"📈 AI Forecast Agent analyzing building: {building_id}")]
    
    updates = {
        "current_agent": "forecast",
        "next_agent": "supervisor",
        "messages": new_messages,
    }
    
    try:
        # ✅ IMPORT AND USE AMOGH'S REAL ML MODEL
        from models.demand_forecast.predict import forecast_water_demand
        
        # Get real ML forecast
        ml_forecast = forecast_water_demand(asset_id=building_id, horizon_hours=24)
        
        # Extract ML predictions
        forecast_total = ml_forecast.get("forecast_total", 0)
        demand_level = ml_forecast.get("demand_level", "UNKNOWN")  # HIGH/MEDIUM/LOW
        peak_hour = ml_forecast.get("peak_hour", {})
        peak_value = peak_hour.get("value", 0) if peak_hour else 0
        peak_time_str = peak_hour.get("timestamp", "N/A") if peak_hour else "N/A"
        recommendation = ml_forecast.get("recommendation", "No recommendation")
        
        # Calculate capacity percentages (adjust MAX_CAPACITY based on your system)
        MAX_CAPACITY_PER_HOUR = 500  # liters per hour (adjust to your tank capacity)
        current_demand = min(100, int((forecast_total / 24) / MAX_CAPACITY_PER_HOUR * 100))
        predicted_demand = min(100, int(peak_value / MAX_CAPACITY_PER_HOUR * 100))
        
        # Parse peak time
        try:
            peak_time = datetime.fromisoformat(peak_time_str) if peak_time_str != "N/A" else datetime.now() + timedelta(hours=2)
        except:
            peak_time = datetime.now() + timedelta(hours=2)
        
        updates.update({
            "current_demand": current_demand,
            "predicted_demand": predicted_demand,
            "peak_time": peak_time.isoformat(),
            "forecast_total": forecast_total,
            "demand_level": demand_level,
            "ml_recommendation": recommendation,
        })
        
        # Use LLM for intelligent reasoning based on REAL ML data
        llm = get_llm()
        
        prompt = f"""You are an AI demand forecasting agent analyzing water demand capacity.

BUILDING: {building_id}

ML FORECAST RESULTS:
- Total 24h Demand: {forecast_total:.2f} liters
- Demand Level: {demand_level}
- Peak Hour: {peak_time.strftime('%Y-%m-%d %H:%M')}
- Peak Value: {peak_value:.2f} liters
- Current Avg Demand: {current_demand}% of hourly capacity
- Predicted Peak Demand: {predicted_demand}% of hourly capacity
- ML Recommendation: {recommendation}

CAPACITY THRESHOLDS:
- 95%+ : Critical - immediate action required
- 85-94% : High - prepare backup systems
- 70-84% : Medium - enhanced monitoring
- <70% : Normal - standard monitoring

Based on this REAL ML forecast data, decide:
1. ACTION_REQUIRED: true/false
2. ACTION_TYPE: capacity_alert | capacity_monitoring | enhanced_monitoring | none
3. PRIORITY: CRITICAL | HIGH | MEDIUM | LOW
4. SLA_HOURS: 2 | 6 | 12 | null
5. REASONING: Brief explanation (max 2 sentences)

Respond in this exact format:
ACTION_REQUIRED: [true/false]
ACTION_TYPE: [type]
PRIORITY: [priority]
SLA_HOURS: [hours]
REASONING: [your reasoning]
"""
        
        response = llm.invoke([
            SystemMessage(content="You are an expert facility management AI assistant specializing in demand forecasting and capacity planning."),
            HumanMessage(content=prompt)
        ])
        
        # Parse LLM response
        lines = response.content.strip().split('\n')
        llm_decision = {}
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                llm_decision[key.strip()] = value.strip()
        
        # Apply LLM decision
        action_required = llm_decision.get("ACTION_REQUIRED", "false").lower() == "true"
        action_type = llm_decision.get("ACTION_TYPE", "none")
        priority = llm_decision.get("PRIORITY", "LOW")
        reasoning = llm_decision.get("REASONING", "No reasoning provided")
        
        try:
            sla = llm_decision.get("SLA_HOURS", "null")
            sla_hours = int(sla) if sla != "null" else None
        except:
            sla_hours = None
        
        updates.update({
            "action_required": action_required,
            "action_type": action_type,
            "priority": priority,
            "sla_hours": sla_hours,
            "reasoning": reasoning,
        })
        
        # Create task if needed (check for duplicates)
        if action_required:
            task_id = f"TASK_FORECAST_{building_id}"
            existing = any(t.get("task_id") == task_id for t in state.get("tasks", []))
            
            if not existing:
                task = {
                    "task_id": task_id,
                    "title": f"{priority}: Capacity Alert - {building_id}",
                    "description": f"ML Forecast: {forecast_total:.2f}L/24h, Peak: {peak_value:.2f}L at {peak_time.strftime('%H:%M')}. Demand level: {demand_level}. {reasoning}",
                    "priority": priority,
                    "sla_hours": sla_hours,
                    "action_type": action_type,
                    "asset_id": building_id
                }
                updates["tasks"] = state.get("tasks", []) + [task]
                updates["task_title"] = task["title"]
                updates["task_description"] = task["description"]
                updates["messages"] = updates["messages"] + [AIMessage(content=f"⚠️ {priority}: {building_id} capacity alert ({demand_level})")]
            else:
                updates["messages"] = updates["messages"] + [AIMessage(content=f"ℹ️ Forecast task already exists for {building_id}")]
        else:
            updates["task_title"] = None
            updates["task_description"] = None
            updates["messages"] = updates["messages"] + [AIMessage(content=f"✅ {building_id} demand normal ({demand_level})")]
    
    except FileNotFoundError as e:
        # Model not trained yet
        updates.update({
            "action_required": False,
            "next_agent": "supervisor",
            "messages": updates["messages"] + [AIMessage(content=f"⚠️ ML model not trained yet. Run: python models/demand_forecast/train.py")],
        })
    except Exception as e:
        updates.update({
            "action_required": False,
            "next_agent": "supervisor",
            "messages": updates["messages"] + [AIMessage(content=f"❌ Error in forecast agent: {str(e)}")],
        })
    
    return updates


def run_forecast_agent(building_id: str) -> dict:
    """
    Standalone function to run forecast agent for a building
    """
    from agents.state import build_agent_state
    
    # Initialize state
    state = build_agent_state(site_id="SITE_001", building_id=building_id)
    
    # Run agent
    result = forecast_agent_node(state)
    
    # Manual merge for standalone output
    merged = dict(state)
    for k, v in result.items():
        if k == "messages":
            merged["messages"] = (state.get("messages", []) or []) + v
        else:
            merged[k] = v
    
    return {
        "building_id": building_id,
        "current_demand": merged.get("current_demand"),
        "predicted_demand": merged.get("predicted_demand"),
        "peak_time": merged.get("peak_time"),
        "forecast_total": merged.get("forecast_total"),
        "demand_level": merged.get("demand_level"),
        "ml_recommendation": merged.get("ml_recommendation"),
        "action_required": merged.get("action_required"),
        "action_type": merged.get("action_type"),
        "priority": merged.get("priority"),
        "sla_hours": merged.get("sla_hours"),
        "reasoning": merged.get("reasoning"),
        "task": merged.get("tasks", [None])[-1] if merged.get("tasks") else None,
        "messages": [m.content if hasattr(m, 'content') else str(m) for m in merged.get("messages", [])]
    }


if __name__ == "__main__":
    """Test the forecast agent with REAL ML"""
    print("="*70)
    print("🤖 AI FORECAST AGENT TEST (with REAL ML + LLM)")
    print("="*70)
    
    buildings = ["BLD_001", "BLD_002"]
    
    for building_id in buildings:
        print(f"\n{'='*70}")
        print(f"Testing: {building_id}")
        print('='*70)
        
        result = run_forecast_agent(building_id)
        
        print(f"🔮 ML Forecast Total: {result.get('forecast_total', 'N/A')} liters/24h")
        print(f"📊 Demand Level: {result.get('demand_level', 'N/A')}")
        print(f"📈 Current Avg Demand: {result['current_demand']}%")
        print(f"⚡ Predicted Peak: {result['predicted_demand']}%")
        print(f"⏰ Peak Time: {result['peak_time']}")
        print(f"💡 ML Recommendation: {result.get('ml_recommendation', 'N/A')}")
        print(f"🚨 Action Required: {result['action_required']}")
        print(f"🎯 Priority: {result['priority']}")
        print(f"\n🤖 LLM Reasoning: {result['reasoning']}")
        
        if result['task']:
            print(f"\n✅ Task Created:")
            print(f"  Title: {result['task']['title']}")
            print(f"  Description: {result['task']['description']}")
    
    print("\n" + "="*70)
    print("✅ FORECAST AGENT TEST COMPLETE (ML + LLM INTEGRATED)")
    print("="*70)

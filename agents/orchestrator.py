"""
Main Orchestrator - Site-wide monitoring using LangGraph workflow
"""
import sys
import os
from datetime import datetime

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from agents.langgraph_workflow import run_langgraph_workflow
from typing import List, Dict

# Site configuration
SITES = {
    "SITE_001": {
        "name": "Chennai Residential Complex",
        "pumps": [
            "PUMP_BLD_001_01",
            "PUMP_BLD_001_02",
            "PUMP_BLD_002_01",
            "PUMP_BLD_002_02"
        ]
    }
}


def monitor_site(site_id: str) -> Dict:
    """
    Monitor all assets at a site using LangGraph AI agents
    """
    print(f"\n{'='*70}")
    print(f"🏢 MONITORING SITE: {site_id} (LangGraph AI)")
    print(f"{'='*70}\n")
    
    site_config = SITES.get(site_id)
    if not site_config:
        return {"error": f"Site {site_id} not found"}
    
    results = {
        "site_id": site_id,
        "site_name": site_config["name"],
        "timestamp": datetime.now().isoformat(),
        "pumps_analyzed": 0,
        "tasks_created": [],
        "critical_count": 0,
        "high_count": 0,
        "medium_count": 0,
        "low_count": 0,
        "assignments": [],
        "details": []
    }
    
    # Analyze each pump using LangGraph workflow
    for pump_id in site_config["pumps"]:
        print(f"🔍 Analyzing {pump_id} with AI agents...")
        
        try:
            # Run full LangGraph workflow (ML + LLM + Routing)
            workflow_result = run_langgraph_workflow(pump_id)
            
            results["pumps_analyzed"] += 1
            
            # Extract results
            priority = workflow_result.get("priority", "LOW")
            risk_score = workflow_result.get("risk_score", 0)
            action_type = workflow_result.get("action_type", "none")
            reasoning = workflow_result.get("reasoning", "N/A")
            
            # Count by priority
            if priority == "CRITICAL":
                results["critical_count"] += 1
            elif priority == "HIGH":
                results["high_count"] += 1
            elif priority == "MEDIUM":
                results["medium_count"] += 1
            else:
                results["low_count"] += 1
            
            # Add tasks
            if workflow_result.get("tasks"):
                results["tasks_created"].extend(workflow_result["tasks"])
            
            # Add assignments
            if workflow_result.get("assignments"):
                results["assignments"].extend(workflow_result["assignments"])
            
            # Store details
            results["details"].append({
                "pump_id": pump_id,
                "risk_score": risk_score,
                "priority": priority,
                "action_type": action_type,
                "reasoning": reasoning,
                "tasks": workflow_result.get("tasks", []),
                "assignments": workflow_result.get("assignments", [])
            })
            
            print(f"   ✅ {pump_id}: {priority} priority (Risk: {risk_score:.1%})\n")
            
        except Exception as e:
            print(f"   ❌ Error analyzing {pump_id}: {str(e)}\n")
            results["low_count"] += 1
    
    return results


def print_summary(results: Dict):
    """
    Print formatted summary of monitoring results
    """
    print("\n" + "="*70)
    print("📊 SITE MONITORING SUMMARY (LangGraph AI)")
    print("="*70)
    
    print(f"\n🏢 Site: {results['site_name']} ({results['site_id']})")
    print(f"⏰ Timestamp: {results['timestamp']}")
    
    print(f"\n📈 ANALYSIS RESULTS:")
    print(f"   Pumps Analyzed: {results['pumps_analyzed']}")
    print(f"   Tasks Created: {len(results['tasks_created'])}")
    print(f"   Technicians Assigned: {len(results['assignments'])}")
    
    print(f"\n🚨 PRIORITY BREAKDOWN:")
    print(f"   🔴 CRITICAL: {results['critical_count']}")
    print(f"   🟠 HIGH:     {results['high_count']}")
    print(f"   🟡 MEDIUM:   {results['medium_count']}")
    print(f"   🟢 LOW:      {results['low_count']}")
    
    if results['tasks_created']:
        print(f"\n📋 TASKS CREATED:")
        for idx, task in enumerate(results['tasks_created'], 1):
            print(f"\n   Task {idx}:")
            print(f"   {task['priority']}: {task['title']}")
            print(f"   SLA: {task['sla_hours']} hours")
            print(f"   Asset: {task['asset_id']}")
            print(f"   Action: {task['action_type']}")
    
    if results['assignments']:
        print(f"\n👷 TECHNICIAN ASSIGNMENTS:")
        for idx, assignment in enumerate(results['assignments'], 1):
            print(f"\n   Assignment {idx}:")
            print(f"   Task: {assignment['task_id']}")
            print(f"   Technician: {assignment['technician_name']}")
            print(f"   Priority: {assignment['priority']}")
            print(f"   Status: {assignment['status']}")
    
    if not results['tasks_created']:
        print(f"\n✅ No urgent tasks required - all assets operating normally")
    
    print("\n" + "="*70)


def monitor_all_sites() -> List[Dict]:
    """
    Monitor all configured sites
    """
    all_results = []
    
    for site_id in SITES.keys():
        results = monitor_site(site_id)
        all_results.append(results)
        print_summary(results)
    
    return all_results


if __name__ == "__main__":
    """Run site monitoring with LangGraph AI agents"""
    print("="*70)
    print("🚀 HOMENET AI AGENT SYSTEM - SITE MONITORING")
    print("🤖 Powered by LangGraph + LLM")
    print("="*70)
    
    # Monitor all sites
    results = monitor_all_sites()
    
    print("\n" + "="*70)
    print("✅ MONITORING COMPLETE")
    print("="*70)
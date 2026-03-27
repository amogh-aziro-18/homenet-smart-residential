#!/usr/bin/env python
"""Test LangGraph workflow"""
from agents.langgraph_workflow import run_langgraph_workflow

print("Testing LangGraph workflow...")
try:
    result = run_langgraph_workflow('PUMP_BLD_001_01')
    print(f"✅ LangGraph SUCCESS!")
    print(f"   Risk Score: {result.get('risk_score')}")
    print(f"   Risk Level: {result.get('risk_level')}")
    print(f"   Messages: {len(result.get('messages', []))} agent responses")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

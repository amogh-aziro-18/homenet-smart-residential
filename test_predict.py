#!/usr/bin/env python
"""Test predictive maintenance"""
from models.predictive_maintenance.predict import predict_failure_risk

result = predict_failure_risk('PUMP_BLD_001_01', horizon_hours=48)
print("Risk Score:", result.get('risk_score'))
print("Risk Level:", result.get('risk_level'))
print("Current Metrics:", result.get('current_metrics'))
print("Signals:", result.get('signals'))

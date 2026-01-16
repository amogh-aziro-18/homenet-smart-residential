# HOMENET POC – Integration Rules (Do Not Break)

To avoid integration issues and conflicts between contributors (and ChatGPT-generated code),
the following function names and return formats MUST NOT be changed.

## Fixed Function Names

### Data Simulation
File: ingestion/simulator.py  
- generate_water_sensor_data(site_id, asset_id, n_rows=100) -> list[dict]

### Demand Forecasting (Time-Series)
File: models/demand_forecast/predict.py  
- forecast_water_demand(asset_id, horizon_hours) -> dict

### Predictive Maintenance
File: models/predictive_maintenance/predict.py  
- predict_failure_risk(asset_id, horizon_hours=48) -> dict

### Supervisor Orchestrator
File: agents/supervisor_agent.py  
- run_supervisor(site_id) -> dict

### Work Orders
File: services/task_service.py  
- create_work_order(alert, assignee_id=None) -> dict  
- update_task_status(task_id, status) -> dict

## Standard Return Format (Preferred)

All cross-module functions should return dictionaries with predictable keys.

Example:

{
  "status": "ok",
  "data": {},
  "generated_at": "ISO_TIMESTAMP"
}

Only internal logic is allowed to change. The above interfaces remain stable.

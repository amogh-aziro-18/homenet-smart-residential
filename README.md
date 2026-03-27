# HOMENET Smart Residential Water Management POC

Production-style POC for predictive water infrastructure monitoring using:
- FastAPI backend
- LangGraph multi-agent workflow
- Prophet demand forecasting
- XGBoost predictive maintenance
- Expo/React Native mobile UI

This README is updated for the current architecture and includes exact local setup steps for running backend + mobile app on a new machine.

---

## 1) What This System Does

- Monitors tank and pump conditions from sample datasets
- Runs AI + ML to predict:
  - water demand risk (24 hours)
  - pump failure risk
- Generates:
  - alerts
  - tasks
  - technician assignment
  - notifications
- Returns a unified payload from `/water/run` used by all UI tabs:
  - Dashboard
  - Details
  - Notifications
  - History

---

## 2) Final Architecture (Current)

Flow:

`Data Sources -> Asset Service -> API (/water/run) -> Orchestrator -> Supervisor -> Agents/Models -> Supervisor Decisions -> Execution Layer -> API Response -> Mobile UI`

### Layer responsibilities

- **API route** (`api/routes/reports.py`)
  - Thin entrypoint
  - Builds `system_state`
  - Delegates orchestration

- **Orchestrator** (`agents/orchestrator.py`)
  - Coordinates flow
  - Calls supervisor + execution
  - Assembles final response
  - Does not own side-effect logic

- **Supervisor** (`agents/orchestrator.py`, `supervisor_*` functions)
  - Central decision maker
  - Decides which agents run based on data signals
  - Produces:
    - `alerts`
    - `task_intents`
    - `notification_intents`
    - `technician_assignment`
    - `ai_summary/ai_reasoning/ai_priority/ai_action`

- **Agents**
  - **Forecast Agent** (`agents/forecast_agent.py`) -> calls Prophet model
  - **Maintenance + Routing Workflow** (`agents/langgraph_workflow.py`) -> maintenance model + technician routing

- **Models**
  - **Demand Forecasting:** Prophet (`models/demand_forecast/predict.py`)
  - **Predictive Maintenance:** XGBoost (`models/predictive_maintenance/predict.py`)

- **Execution Layer** (`execution_layer` in `agents/orchestrator.py`)
  - Converts intents into side effects:
    - creates tasks
    - creates notifications

---

## 3) Data Sources Used

All key CSVs in `data/samples`:

- `water_tanks.csv`
  - tank level/capacity/timestamp used for runtime tank state
- `water_pumps.csv`
  - pump telemetry used for runtime pump status and maintenance risk features
- `water_consumption.csv`
  - consumption history used for demand forecasting model pipeline
- `technicians.csv`
  - technician availability/skills/load used for routing assignments

---

## 4) API Contract (Used by UI)

Main endpoint:

- `POST /water/run?building_id=BLD_001&mode=latest&tank_mode=latest&pump_mode=latest`

Response contains (stable structure expected by UI):

- `tank_status`
- `pump_status`
- `forecast`
- `maintenance`
- `alerts`
- `tasks`
- `created_tasks`
- `notifications`
- `technician_assignment`
- `langgraph`
- `ai_summary`
- `ai_reasoning`
- `ai_priority`
- `ai_action`

---

## 5) Local Setup (Manager-Friendly)

These steps are for Windows PowerShell.

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm
- Mobile device connected to same Wi-Fi as laptop
- Expo Go app installed on phone (Android/iOS)

### Step A: Start Backend (Terminal 1)

From repo root:

```powershell
cd d:\homenet-smart-residential
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Quick health check:

```powershell
curl http://127.0.0.1:8000/health
```

Optional docs check:

- Open: `http://127.0.0.1:8000/docs`

### Step B: Get Local IP

In a new PowerShell terminal:

```powershell
ipconfig | findstr /R /C:"IPv4"
```

Pick your active Wi-Fi IPv4 (example: `192.168.1.23`).

### Step C: Configure Frontend API Base URL

Update this file:

- `water-app/services/api.ts`

Set:

```ts
export const API_BASE_URL = "http://<YOUR_LOCAL_IP>:8000";
```

Example:

```ts
export const API_BASE_URL = "http://192.168.1.23:8000";
```

Note: UI tabs now consume this centralized constant. You do not need to edit each tab file separately.

### Step D: Start Frontend (Terminal 2)

```powershell
cd d:\homenet-smart-residential\water-app
npm install
npx expo start
```

### Step E: Run on Mobile

1. Open **Expo Go** on phone
2. Scan QR code shown in Terminal 2
3. App loads with tabs:
   - Dashboard
   - Details
   - Notifications
   - History

---

## 6) Run Workflow / Demo Flow

1. Open Dashboard in latest mode
2. Toggle tank/pump worst-case switches
3. Verify:
   - tank and pump states update
   - alerts appear
   - technician assignment appears
   - details tab shows diagnostics + dispatch
   - history shows created tasks

Useful API checks:

```powershell
curl -X POST "http://127.0.0.1:8000/water/run?building_id=BLD_001&mode=latest&tank_mode=latest&pump_mode=latest"
curl -X POST "http://127.0.0.1:8000/water/run?building_id=BLD_001&mode=latest&tank_mode=worst&pump_mode=worst"
curl "http://127.0.0.1:8000/tasks"
curl "http://127.0.0.1:8000/notifications"
```

---

## 7) Key Technical Highlights Implemented

- Cleaner multi-agent architecture with clearer layer boundaries
- Intent-based execution separation (`task_intents`, `notification_intents`)
- Data-driven technician routing via `technicians.csv` + `technician_service`
- Stable `/water/run` contract preserved for UI
- Forecast + maintenance outputs aligned across dashboard/details/history/notifications
- Worst-case scenarios driven by rotating real CSV rows

---

## 8) Project Structure (Relevant)

```text
homenet-smart-residential/
├── api/
│   ├── main.py
│   └── routes/reports.py
├── agents/
│   ├── orchestrator.py
│   ├── langgraph_workflow.py
│   ├── forecast_agent.py
│   ├── maintenance_agent.py
│   └── routing_agent.py
├── models/
│   ├── demand_forecast/
│   │   ├── train.py
│   │   └── predict.py
│   └── predictive_maintenance/
│       ├── train.py
│       └── predict.py
├── services/
│   ├── asset_service.py
│   ├── task_service.py
│   ├── notification_service.py
│   └── technician_service.py
├── data/samples/
│   ├── water_tanks.csv
│   ├── water_pumps.csv
│   ├── water_consumption.csv
│   └── technicians.csv
└── water-app/
    ├── services/api.ts
    └── app/(tabs)/
```

---

## 9) Troubleshooting

### App cannot hit backend
- Ensure backend is started with `--host 0.0.0.0`
- Ensure phone and laptop are on same Wi-Fi
- Recheck `API_BASE_URL` in `water-app/services/api.ts`

### Data not updating
- Check `/water/run` in browser or curl
- Confirm no firewall blocking port `8000`

### No QR scan / Expo issue
- Restart expo:
  - stop terminal
  - run `npx expo start` again

---

## 10) Future Expansion Readiness

Current architecture is suitable for:
- real-time IoT ingestion (replace CSV adapters with stream adapters)
- multiple service providers (extend routing/provider adapters)
- multi-asset expansion (water -> hvac/power) with same orchestration pattern

---

## Authors

- Amogh D R
- Vadde Vignesh


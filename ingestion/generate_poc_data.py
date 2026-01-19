import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

np.random.seed(42)

# Create output directory if not exists
os.makedirs('data/samples', exist_ok=True)

# Config - 2 weeks
START = datetime(2025, 10, 1)
DAYS = 14
BUILDINGS = ['BLD_001', 'BLD_002']

print("🚀 Starting data generation...")
print(f"Time period: {DAYS} days starting {START.date()}")
print(f"Buildings: {len(BUILDINGS)}")

# === 1. PUMP DATA (2700 rows) ===
print("\n📊 Generating pump data...")
pump_rows = []
timestamps = pd.date_range(START, periods=DAYS*48, freq='30min')

scenarios = {
    'PUMP_BLD001_01': 'gradual_failure',
    'PUMP_BLD001_02': 'early_warning',
    'PUMP_BLD002_01': 'sudden_failure',
    'PUMP_BLD002_02': 'normal'
}

for bld in BUILDINGS:
    for pump_num in [1, 2]:
        pump_id = f"PUMP_{bld}_{pump_num:02d}"
        scenario = scenarios.get(pump_id, 'normal')
        
        for ts in timestamps:
            day = (ts - START).days + 1
            vib = np.random.normal(2.5, 0.3)
            temp = np.random.normal(50, 2)
            status = 'running'
            
            if scenario == 'gradual_failure':
                if day >= 6 and day <= 10:
                    vib = 2.5 + (day - 5) * 1.2
                    temp = 50 + (day - 5) * 4
                elif day >= 11:
                    status = 'failed'
                    vib = 0
                    temp = 25
            elif scenario == 'early_warning':
                if day == 8:
                    vib = np.random.normal(7, 0.5)
                    temp = np.random.normal(65, 2)
            elif scenario == 'sudden_failure':
                if day >= 12:
                    status = 'failed'
                    vib = 0
                    temp = 25
            
            pump_rows.append({
                'pump_id': pump_id,
                'building_id': bld,
                'tank_id': f"TANK_{bld}_{pump_num:02d}",
                'timestamp': ts,
                'status': status,
                'current_amps': round(np.random.normal(12, 1), 2),
                'vibration_mm_s': round(max(0, vib), 2),
                'temperature_celsius': round(temp, 1),
                'flow_rate_lpm': 0 if status == 'failed' else round(np.random.normal(180, 15), 1),
                'pressure_psi': 0 if status == 'failed' else round(np.random.normal(45, 3), 1)
            })

df_pumps = pd.DataFrame(pump_rows)
df_pumps.to_csv('data/samples/water_pumps.csv', index=False)
print(f"   ✅ water_pumps.csv: {len(df_pumps)} rows")

# === 2. TANK DATA ===
print("\n📊 Generating tank data...")
tank_rows = []
timestamps_hourly = pd.date_range(START, periods=DAYS*24, freq='1h')

for bld in BUILDINGS:
    for tank_num in [1, 2]:
        tank_id = f"TANK_{bld}_{tank_num:02d}"
        capacity = 5000 if tank_num == 1 else 3000
        
        for ts in timestamps_hourly:
            day = (ts - START).days + 1
            if tank_id == 'TANK_BLD001_01' and day == 9:
                level_pct = np.random.uniform(20, 30)
            else:
                level_pct = np.random.uniform(80, 92)
            
            tank_rows.append({
                'tank_id': tank_id,
                'building_id': bld,
                'timestamp': ts,
                'capacity_liters': capacity,
                'current_level_liters': round(capacity * level_pct / 100),
                'level_percentage': round(level_pct, 1),
                'inlet_flow_rate_lpm': round(np.random.normal(150, 15), 1),
                'outlet_flow_rate_lpm': round(np.random.normal(120, 12), 1)
            })

df_tanks = pd.DataFrame(tank_rows)
df_tanks.to_csv('data/samples/water_tanks.csv', index=False)
print(f"   ✅ water_tanks.csv: {len(df_tanks)} rows")

# === 3. CONSUMPTION ===
print("\n📊 Generating consumption data...")
cons_rows = []
timestamps_4hr = pd.date_range(START, periods=DAYS*6, freq='4h')

for bld in BUILDINGS:
    for unit_num in range(101, 106):
        unit_id = f"UNIT_{bld}_{unit_num}"
        
        for ts in timestamps_4hr:
            day = (ts - START).days + 1
            hour = ts.hour
            
            if 6 <= hour <= 9 or 18 <= hour <= 21:
                base_cons = 50
            else:
                base_cons = 15
            
            if unit_id == 'UNIT_BLD001_102' and 7 <= day <= 10:
                consumption = np.random.normal(120, 10)
            else:
                consumption = np.random.normal(base_cons, 5)
            
            cons_rows.append({
                'timestamp': ts,
                'building_id': bld,
                'unit_id': unit_id,
                'tank_id': f"TANK_{bld}_02",
                'consumption_liters': round(max(0, consumption), 1),
                'flow_rate_lpm': round(max(0, consumption) / 4, 2)
            })

df_cons = pd.DataFrame(cons_rows)
df_cons.to_csv('data/samples/water_consumption.csv', index=False)
print(f"   ✅ water_consumption.csv: {len(df_cons)} rows")

# === 4. ALERTS ===
print("\n📊 Generating alerts...")
alerts = [
    {'alert_id': 'ALERT_001', 'timestamp': datetime(2025, 10, 11, 10, 0), 'building_id': 'BLD_001', 
     'asset_id': 'PUMP_BLD001_01', 'asset_type': 'pump', 'alert_type': 'pump_failure', 'severity': 'critical',
     'description': 'Pump bearing failure - complete shutdown'},
    {'alert_id': 'ALERT_002', 'timestamp': datetime(2025, 10, 12, 14, 0), 'building_id': 'BLD_002', 
     'asset_id': 'PUMP_BLD002_01', 'asset_type': 'pump', 'alert_type': 'pump_failure', 'severity': 'critical',
     'description': 'Sudden pump seal rupture'},
    {'alert_id': 'ALERT_003', 'timestamp': datetime(2025, 10, 10, 8, 0), 'building_id': 'BLD_001', 
     'asset_id': 'PUMP_BLD001_01', 'asset_type': 'pump', 'alert_type': 'high_vibration', 'severity': 'high',
     'description': 'Vibration exceeded threshold'},
    {'alert_id': 'ALERT_004', 'timestamp': datetime(2025, 10, 8, 9, 0), 'building_id': 'BLD_001', 
     'asset_id': 'PUMP_BLD001_02', 'asset_type': 'pump', 'alert_type': 'high_vibration', 'severity': 'medium',
     'description': 'Elevated vibration detected'},
    {'alert_id': 'ALERT_005', 'timestamp': datetime(2025, 10, 9, 15, 0), 'building_id': 'BLD_001', 
     'asset_id': 'PUMP_BLD001_01', 'asset_type': 'pump', 'alert_type': 'high_temperature', 'severity': 'medium',
     'description': 'Temperature exceeded 65C'},
    {'alert_id': 'ALERT_006', 'timestamp': datetime(2025, 10, 9, 6, 0), 'building_id': 'BLD_001', 
     'asset_id': 'TANK_BLD001_01', 'asset_type': 'tank', 'alert_type': 'low_tank_level', 'severity': 'high',
     'description': 'Tank level below 30%'},
    {'alert_id': 'ALERT_007', 'timestamp': datetime(2025, 10, 7, 12, 0), 'building_id': 'BLD_001', 
     'asset_id': 'UNIT_BLD001_102', 'asset_type': 'unit', 'alert_type': 'high_consumption', 'severity': 'medium',
     'description': 'Possible leak detected'},
    {'alert_id': 'ALERT_008', 'timestamp': datetime(2025, 10, 8, 10, 0), 'building_id': 'BLD_001', 
     'asset_id': 'PUMP_BLD001_02', 'asset_type': 'pump', 'alert_type': 'preventive_maintenance', 'severity': 'low',
     'description': 'Scheduled maintenance due'},
]

df_alerts = pd.DataFrame(alerts)
df_alerts.to_csv('data/samples/alerts.csv', index=False)
print(f"   ✅ alerts.csv: {len(df_alerts)} events")

print("\n" + "="*60)
print("🎉 DATA GENERATION COMPLETE!")
print("="*60)
total_rows = len(df_pumps) + len(df_tanks) + len(df_cons) + len(df_alerts)
print(f"Total rows: {total_rows:,}")
print(f"\nFiles created in data/samples/:")
print(f"  1. water_pumps.csv ({len(df_pumps):,} rows)")
print(f"  2. water_tanks.csv ({len(df_tanks):,} rows)")
print(f"  3. water_consumption.csv ({len(df_cons):,} rows)")
print(f"  4. alerts.csv ({len(df_alerts)} rows)")
print("="*60)

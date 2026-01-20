import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

np.random.seed(42)

# Create output directory
os.makedirs('data/samples', exist_ok=True)

# Config
START = datetime(2025, 10, 1)
DAYS = 14
BUILDINGS = ['BLD_001', 'BLD_002']

print("🚀 Starting REALISTIC data generation...")
print(f"Time period: {DAYS} days starting {START.date()}")
print(f"Buildings: {len(BUILDINGS)}")

# === 1. PUMP DATA WITH DIVERSE SCENARIOS ===
print("\n📊 Generating pump data with realistic failure scenarios...")
pump_rows = []
timestamps = pd.date_range(START, periods=DAYS*48, freq='30min')

# Define realistic scenarios for each pump
pump_scenarios = {
    'PUMP_BLD_001_01': {
        'type': 'gradual_bearing_failure',
        'description': 'Bearing gradually fails - vibration and temp increase over 5 days',
        'failure_day': 11
    },
    'PUMP_BLD_001_02': {
        'type': 'early_warning_normal',
        'description': 'Shows early warning signs but recovers - preventive maintenance works',
        'warning_day': 8
    },
    'PUMP_BLD_002_01': {
        'type': 'sudden_seal_failure',
        'description': 'Sudden seal failure after brief warning',
        'failure_day': 12
    },
    'PUMP_BLD_002_02': {
        'type': 'healthy_normal',
        'description': 'Completely healthy pump - baseline for comparison',
        'failure_day': None
    },
}

for bld in BUILDINGS:
    for pump_num in [1, 2]:
        pump_id = f"PUMP_{bld}_{pump_num:02d}"
        scenario = pump_scenarios.get(pump_id, {'type': 'healthy_normal', 'failure_day': None})
        scenario_type = scenario['type']
        failure_day = scenario.get('failure_day', None)
        
        print(f"   Generating {pump_id}: {scenario['description']}")
        
        for idx, ts in enumerate(timestamps):
            day = (ts - START).days + 1
            hour = ts.hour
            
            # === SCENARIO 1: GRADUAL BEARING FAILURE ===
            if scenario_type == 'gradual_bearing_failure':
                if day <= 5:
                    # Normal operation
                    vib = np.random.normal(3.5, 0.4)
                    temp = np.random.normal(50, 2)
                    current = np.random.normal(9.5, 0.5)
                    status = 'running'
                
                elif day == 6:
                    # Day 6: Slight increase (early warning)
                    vib = np.random.normal(4.8, 0.5)
                    temp = np.random.normal(54, 2)
                    current = np.random.normal(10.0, 0.5)
                    status = 'running'
                
                elif day == 7:
                    # Day 7: More pronounced
                    vib = np.random.normal(5.9, 0.6)
                    temp = np.random.normal(58, 2.5)
                    current = np.random.normal(10.5, 0.5)
                    status = 'running'
                
                elif day == 8:
                    # Day 8: Clear warning signs
                    vib = np.random.normal(7.2, 0.7)
                    temp = np.random.normal(63, 2)
                    current = np.random.normal(11.0, 0.6)
                    status = 'warning'
                
                elif day == 9:
                    # Day 9: Severe degradation
                    vib = np.random.normal(8.5, 0.8)
                    temp = np.random.normal(67, 2.5)
                    current = np.random.normal(11.5, 0.6)
                    status = 'critical'
                
                elif day == 10:
                    # Day 10: Very severe - about to fail
                    vib = np.random.normal(9.5, 0.9)
                    temp = np.random.normal(72, 3)
                    current = np.random.normal(12.0, 0.7)
                    status = 'critical'
                
                else:  # day >= 11
                    # FAILED - pump stopped
                    vib = 0
                    temp = np.random.normal(25, 1)  # Ambient temp
                    current = 0
                    status = 'failed'
            
            # === SCENARIO 2: EARLY WARNING BUT RECOVERS ===
            elif scenario_type == 'early_warning_normal':
                if day <= 7:
                    # Normal operation
                    vib = np.random.normal(3.2, 0.3)
                    temp = np.random.normal(49, 1.5)
                    current = np.random.normal(9.2, 0.4)
                    status = 'running'
                
                elif day == 8:
                    # Day 8: Spike in vibration (loose bolt, debris, etc.)
                    vib = np.random.normal(7.5, 0.8)
                    temp = np.random.normal(65, 2)
                    current = np.random.normal(10.8, 0.5)
                    status = 'warning'
                
                elif day == 9:
                    # Day 9: Maintenance performed - still elevated
                    vib = np.random.normal(5.0, 0.5)
                    temp = np.random.normal(56, 2)
                    current = np.random.normal(9.8, 0.4)
                    status = 'running'
                
                else:  # day >= 10
                    # Back to normal after maintenance
                    vib = np.random.normal(3.2, 0.3)
                    temp = np.random.normal(49, 1.5)
                    current = np.random.normal(9.2, 0.4)
                    status = 'running'
            
            # === SCENARIO 3: SUDDEN SEAL FAILURE ===
            elif scenario_type == 'sudden_seal_failure':
                if day <= 10:
                    # Normal operation
                    vib = np.random.normal(3.8, 0.4)
                    temp = np.random.normal(51, 2)
                    current = np.random.normal(9.6, 0.5)
                    status = 'running'
                
                elif day == 11:
                    # Day 11: Brief warning - pressure drop
                    vib = np.random.normal(5.5, 0.6)
                    temp = np.random.normal(57, 2)
                    current = np.random.normal(10.2, 0.5)
                    status = 'running'
                
                elif day == 12 and hour < 14:
                    # Day 12 morning: Still running but degraded
                    vib = np.random.normal(6.8, 0.7)
                    temp = np.random.normal(62, 2)
                    current = np.random.normal(10.8, 0.6)
                    status = 'warning'
                
                else:  # day 12 afternoon onwards
                    # SUDDEN FAILURE - seal rupture
                    vib = 0
                    temp = np.random.normal(25, 1)
                    current = 0
                    status = 'failed'
            
            # === SCENARIO 4: HEALTHY NORMAL ===
            else:  # healthy_normal
                # Consistent healthy operation
                # Add realistic daily patterns (slightly higher in afternoon)
                hour_factor = 1.0 + 0.05 * np.sin((hour - 12) * np.pi / 12)
                
                vib = np.random.normal(3.0 * hour_factor, 0.3)
                temp = np.random.normal(48 * hour_factor, 1.5)
                current = np.random.normal(9.0 * hour_factor, 0.4)
                status = 'running'
            
            # Calculate dependent variables
            if status == 'failed':
                flow_rate = 0
                pressure = 0
            else:
                # Flow rate decreases as pump degrades
                degradation_factor = 1.0 - (vib / 12.0) * 0.3  # Up to 30% reduction
                flow_rate = np.random.normal(180 * degradation_factor, 15)
                pressure = np.random.normal(45 * degradation_factor, 3)
            
            pump_rows.append({
                'pump_id': pump_id,
                'building_id': bld,
                'tank_id': f"TANK_{bld}_{pump_num:02d}",
                'timestamp': ts,
                'status': status,
                'current_amps': round(max(0, current), 2),
                'vibration_mm_s': round(max(0, vib), 2),
                'temperature_celsius': round(temp, 1),
                'flow_rate_lpm': round(max(0, flow_rate), 1),
                'pressure_psi': round(max(0, pressure), 1)
            })

df_pumps = pd.DataFrame(pump_rows)
df_pumps.to_csv('data/samples/water_pumps.csv', index=False)
print(f"\n   ✅ water_pumps.csv: {len(df_pumps)} rows")
print(f"   Status distribution:")
for status, count in df_pumps['status'].value_counts().items():
    print(f"      {status}: {count} ({count/len(df_pumps)*100:.1f}%)")

# === 2. TANK DATA WITH REALISTIC PATTERNS ===
print("\n📊 Generating tank data with realistic consumption patterns...")
tank_rows = []
timestamps_hourly = pd.date_range(START, periods=DAYS*24, freq='1h')

for bld in BUILDINGS:
    for tank_num in [1, 2]:
        tank_id = f"TANK_{bld}_{tank_num:02d}"
        capacity = 5000 if tank_num == 1 else 3000
        
        for ts in timestamps_hourly:
            day = (ts - START).days + 1
            hour = ts.hour
            
            # Realistic daily patterns
            if 6 <= hour <= 9:  # Morning peak
                outlet_flow = np.random.normal(180, 20)
            elif 18 <= hour <= 21:  # Evening peak
                outlet_flow = np.random.normal(160, 18)
            elif 0 <= hour <= 5:  # Night - very low
                outlet_flow = np.random.normal(40, 10)
            else:  # Daytime
                outlet_flow = np.random.normal(100, 15)
            
            inlet_flow = np.random.normal(150, 15)
            
            # Tank level varies based on consumption
            if tank_id == 'TANK_BLD_001_01' and day == 9:
                # Low level due to pump failure
                level_pct = np.random.uniform(20, 30)
            elif hour in [7, 8, 19, 20]:  # Post-peak hours
                level_pct = np.random.uniform(65, 80)
            else:
                level_pct = np.random.uniform(75, 92)
            
            tank_rows.append({
                'tank_id': tank_id,
                'building_id': bld,
                'timestamp': ts,
                'capacity_liters': capacity,
                'current_level_liters': round(capacity * level_pct / 100),
                'level_percentage': round(level_pct, 1),
                'inlet_flow_rate_lpm': round(max(0, inlet_flow), 1),
                'outlet_flow_rate_lpm': round(max(0, outlet_flow), 1)
            })

df_tanks = pd.DataFrame(tank_rows)
df_tanks.to_csv('data/samples/water_tanks.csv', index=False)
print(f"   ✅ water_tanks.csv: {len(df_tanks)} rows")

# === 3. CONSUMPTION DATA WITH DIVERSE PATTERNS ===
print("\n📊 Generating consumption data with diverse usage patterns...")
cons_rows = []
timestamps_4hr = pd.date_range(START, periods=DAYS*6, freq='4h')

# Define unit behaviors
unit_patterns = {
    101: 'normal_family',      # Regular family usage
    102: 'leak',               # Has a leak - high consumption
    103: 'low_usage',          # Single person, low usage
    104: 'high_usage',         # Large family
    105: 'variable',           # Irregular patterns (maybe Airbnb)
}

for bld in BUILDINGS:
    for unit_num in range(101, 106):
        unit_id = f"UNIT_{bld}_{unit_num}"
        pattern = unit_patterns[unit_num]
        
        for ts in timestamps_4hr:
            day = (ts - START).days + 1
            hour = ts.hour
            
            # Base consumption by time of day
            if 6 <= hour <= 9 or 18 <= hour <= 21:
                base = 50
            elif 0 <= hour <= 5:
                base = 8
            else:
                base = 20
            
            # Apply pattern-specific modifications
            if pattern == 'normal_family':
                consumption = np.random.normal(base, base * 0.2)
            
            elif pattern == 'leak':
                # High consumption consistently (leak days 7-10)
                if 7 <= day <= 10:
                    consumption = np.random.normal(base + 70, 15)
                else:
                    consumption = np.random.normal(base, base * 0.2)
            
            elif pattern == 'low_usage':
                consumption = np.random.normal(base * 0.4, base * 0.1)
            
            elif pattern == 'high_usage':
                consumption = np.random.normal(base * 1.8, base * 0.3)
            
            elif pattern == 'variable':
                # Random spikes (guests coming/going)
                if np.random.random() < 0.3:
                    consumption = np.random.normal(base * 2.5, base * 0.4)
                else:
                    consumption = np.random.normal(base * 0.5, base * 0.15)
            
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

# === 4. ALERTS - COMPREHENSIVE ===
print("\n📊 Generating comprehensive alerts...")
alerts = [
    # Pump BLD_001_01 - Gradual failure progression
    {'alert_id': 'ALERT_001', 'timestamp': datetime(2025, 10, 6, 14, 30), 'building_id': 'BLD_001', 
     'asset_id': 'PUMP_BLD_001_01', 'asset_type': 'pump', 'alert_type': 'high_vibration', 'severity': 'low',
     'description': 'Vibration slightly elevated: 4.8 mm/s (threshold: 4.5)'},
    
    {'alert_id': 'ALERT_002', 'timestamp': datetime(2025, 10, 7, 16, 0), 'building_id': 'BLD_001', 
     'asset_id': 'PUMP_BLD_001_01', 'asset_type': 'pump', 'alert_type': 'high_vibration', 'severity': 'medium',
     'description': 'Vibration elevated: 5.9 mm/s'},
    
    {'alert_id': 'ALERT_003', 'timestamp': datetime(2025, 10, 8, 10, 15), 'building_id': 'BLD_001', 
     'asset_id': 'PUMP_BLD_001_01', 'asset_type': 'pump', 'alert_type': 'high_vibration', 'severity': 'high',
     'description': 'Vibration critical: 7.2 mm/s - immediate inspection required'},
    
    {'alert_id': 'ALERT_004', 'timestamp': datetime(2025, 10, 8, 10, 20), 'building_id': 'BLD_001', 
     'asset_id': 'PUMP_BLD_001_01', 'asset_type': 'pump', 'alert_type': 'high_temperature', 'severity': 'medium',
     'description': 'Temperature elevated: 63°C (threshold: 60°C)'},
    
    {'alert_id': 'ALERT_005', 'timestamp': datetime(2025, 10, 9, 12, 0), 'building_id': 'BLD_001', 
     'asset_id': 'PUMP_BLD_001_01', 'asset_type': 'pump', 'alert_type': 'high_vibration', 'severity': 'critical',
     'description': 'Vibration very high: 8.5 mm/s - bearing failure imminent'},
    
    {'alert_id': 'ALERT_006', 'timestamp': datetime(2025, 10, 9, 12, 5), 'building_id': 'BLD_001', 
     'asset_id': 'PUMP_BLD_001_01', 'asset_type': 'pump', 'alert_type': 'high_temperature', 'severity': 'high',
     'description': 'Temperature critical: 67°C'},
    
    {'alert_id': 'ALERT_007', 'timestamp': datetime(2025, 10, 11, 8, 0), 'building_id': 'BLD_001', 
     'asset_id': 'PUMP_BLD_001_01', 'asset_type': 'pump', 'alert_type': 'pump_failure', 'severity': 'critical',
     'description': 'Pump complete failure - bearing seized'},
    
    # Pump BLD_001_02 - Early warning
    {'alert_id': 'ALERT_008', 'timestamp': datetime(2025, 10, 8, 9, 30), 'building_id': 'BLD_001', 
     'asset_id': 'PUMP_BLD_001_02', 'asset_type': 'pump', 'alert_type': 'high_vibration', 'severity': 'medium',
     'description': 'Vibration spike detected: 7.5 mm/s'},
    
    {'alert_id': 'ALERT_009', 'timestamp': datetime(2025, 10, 8, 15, 0), 'building_id': 'BLD_001', 
     'asset_id': 'PUMP_BLD_001_02', 'asset_type': 'pump', 'alert_type': 'preventive_maintenance', 'severity': 'medium',
     'description': 'Preventive maintenance recommended - vibration anomaly detected'},
    
    # Pump BLD_002_01 - Sudden failure
    {'alert_id': 'ALERT_010', 'timestamp': datetime(2025, 10, 11, 16, 0), 'building_id': 'BLD_002', 
     'asset_id': 'PUMP_BLD_002_01', 'asset_type': 'pump', 'alert_type': 'high_vibration', 'severity': 'medium',
     'description': 'Vibration elevated: 5.5 mm/s'},
    
    {'alert_id': 'ALERT_011', 'timestamp': datetime(2025, 10, 12, 10, 30), 'building_id': 'BLD_002', 
     'asset_id': 'PUMP_BLD_002_01', 'asset_type': 'pump', 'alert_type': 'high_vibration', 'severity': 'high',
     'description': 'Vibration high: 6.8 mm/s'},
    
    {'alert_id': 'ALERT_012', 'timestamp': datetime(2025, 10, 12, 14, 15), 'building_id': 'BLD_002', 
     'asset_id': 'PUMP_BLD_002_01', 'asset_type': 'pump', 'alert_type': 'pump_failure', 'severity': 'critical',
     'description': 'Sudden pump seal rupture - immediate shutdown'},
    
    # Tank alerts
    {'alert_id': 'ALERT_013', 'timestamp': datetime(2025, 10, 9, 6, 0), 'building_id': 'BLD_001', 
     'asset_id': 'TANK_BLD_001_01', 'asset_type': 'tank', 'alert_type': 'low_tank_level', 'severity': 'high',
     'description': 'Tank level critically low: 22% (pump failure upstream)'},
    
    # Consumption alerts
    {'alert_id': 'ALERT_014', 'timestamp': datetime(2025, 10, 7, 12, 0), 'building_id': 'BLD_001', 
     'asset_id': 'UNIT_BLD_001_102', 'asset_type': 'unit', 'alert_type': 'high_consumption', 'severity': 'medium',
     'description': 'Abnormally high consumption detected - possible leak'},
    
    {'alert_id': 'ALERT_015', 'timestamp': datetime(2025, 10, 9, 8, 0), 'building_id': 'BLD_001', 
     'asset_id': 'UNIT_BLD_001_102', 'asset_type': 'unit', 'alert_type': 'high_consumption', 'severity': 'high',
     'description': 'Sustained high consumption for 3 days - leak investigation required'},
]

df_alerts = pd.DataFrame(alerts)
df_alerts.to_csv('data/samples/alerts.csv', index=False)
print(f"   ✅ alerts.csv: {len(df_alerts)} events")

# === SUMMARY ===
print("\n" + "="*60)
print("🎉 REALISTIC DATA GENERATION COMPLETE!")
print("="*60)
total_rows = len(df_pumps) + len(df_tanks) + len(df_cons) + len(df_alerts)
print(f"Total rows: {total_rows:,}")
print(f"\nFiles created in data/samples/:")
print(f"  1. water_pumps.csv ({len(df_pumps):,} rows)")
print(f"  2. water_tanks.csv ({len(df_tanks):,} rows)")
print(f"  3. water_consumption.csv ({len(df_cons):,} rows)")
print(f"  4. alerts.csv ({len(df_alerts)} rows)")

print("\n📊 Pump Scenarios Summary:")
for pump_id, scenario in pump_scenarios.items():
    print(f"  {pump_id}: {scenario['description']}")

print("\n📊 Data Characteristics:")
print(f"  • 2 failed pumps with different failure modes")
print(f"  • 1 pump with early warning that recovers")
print(f"  • 1 completely healthy pump (baseline)")
print(f"  • Realistic daily consumption patterns")
print(f"  • Tank levels responding to pump failures")
print(f"  • Comprehensive alert timeline")
print("="*60)

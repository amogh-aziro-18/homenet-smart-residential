import pandas as pd
import numpy as np
import pickle
import json
import os
from datetime import datetime, timedelta

def predict_failure_risk(asset_id: str, horizon_hours: int = 48, timestamp=None) -> dict:
    """
    Predict asset failure risk score for the next horizon.
    
    Args:
        asset_id: Pump ID (e.g., 'PUMP_BLD_001_01')
        horizon_hours: Prediction horizon (default 48 hours)
        timestamp: Specific timestamp to predict from (optional, defaults to latest non-failed reading)
    
    Returns:
        dict with risk_score, risk_level, and signals
    """
    
    # Load model artifacts
    model_path = 'models/predictive_maintenance/artifacts/model.pkl'
    scaler_path = 'models/predictive_maintenance/artifacts/scaler.pkl'
    metadata_path = 'models/predictive_maintenance/artifacts/metadata.json'
    
    if not os.path.exists(model_path):
        return {
            "asset_id": asset_id,
            "horizon_hours": horizon_hours,
            "risk_score": 0.0,
            "risk_level": "UNKNOWN",
            "signals": ["Model not trained yet"]
        }
    
    # Load model and scaler
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    with open(scaler_path, 'rb') as f:
        scaler = pickle.load(f)
    
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    feature_cols = metadata['features']
    
    # Load pump data
    data_path = 'data/samples/water_pumps.csv'
    df_pumps = pd.read_csv(data_path)
    df_pumps['timestamp'] = pd.to_datetime(df_pumps['timestamp'])
    
    # Get data for this pump
    pump_data = df_pumps[df_pumps['pump_id'] == asset_id].copy()
    
    if len(pump_data) == 0:
        return {
            "asset_id": asset_id,
            "horizon_hours": horizon_hours,
            "risk_score": 0.0,
            "risk_level": "UNKNOWN",
            "signals": [f"Pump '{asset_id}' not found in data"]
        }
    
    pump_data = pump_data.sort_values('timestamp')
    
    # Feature engineering (same as training)
    pump_data['vibration_rolling_mean_24h'] = pump_data['vibration_mm_s'].rolling(48, min_periods=1).mean()
    pump_data['vibration_rolling_std_24h'] = pump_data['vibration_mm_s'].rolling(48, min_periods=1).std()
    pump_data['vibration_rolling_max_24h'] = pump_data['vibration_mm_s'].rolling(48, min_periods=1).max()
    
    pump_data['temp_rolling_mean_24h'] = pump_data['temperature_celsius'].rolling(48, min_periods=1).mean()
    pump_data['temp_rolling_std_24h'] = pump_data['temperature_celsius'].rolling(48, min_periods=1).std()
    pump_data['temp_rolling_max_24h'] = pump_data['temperature_celsius'].rolling(48, min_periods=1).max()
    
    pump_data['current_rolling_mean_24h'] = pump_data['current_amps'].rolling(48, min_periods=1).mean()
    pump_data['current_rolling_std_24h'] = pump_data['current_amps'].rolling(48, min_periods=1).std()
    
    pump_data['vibration_change'] = pump_data['vibration_mm_s'].diff().fillna(0)
    pump_data['temp_change'] = pump_data['temperature_celsius'].diff().fillna(0)
    
    pump_data['vibration_lag_12h'] = pump_data['vibration_mm_s'].shift(24).fillna(pump_data['vibration_mm_s'])
    pump_data['temp_lag_12h'] = pump_data['temperature_celsius'].shift(24).fillna(pump_data['temperature_celsius'])
    
    pump_data['vib_temp_interaction'] = pump_data['vibration_mm_s'] * pump_data['temperature_celsius']
    pump_data['vibration_above_threshold'] = (pump_data['vibration_mm_s'] > 6).astype(int)
    pump_data['temp_above_threshold'] = (pump_data['temperature_celsius'] > 60).astype(int)
    
    # Get the right reading - if no timestamp specified, use last non-failed reading
    if timestamp is None:
        # Find last reading before failure (if pump failed) or just last reading
        failed_readings = pump_data[pump_data['status'] == 'failed']
        if len(failed_readings) > 0:
            # Get reading 48 hours before failure for demo purposes
            failure_time = failed_readings.iloc[0]['timestamp']
            target_time = failure_time - timedelta(hours=48)
            idx = (pump_data['timestamp'] - target_time).abs().idxmin()
            latest = pump_data.loc[idx]
        else:
            # Use latest reading
            latest = pump_data.iloc[-1]
    else:
        # Use specified timestamp
        idx = (pump_data['timestamp'] - pd.to_datetime(timestamp)).abs().idxmin()
        latest = pump_data.loc[idx]
    
    # Prepare features (convert to numpy array to avoid feature name warning)
    X = latest[feature_cols].values.reshape(1, -1)
    X_scaled = scaler.transform(X)
    
    # Predict
    risk_prob = model.predict_proba(X_scaled)[0][1]
    
    # Determine risk level
    if risk_prob >= 0.8:
        risk_level = "CRITICAL"
    elif risk_prob >= 0.6:
        risk_level = "HIGH"
    elif risk_prob >= 0.3:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
    
    # Generate signals
    signals = []
    
    if latest['vibration_mm_s'] > 8:
        signals.append(f"⚠️ Vibration very high: {latest['vibration_mm_s']:.1f} mm/s (threshold: 6.0)")
    elif latest['vibration_mm_s'] > 6:
        signals.append(f"⚠️ Vibration elevated: {latest['vibration_mm_s']:.1f} mm/s (threshold: 6.0)")
    
    if latest['temperature_celsius'] > 65:
        signals.append(f"🔥 Temperature very high: {latest['temperature_celsius']:.1f}°C (threshold: 60.0)")
    elif latest['temperature_celsius'] > 60:
        signals.append(f"🔥 Temperature elevated: {latest['temperature_celsius']:.1f}°C (threshold: 60.0)")
    
    if latest['vibration_change'] > 1:
        signals.append(f"📈 Rapid vibration increase: +{latest['vibration_change']:.2f} mm/s")
    
    if latest['temp_change'] > 3:
        signals.append(f"📈 Rapid temperature increase: +{latest['temp_change']:.1f}°C")
    
    if latest['current_amps'] > 11:
        signals.append(f"⚡ Current high: {latest['current_amps']:.2f} A")
    
    if len(signals) == 0:
        signals.append("✅ All parameters within normal range")
    
    return {
        "asset_id": asset_id,
        "timestamp": str(latest['timestamp']),
        "horizon_hours": horizon_hours,
        "risk_score": round(float(risk_prob), 3),
        "risk_level": risk_level,
        "signals": signals,
        "current_metrics": {
            "vibration": round(float(latest['vibration_mm_s']), 2),
            "temperature": round(float(latest['temperature_celsius']), 1),
            "current": round(float(latest['current_amps']), 2),
            "flow_rate": round(float(latest['flow_rate_lpm']), 1),
            "pressure": round(float(latest['pressure_psi']), 1),
            "status": latest['status']
        }
    }


if __name__ == '__main__':
    # Test all pumps
    print("="*70)
    print("PREDICTIVE MAINTENANCE - RISK PREDICTIONS")
    print("="*70)
    
    pumps = [
        'PUMP_BLD_001_01',  # Gradual failure
        'PUMP_BLD_001_02',  # Early warning
        'PUMP_BLD_002_01',  # Sudden failure
        'PUMP_BLD_002_02',  # Healthy
    ]
    
    for pump_id in pumps:
        print(f"\n{'='*70}")
        print(f"🔧 Pump: {pump_id}")
        print('='*70)
        
        result = predict_failure_risk(pump_id, horizon_hours=48)
        
        print(f"📅 Prediction Time: {result['timestamp']}")
        print(f"📊 Risk Score: {result['risk_score']:.3f}")
        print(f"🎯 Risk Level: {result['risk_level']}")
        
        print(f"\n📈 Current Metrics:")
        metrics = result['current_metrics']
        print(f"   Status:      {metrics['status']}")
        print(f"   Vibration:   {metrics['vibration']} mm/s")
        print(f"   Temperature: {metrics['temperature']}°C")
        print(f"   Current:     {metrics['current']} A")
        print(f"   Flow Rate:   {metrics['flow_rate']} L/min")
        print(f"   Pressure:    {metrics['pressure']} psi")
        
        print(f"\n🚨 Warning Signals:")
        for signal in result['signals']:
            print(f"   {signal}")
    
    print("\n" + "="*70)
    print("✅ PREDICTION TEST COMPLETE!")
    print("="*70)

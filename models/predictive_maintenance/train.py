import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, recall_score, precision_score, f1_score
import pickle
import json
import os

def train_failure_risk_model(data_path: str, model_out_path: str) -> str:
    """
    Train predictive maintenance model and save artifact.
    
    Args:
        data_path: Path to water_pumps.csv
        model_out_path: Path to save model artifacts
    
    Returns:
        model_out_path: Path where model was saved
    """
    
    print("="*60)
    print("PREDICTIVE MAINTENANCE MODEL TRAINING")
    print("="*60)
    
    # === 1. Load Data ===
    print("\n📊 Loading pump data...")
    df_pumps = pd.read_csv(data_path)
    df_pumps['timestamp'] = pd.to_datetime(df_pumps['timestamp'])
    print(f"   Loaded {len(df_pumps)} rows, {df_pumps['pump_id'].nunique()} pumps")
    
    # === 2. Feature Engineering ===
    print("\n🔧 Creating features...")
    df_pumps = df_pumps.sort_values(['pump_id', 'timestamp'])
    
    # Rolling window features (24 hours = 48 readings at 30min intervals)
    df_pumps['vibration_rolling_mean_24h'] = df_pumps.groupby('pump_id')['vibration_mm_s'].rolling(48, min_periods=1).mean().reset_index(0, drop=True)
    df_pumps['vibration_rolling_std_24h'] = df_pumps.groupby('pump_id')['vibration_mm_s'].rolling(48, min_periods=1).std().reset_index(0, drop=True)
    df_pumps['vibration_rolling_max_24h'] = df_pumps.groupby('pump_id')['vibration_mm_s'].rolling(48, min_periods=1).max().reset_index(0, drop=True)
    
    df_pumps['temp_rolling_mean_24h'] = df_pumps.groupby('pump_id')['temperature_celsius'].rolling(48, min_periods=1).mean().reset_index(0, drop=True)
    df_pumps['temp_rolling_std_24h'] = df_pumps.groupby('pump_id')['temperature_celsius'].rolling(48, min_periods=1).std().reset_index(0, drop=True)
    df_pumps['temp_rolling_max_24h'] = df_pumps.groupby('pump_id')['temperature_celsius'].rolling(48, min_periods=1).max().reset_index(0, drop=True)
    
    df_pumps['current_rolling_mean_24h'] = df_pumps.groupby('pump_id')['current_amps'].rolling(48, min_periods=1).mean().reset_index(0, drop=True)
    df_pumps['current_rolling_std_24h'] = df_pumps.groupby('pump_id')['current_amps'].rolling(48, min_periods=1).std().reset_index(0, drop=True)
    
    # Rate of change (trend detection)
    df_pumps['vibration_change'] = df_pumps.groupby('pump_id')['vibration_mm_s'].diff().fillna(0)
    df_pumps['temp_change'] = df_pumps.groupby('pump_id')['temperature_celsius'].diff().fillna(0)
    
    # Lag features (values 12 hours ago)
    df_pumps['vibration_lag_12h'] = df_pumps.groupby('pump_id')['vibration_mm_s'].shift(24).fillna(df_pumps['vibration_mm_s'])
    df_pumps['temp_lag_12h'] = df_pumps.groupby('pump_id')['temperature_celsius'].shift(24).fillna(df_pumps['temperature_celsius'])
    
    # Interaction features
    df_pumps['vib_temp_interaction'] = df_pumps['vibration_mm_s'] * df_pumps['temperature_celsius']
    
    # Threshold-based features
    df_pumps['vibration_above_threshold'] = (df_pumps['vibration_mm_s'] > 6).astype(int)
    df_pumps['temp_above_threshold'] = (df_pumps['temperature_celsius'] > 60).astype(int)
    
    print(f"   Created {len(df_pumps.columns) - 11} engineered features")
    
    # === 3. Create Labels ===
    print("\n🏷️  Creating failure labels...")
    
    # Find failure times for each pump
    failure_times = df_pumps[df_pumps['status'] == 'failed'].groupby('pump_id')['timestamp'].first()
    
    def create_failure_label(row):
        pump_id = row['pump_id']
        current_time = row['timestamp']
        
        if pump_id in failure_times.index:
            failure_time = failure_times[pump_id]
            hours_to_failure = (failure_time - current_time).total_seconds() / 3600
            
            # Label = 1 if failure within 48 hours
            if 0 < hours_to_failure <= 48:
                return 1
        return 0
    
    df_pumps['will_fail_48h'] = df_pumps.apply(create_failure_label, axis=1)
    
    failure_count = df_pumps['will_fail_48h'].sum()
    normal_count = (df_pumps['will_fail_48h'] == 0).sum()
    print(f"   Failure cases: {failure_count} ({failure_count/len(df_pumps)*100:.1f}%)")
    print(f"   Normal cases: {normal_count} ({normal_count/len(df_pumps)*100:.1f}%)")
    
    # === 4. Prepare Training Data ===
    print("\n📋 Preparing training data...")
    
    feature_cols = [
        'vibration_mm_s', 'temperature_celsius', 'current_amps',
        'flow_rate_lpm', 'pressure_psi',
        'vibration_rolling_mean_24h', 'vibration_rolling_std_24h', 'vibration_rolling_max_24h',
        'temp_rolling_mean_24h', 'temp_rolling_std_24h', 'temp_rolling_max_24h',
        'current_rolling_mean_24h', 'current_rolling_std_24h',
        'vibration_change', 'temp_change',
        'vibration_lag_12h', 'temp_lag_12h',
        'vib_temp_interaction',
        'vibration_above_threshold', 'temp_above_threshold'
    ]
    
    # Remove rows with NaN
    df_model = df_pumps.dropna(subset=feature_cols + ['will_fail_48h'])
    
    X = df_model[feature_cols]
    y = df_model['will_fail_48h']
    
    print(f"   Training samples: {len(X)}")
    print(f"   Features: {len(feature_cols)}")
    
    # === 5. Train/Test Split ===
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # === 6. Scale Features ===
    print("\n⚖️  Scaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # === 7. Train XGBoost Model ===
    print("\n🤖 Training XGBoost classifier...")
    
    # Calculate scale_pos_weight for imbalanced data
    scale_weight = len(y_train[y_train == 0]) / len(y_train[y_train == 1])
    
    model = XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        scale_pos_weight=scale_weight,
        random_state=42,
        eval_metric='logloss'
    )
    
    model.fit(X_train_scaled, y_train)
    print("   ✅ Model trained successfully")
    
    # === 8. Evaluate Model ===
    print("\n📊 Model Evaluation:")
    
    y_pred_train = model.predict(X_train_scaled)
    y_pred_test = model.predict(X_test_scaled)
    
    print("\n   Training Set:")
    print(f"      Recall: {recall_score(y_train, y_pred_train):.3f}")
    print(f"      Precision: {precision_score(y_train, y_pred_train):.3f}")
    print(f"      F1-Score: {f1_score(y_train, y_pred_train):.3f}")
    
    print("\n   Test Set:")
    print(f"      Recall: {recall_score(y_test, y_pred_test):.3f}")
    print(f"      Precision: {precision_score(y_test, y_pred_test):.3f}")
    print(f"      F1-Score: {f1_score(y_test, y_pred_test):.3f}")
    
    print("\n   Confusion Matrix (Test):")
    cm = confusion_matrix(y_test, y_pred_test)
    print(f"      TN: {cm[0,0]}, FP: {cm[0,1]}")
    print(f"      FN: {cm[1,0]}, TP: {cm[1,1]}")
    
    # === 9. Feature Importance ===
    print("\n🎯 Top 10 Important Features:")
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    for idx, row in feature_importance.head(10).iterrows():
        print(f"      {row['feature']}: {row['importance']:.4f}")
    
    # === 10. Save Model Artifacts ===
    print("\n💾 Saving model artifacts...")
    
    os.makedirs(model_out_path, exist_ok=True)
    
    # Save model
    model_file = os.path.join(model_out_path, 'model.pkl')
    with open(model_file, 'wb') as f:
        pickle.dump(model, f)
    print(f"   ✅ Model saved: {model_file}")
    
    # Save scaler
    scaler_file = os.path.join(model_out_path, 'scaler.pkl')
    with open(scaler_file, 'wb') as f:
        pickle.dump(scaler, f)
    print(f"   ✅ Scaler saved: {scaler_file}")
    
    # Save feature list and metadata
    metadata = {
        'features': feature_cols,
        'model_type': 'XGBoost',
        'n_features': len(feature_cols),
        'train_samples': len(X_train),
        'test_recall': float(recall_score(y_test, y_pred_test)),
        'test_precision': float(precision_score(y_test, y_pred_test)),
        'test_f1': float(f1_score(y_test, y_pred_test)),
        'trained_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    metadata_file = os.path.join(model_out_path, 'metadata.json')
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"   ✅ Metadata saved: {metadata_file}")
    
    print("\n" + "="*60)
    print("✅ TRAINING COMPLETE!")
    print("="*60)
    
    return model_out_path


if __name__ == '__main__':
    # Run training
    data_path = 'data/samples/water_pumps.csv'
    model_out_path = 'models/predictive_maintenance/artifacts'
    
    result = train_failure_risk_model(data_path, model_out_path)
    print(f"\n🎉 Model artifacts saved to: {result}")

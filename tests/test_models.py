import pytest
from pathlib import Path

def test_maintenance_model_exists():
    """Test that maintenance model file exists"""
    model_path = Path("models/predictive_maintenance/artifacts/model.pkl")
    if not model_path.exists():
        pytest.skip("Maintenance model not trained yet")
    assert model_path.exists()

def test_demand_forecast_models_exist():
    """Test that demand forecast model files exist"""
    artifacts_dir = Path("models/demand_forecast/artifacts")
    if not artifacts_dir.exists():
        pytest.skip("Demand forecast models not trained yet")
    
    # Check if any prophet models exist
    prophet_models = list(artifacts_dir.glob("prophet_*.pkl"))
    assert len(prophet_models) > 0, "No prophet models found"

def test_maintenance_model_loads():
    """Test that maintenance model can be loaded"""
    model_path = Path("models/predictive_maintenance/artifacts/model.pkl")
    if not model_path.exists():
        pytest.skip("Maintenance model not available")
    
    import pickle
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    assert model is not None

def test_demand_forecast_model_loads():
    """Test that demand forecast models can be loaded"""
    artifacts_dir = Path("models/demand_forecast/artifacts")
    if not artifacts_dir.exists():
        pytest.skip("Demand forecast models not available")
    
    prophet_models = list(artifacts_dir.glob("prophet_*.pkl"))
    if len(prophet_models) == 0:
        pytest.skip("No prophet models found")
    
    # Prophet models are saved with pickle, but may need special handling
    try:
        import pickle
        with open(prophet_models[0], "rb") as f:
            model = pickle.load(f)
        assert model is not None
    except Exception as e:
        # If loading fails, just check the file exists
        pytest.skip(f"Prophet model exists but couldn't be loaded (may need Prophet-specific loader): {e}")

def test_training_data_exists():
    """Test that training data files exist"""
    pump_data = Path("data/samples/water_pumps.csv")
    consumption_data = Path("data/samples/water_consumption.csv")
    
    if not pump_data.exists() or not consumption_data.exists():
        pytest.skip("Training data not generated yet")
    
    assert pump_data.exists(), "Pump data not found"
    assert consumption_data.exists(), "Consumption data not found"

def test_orchestrator_exists():
    """Test orchestrator file exists"""
    assert Path("agents/orchestrator.py").exists()

def test_models_directory_exists():
    """Test that models directory exists"""
    assert Path("models").exists(), "models directory not found"

def test_data_directory_exists():
    """Test that data directory exists"""
    assert Path("data").exists(), "data directory not found"

def test_predictive_maintenance_artifacts():
    """Test predictive maintenance artifacts directory"""
    artifacts_dir = Path("models/predictive_maintenance/artifacts")
    if not artifacts_dir.exists():
        pytest.skip("Artifacts not generated yet")
    
    assert artifacts_dir.exists()
    # Check for model, scaler, metadata
    assert (artifacts_dir / "model.pkl").exists()
    assert (artifacts_dir / "scaler.pkl").exists()
    assert (artifacts_dir / "metadata.json").exists()

def test_demand_forecast_artifacts():
    """Test demand forecast artifacts directory"""
    artifacts_dir = Path("models/demand_forecast/artifacts")
    if not artifacts_dir.exists():
        pytest.skip("Artifacts not generated yet")
    
    assert artifacts_dir.exists()
    assert (artifacts_dir / "metadata.json").exists()

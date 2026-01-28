import pytest
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_api_file_exists():
    """Test that main API file exists"""
    assert Path("api/main.py").exists(), "API main.py not found"

def test_api_imports():
    """Test that FastAPI app can be imported"""
    try:
        from api.main import app
        assert app is not None
    except ImportError as e:
        pytest.fail(f"Failed to import FastAPI app: {e}")

def test_requirements_file_exists():
    """Test that requirements.txt exists"""
    assert Path("requirements.txt").exists(), "requirements.txt not found"

def test_rules_directory_exists():
    """Test that rules directory exists"""
    assert Path("rules").exists(), "rules directory not found"

def test_ingestion_scripts_exist():
    """Test that ingestion scripts exist"""
    scripts = [
        "ingestion/generate_poc_data.py",
        "ingestion/mqtt_consumer.py",
        "ingestion/simulator.py",
        "ingestion/ticket_ingest.py"
    ]
    for script in scripts:
        assert Path(script).exists(), f"{script} not found"

def test_data_directory_structure():
    """Test that required data directories exist"""
    dirs = ["data", "data/tickets"]
    for dir_path in dirs:
        assert Path(dir_path).exists(), f"Directory {dir_path} not found"

def test_agents_directory_exists():
    """Test that agents directory exists"""
    assert Path("agents").exists(), "agents directory not found"

def test_models_directory_exists():
    """Test that models directory exists"""
    assert Path("models").exists(), "models directory not found"

import pytest
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_orchestrator_file_exists():
    """Test that orchestrator file exists"""
    assert Path("agents/orchestrator.py").exists(), "orchestrator.py not found"

def test_routing_agent_file_exists():
    """Test that routing agent file exists"""
    assert Path("agents/routing_agent.py").exists(), "routing_agent.py not found"

def test_maintenance_agent_file_exists():
    """Test that maintenance agent file exists"""
    assert Path("agents/maintenance_agent.py").exists(), "maintenance_agent.py not found"

def test_orchestrator_imports():
    """Test orchestrator can be imported"""
    try:
        import agents.orchestrator
        assert agents.orchestrator is not None
    except ImportError as e:
        pytest.fail(f"Failed to import orchestrator: {e}")

def test_routing_agent_imports():
    """Test routing agent can be imported"""
    try:
        import agents.routing_agent
        assert agents.routing_agent is not None
    except ImportError as e:
        pytest.fail(f"Failed to import routing agent: {e}")

def test_maintenance_agent_imports():
    """Test maintenance agent can be imported"""
    try:
        import agents.maintenance_agent
        assert agents.maintenance_agent is not None
    except ImportError as e:
        pytest.fail(f"Failed to import maintenance agent: {e}")

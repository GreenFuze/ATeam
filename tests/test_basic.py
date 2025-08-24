"""Basic tests to verify package structure."""

def test_package_import():
    """Test that the ateam package can be imported."""
    import ateam
    assert ateam.__version__ == "0.1.0a1"

def test_util_imports():
    """Test that utility modules can be imported."""
    from ateam.util.types import Result, ErrorInfo
    from ateam.util.const import TailType, AgentState, DEFAULTS
    from ateam.util.logging import log
    from ateam.util.paths import expand_user_vars, resolve_within, SandboxViolation
    
    # Test Result type
    result = Result(ok=True, value="test")
    assert result.ok is True
    assert result.value == "test"
    
    # Test constants
    assert TailType.TOKEN == "token"
    assert AgentState.IDLE == "idle"
    assert "HEARTBEAT_INTERVAL_SEC" in DEFAULTS

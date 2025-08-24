"""Tests for configuration discovery and merging."""

import tempfile
import yaml
from pathlib import Path
from ateam.config.discovery import ConfigDiscovery
from ateam.config.merge import ConfigMerger
from ateam.config.loader import load_stack
from ateam.agent.identity import AgentIdentity

def test_discovery_stack(tmp_path):
    """Test config discovery from CWD to home."""
    # Create nested structure
    project = tmp_path / "project"
    project.mkdir()
    subdir = project / "subdir"
    subdir.mkdir()
    
    # Create .ateam directories
    project_ateam = project / ".ateam"
    project_ateam.mkdir()
    subdir_ateam = subdir / ".ateam"
    subdir_ateam.mkdir()
    
    # Test discovery from subdir
    discovery = ConfigDiscovery(str(subdir))
    result = discovery.discover_stack()
    
    assert result.ok
    stack = result.value
    assert len(stack) >= 2  # subdir + project + possibly home
    assert str(subdir_ateam) in stack
    assert str(project_ateam) in stack

def test_merge_scalars():
    """Test scalar merging (first non-None wins)."""
    merger = ConfigMerger()
    
    # Test with None values
    result = merger.merge_scalars([None, None, "value"])
    assert result == "value"
    
    # Test with first value
    result = merger.merge_scalars(["first", "second"])
    assert result == "first"

def test_merge_dicts():
    """Test dictionary deep merging."""
    merger = ConfigMerger()
    
    dict1 = {"a": 1, "b": {"x": 1, "y": 2}}
    dict2 = {"b": {"y": 3, "z": 4}, "c": 5}
    
    result = merger.merge_dicts([dict1, dict2])
    expected = {"a": 1, "b": {"x": 1, "y": 3, "z": 4}, "c": 5}
    assert result == expected

def test_merge_lists():
    """Test list merging with de-duplication."""
    merger = ConfigMerger()
    
    list1 = [{"id": "a", "val": 1}, {"id": "b", "val": 2}]
    list2 = [{"id": "b", "val": 3}, {"id": "c", "val": 4}]
    
    # De-dupe by id
    result = merger.merge_lists([list1, list2], key="id")
    assert len(result) == 3  # a, b, c
    assert any(item["id"] == "a" for item in result)
    assert any(item["id"] == "b" for item in result)
    assert any(item["id"] == "c" for item in result)

def test_load_stack(tmp_path):
    """Test loading and merging config stack."""
    # Create project structure
    project = tmp_path / "myproj"
    project.mkdir()
    ateam = project / ".ateam"
    ateam.mkdir()
    
    # Create project.yaml
    project_yaml = ateam / "project.yaml"
    project_yaml.write_text(yaml.dump({"name": "myproj"}))
    
    # Create models.yaml
    models_yaml = ateam / "models.yaml"
    models_yaml.write_text(yaml.dump({
        "models": {
            "gpt-4": {
                "provider": "openai",
                "context_window_size": 8192
            }
        }
    }))
    
    # Create tools.yaml
    tools_yaml = ateam / "tools.yaml"
    tools_yaml.write_text(yaml.dump({
        "mcp": {
            "kind": "redis",
            "url": "redis://localhost:6379/0"
        }
    }))
    
    # Test loading
    result = load_stack(str(project))
    assert result.ok
    
    project_cfg, models_cfg, tools_cfg, agents_cfg = result.value
    assert project_cfg.name == "myproj"
    assert "gpt-4" in models_cfg.models
    assert str(tools_cfg.mcp.url) == "redis://localhost:6379/0"
    assert len(agents_cfg) == 0  # No agents defined

def test_agent_identity(tmp_path):
    """Test agent identity computation."""
    # Create project structure
    project = tmp_path / "myproj"
    project.mkdir()
    ateam = project / ".ateam"
    ateam.mkdir()
    
    # Create project.yaml
    project_yaml = ateam / "project.yaml"
    project_yaml.write_text(yaml.dump({"name": "myproj"}))
    
    # Test identity without agent config (uses directory name)
    identity = AgentIdentity(str(project))
    agent_id = identity.compute()
    assert agent_id == "myproj/myproj"  # project name / directory name
    
    # Test with overrides
    identity = AgentIdentity(str(project), project_override="testproj", name_override="zeus")
    agent_id = identity.compute()
    assert agent_id == "testproj/zeus"

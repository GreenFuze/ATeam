import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from .schema_project import ProjectCfg
from .schema_models import ModelsYaml
from .schema_tools import ToolsCfg, TransportCfg
from .schema_agents import AgentCfg
from .discovery import ConfigDiscovery
from .merge import ConfigMerger
from ..util.types import Result, ErrorInfo

def load_yaml(path: Path) -> Dict[str, Any]:
    """Load YAML file, return empty dict if file doesn't exist."""
    return yaml.safe_load(path.read_text()) if path.exists() else {}

def load_stack(start_cwd: str) -> Result[Tuple[Optional[ProjectCfg], ModelsYaml, ToolsCfg, Dict[str, AgentCfg]]]:
    """Load and merge config from .ateam stack."""
    try:
        # Discover config stack
        discovery = ConfigDiscovery(start_cwd)
        stack_result = discovery.discover_stack()
        if not stack_result.ok:
            return Result(ok=False, error=stack_result.error)
        
        stack = stack_result.value
        merger = ConfigMerger()

        # Aggregate dicts across layers (highest→lowest)
        project_dicts: List[Dict[str, Any]] = []
        models_dicts:  List[Dict[str, Any]] = []
        tools_dicts:   List[Dict[str, Any]] = []
        agents_maps:   List[Dict[str, Any]] = []

        for root in stack:
            p = Path(root)
            project_dicts.append(load_yaml(p / "project.yaml"))
            models_dicts.append(load_yaml(p / "models.yaml"))
            tools_dicts.append(load_yaml(p / "tools.yaml"))

            agents_dir = p / "agents"
            if agents_dir.exists():
                m: Dict[str, Any] = {}
                for d in agents_dir.iterdir():
                    if d.is_dir():
                        agent_yaml = load_yaml(d / "agent.yaml")
                        if agent_yaml:  # Only include if file exists and has content
                            m[d.name] = agent_yaml
                agents_maps.append(m)

        # Merge configs
        project_merged = merger.merge_dicts(project_dicts)
        models_merged  = merger.merge_dicts(models_dicts)
        tools_merged   = merger.merge_dicts(tools_dicts)

        # Agent precedence: take full directory from highest layer if conflict
        agents: Dict[str, Any] = {}
        for m in agents_maps:
            for name, cfg in m.items():
                if name not in agents:
                    agents[name] = cfg  # first occurrence is highest-priority

        # Create Pydantic objects
        project = ProjectCfg(**project_merged) if project_merged else None
        models  = ModelsYaml(**models_merged) if models_merged else ModelsYaml()
        tools   = ToolsCfg(**tools_merged) if tools_merged else ToolsCfg(
            mcp=TransportCfg(url="redis://127.0.0.1:6379/0")
        )

        agent_objs: Dict[str, AgentCfg] = {k: AgentCfg(**v) for k, v in agents.items()}
        
        return Result(ok=True, value=(project, models, tools, agent_objs))
    except Exception as e:
        return Result(ok=False, error=ErrorInfo("config.load_failed", str(e)))

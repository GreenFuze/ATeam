from dataclasses import dataclass
from typing import Literal, Optional, List, Dict, Any, Tuple

AgentId = str  # "project/agent"
DocId = str
Scope = Literal["agent", "project", "user"]
State = Literal["init", "registered", "idle", "busy", "disconnected", "shutdown"]

@dataclass
class AgentInfo:
    id: AgentId
    name: str
    project: str
    model: str
    cwd: str
    host: str
    pid: int
    started_at: str
    state: State
    ctx_pct: float = 0.0

@dataclass
class TailEvent:
    type: Literal["token", "tool", "warn", "error", "task.start", "task.end"]
    text: Optional[str] = None
    name: Optional[str] = None           # tool name
    input: Optional[Dict[str, Any]] = None
    msg: Optional[str] = None
    trace: Optional[str] = None
    id: Optional[str] = None             # task id
    prompt_id: Optional[str] = None
    ok: Optional[bool] = None
    model: Optional[str] = None

@dataclass
class QueueItem:
    id: str
    text: str
    source: Literal["console", "local"]
    ts: float

@dataclass
class Turn:
    ts: float
    role: Literal["user", "assistant", "tool"]
    source: Literal["console", "local", "system"]
    content: str
    tokens_in: int
    tokens_out: int
    tool_calls: Optional[List[Dict[str, Any]]] = None

@dataclass
class KBItem:
    path_or_url: str
    metadata: Dict[str, Any]

@dataclass
class KBHit:
    id: DocId
    score: float
    metadata: Dict[str, Any]

@dataclass
class AgentCreateSpec:
    project: str
    name: str
    cwd: str
    model_id: str
    system_base_path: str
    kb_seeds: List[str]

@dataclass
class AgentSpawnSpec:
    project: str
    name: str
    cwd: str
    redis_url: str
    model_id: str
    bootstrap_token: str

@dataclass
class BootstrapInfo:
    token: str
    local_spawn: bool
    cmdline: str

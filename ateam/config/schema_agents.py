from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class PromptCfg(BaseModel):
    base: str
    overlay: Optional[str] = None

class ScratchpadCfg(BaseModel):
    max_iterations: int = Field(ge=1, default=3)
    score_lower_bound: float = Field(ge=0, le=1, default=0.7)

class FSWhitelistCfg(BaseModel):
    whitelist: List[str] = Field(default_factory=list)

class TelemetryCfg(BaseModel):
    prometheus_port: int = 0  # 0=disabled

class AgentCfg(BaseModel):
    name: str
    model: str
    prompt: PromptCfg
    scratchpad: Optional[ScratchpadCfg] = None
    tools: Optional[Dict[str, bool]] = None  # legacy; prefer ToolsPolicyCfg
    fs: Optional[FSWhitelistCfg] = None
    telemetry: Optional[TelemetryCfg] = None

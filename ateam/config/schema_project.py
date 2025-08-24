from pydantic import BaseModel, Field
from typing import Optional

class ProjectCfg(BaseModel):
    name: str = Field(min_length=1, description="Project logical name")
    description: Optional[str] = None
    retention_days: Optional[int] = Field(default=None, ge=1, le=365)

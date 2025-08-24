from pydantic import BaseModel, Field
from typing import Dict

class ModelEntry(BaseModel):
    provider: str
    context_window_size: int = Field(gt=0)
    default_inference: dict = {}
    model_settings: dict = {}

class ModelsYaml(BaseModel):
    models: Dict[str, ModelEntry] = {}

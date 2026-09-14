from typing import Literal

from pydantic import BaseModel, Field

AIProvider = Literal["anthropic", "openai", "google"]


class AISettingsUpdate(BaseModel):
    provider: AIProvider
    model: str = Field(min_length=1, max_length=100)
    api_key: str = Field(min_length=1, max_length=500)


class AISettingsOut(BaseModel):
    provider: str
    model: str
    api_key_configured: bool
    api_key_preview: str | None = None

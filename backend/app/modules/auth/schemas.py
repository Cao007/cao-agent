from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(min_length=10, max_length=128)


class CurrentUser(BaseModel):
    id: UUID
    username: str
    csrf_token: str

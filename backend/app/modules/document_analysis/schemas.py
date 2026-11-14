from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AnalysisInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=32000)
    require_review: bool = True


class Extraction(BaseModel):
    """HTTP 业务结果；图状态通过显式映射返回此 schema。"""

    title: str = Field(max_length=200)
    summary: str = Field(max_length=4000)
    key_points: list[str] = Field(max_length=20)
    action_items: list[str] = Field(max_length=20)


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approved: bool


class AnalysisInfo(BaseModel):
    id: UUID
    title: str
    status: str
    text: str
    require_review: bool
    result: Extraction | None = None
    review: Extraction | None = None
